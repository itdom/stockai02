"""Validate standardized data records against AI3 contract rules."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence

from common.logger import configure_logging, get_logger
from common.timeutils import week_monday
from data.contracts.enums import DataSource, Frequency
from data.normalizers.instrument_normalizer import normalize_instruments
from data.normalizers.market_normalizer import normalize_market_bars
from data.providers.csv_provider import CsvProvider
from data.repositories.base import InMemoryRecordWriter
from data.repositories.instrument_repo import InstrumentRepository
from data.repositories.market_repo import MarketRepository
from data.repositories.social_repo import SocialRepository
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql


LOGGER = get_logger(__name__)

SYMBOL_RE = re.compile(r"^\d{6}\.(SZ|SH|BJ)$")
DATE_RE = re.compile(r"^\d{8}$")
PCT_CHG_TOLERANCE = Decimal("0.01")
MAX_SAMPLES = 5


@dataclass(frozen=True)
class ValidationRuleResult:
    rule_id: str
    domain: str
    severity: str
    message: str
    passed_count: int
    failed_count: int
    samples: list[dict[str, Any]]

    @property
    def passed(self) -> bool:
        return self.failed_count == 0


@dataclass(frozen=True)
class ValidationSummary:
    domain: str
    checked_count: int
    results: list[ValidationRuleResult]

    @property
    def error_count(self) -> int:
        return sum(1 for result in self.results if result.severity == "error" and not result.passed)

    @property
    def warning_count(self) -> int:
        return sum(1 for result in self.results if result.severity == "warning" and not result.passed)

    @property
    def info_count(self) -> int:
        return sum(1 for result in self.results if result.severity == "info")

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["error_count"] = self.error_count
        payload["warning_count"] = self.warning_count
        payload["info_count"] = self.info_count
        payload["passed"] = self.passed
        return payload


def run(
    *,
    domain: str,
    instrument_repository: InstrumentRepository | None = None,
    market_repository: MarketRepository | None = None,
    social_repository: SocialRepository | None = None,
    records: list[Mapping[str, Any]] | None = None,
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> ValidationSummary:
    LOGGER.info(
        "validate_data started domain=%s symbol=%s start_date=%s end_date=%s",
        domain,
        symbol,
        start_date,
        end_date,
    )
    loaded_records = _load_domain_records(
        domain=domain,
        instrument_repository=instrument_repository,
        market_repository=market_repository,
        social_repository=social_repository,
        records=records,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )
    summary = validate_records(domain, loaded_records)
    LOGGER.info(
        "validate_data finished domain=%s checked=%s errors=%s warnings=%s",
        summary.domain,
        summary.checked_count,
        summary.error_count,
        summary.warning_count,
    )
    return summary


def validate_records(
    domain: str,
    records: list[Mapping[str, Any]],
) -> ValidationSummary:
    if domain == "instrument":
        results = validate_instruments(records)
    elif domain == "market_daily":
        results = validate_market_bars(records, domain=domain, expected_frequency=Frequency.DAILY.value)
    elif domain == "market_weekly":
        results = validate_market_bars(records, domain=domain, expected_frequency=Frequency.WEEKLY.value)
    elif domain == "social":
        results = validate_social_posts(records)
    else:
        raise ValueError(f"Unsupported validation domain: {domain}")
    return ValidationSummary(domain=domain, checked_count=len(records), results=results)


def validate_instruments(records: list[Mapping[str, Any]]) -> list[ValidationRuleResult]:
    return [
        _rule(
            "INS-001",
            "instrument",
            "error",
            "symbol must be non-empty and unique",
            records,
            _instrument_symbol_non_empty_unique_failures(records),
        ),
        _rule(
            "INS-002",
            "instrument",
            "error",
            "symbol must match 000001.SZ / 600000.SH / 430000.BJ format",
            records,
            [row for row in records if not _matches(SYMBOL_RE, row.get("symbol"))],
        ),
        _rule(
            "INS-003",
            "instrument",
            "warning",
            "name should be non-empty",
            records,
            [row for row in records if _is_blank(row.get("name"))],
        ),
        _rule(
            "INS-004",
            "instrument",
            "warning",
            "list_date should be YYYYMMDD and not later than today",
            records,
            [row for row in records if not _date_is_empty_or_valid(row.get("list_date"), max_today=True)],
        ),
        _rule(
            "INS-005",
            "instrument",
            "warning",
            "delist_date should be empty or not earlier than list_date",
            records,
            [row for row in records if not _delist_date_is_valid(row)],
        ),
        _info(
            "INS-006",
            "instrument",
            "instrument count by exchange",
            records,
            dict(Counter(str(row.get("exchange") or row.get("market") or "unknown") for row in records)),
        ),
    ]


def validate_market_bars(
    records: list[Mapping[str, Any]],
    *,
    domain: str,
    expected_frequency: str,
) -> list[ValidationRuleResult]:
    prefix = "DLY" if expected_frequency == Frequency.DAILY.value else "WKY"
    results = [
        _rule(
            f"{prefix}-001" if prefix == "DLY" else "WKY-002",
            domain,
            "error",
            "(symbol, trade_date, frequency, source) must be unique",
            records,
            _market_key_duplicate_failures(records),
        ),
        _rule(
            f"{prefix}-002" if prefix == "DLY" else "WKY-001",
            domain,
            "error",
            "trade_date must be YYYYMMDD" if prefix == "DLY" else "weekly trade_date must be Monday",
            records,
            _trade_date_failures(records, require_monday=expected_frequency == Frequency.WEEKLY.value),
        ),
        _rule(
            f"{prefix}-003",
            domain,
            "error",
            "OHLC values must be positive and frequency must match the domain",
            records,
            [
                row
                for row in records
                if row.get("frequency") != expected_frequency
                or not all(_decimal_gt_zero(row.get(field)) for field in ("open", "high", "low", "close"))
            ],
        ),
        _rule(
            f"{prefix}-004",
            domain,
            "error",
            "high/low must be consistent with open and close",
            records,
            [row for row in records if not _ohlc_relation_is_valid(row)],
        ),
        _rule(
            f"{prefix}-005",
            domain,
            "error" if prefix == "DLY" else "warning",
            "volume and amount must be non-negative",
            records,
            [
                row
                for row in records
                if not _decimal_gte_zero(row.get("volume")) or not _decimal_gte_zero(row.get("amount"))
            ],
        ),
    ]
    if expected_frequency == Frequency.DAILY.value:
        results.append(
            _rule(
                "DLY-006",
                domain,
                "warning",
                "pct_chg should match (close - pre_close) / pre_close * 100",
                records,
                [row for row in records if not _pct_chg_is_valid(row)],
            )
        )
    return results


def validate_social_posts(records: list[Mapping[str, Any]]) -> list[ValidationRuleResult]:
    return [
        _rule(
            "SOC-001",
            "social",
            "error",
            "(post_id, source) must be non-empty and unique",
            records,
            _social_key_duplicate_failures(records),
        ),
        _rule(
            "SOC-002",
            "social",
            "error",
            "created_at must be non-empty and parseable",
            records,
            [row for row in records if not _datetime_is_valid(row.get("created_at"))],
        ),
        _rule(
            "SOC-003",
            "social",
            "error",
            "text must be non-empty",
            records,
            [row for row in records if _is_blank(row.get("text"))],
        ),
        _rule(
            "SOC-005",
            "social",
            "warning",
            "engagement counts should be non-negative when present",
            records,
            [
                row
                for row in records
                if any(
                    not _optional_decimal_gte_zero(row.get(field))
                    for field in (
                        "like_count",
                        "repost_count",
                        "reply_count",
                        "quote_count",
                        "view_count",
                    )
                )
            ],
        ),
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate standardized AI3 data")
    parser.add_argument(
        "--domain",
        choices=("instrument", "market_daily", "market_weekly", "social"),
        required=True,
    )
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--instruments-csv-path", default=None)
    parser.add_argument("--daily-bars-csv-path", default=None)
    parser.add_argument("--weekly-bars-csv-path", default=None)
    parser.add_argument("--output-json", default=None)
    parser.add_argument(
        "--read-db",
        action="store_true",
        help="Read from MySQL through repositories. Default validates CSV inputs or an empty dry-run repository.",
    )
    return parser


def build_repositories(
    args: argparse.Namespace,
) -> tuple[InstrumentRepository, MarketRepository, SocialRepository]:
    if not args.read_db:
        writer = InMemoryRecordWriter()
        return InstrumentRepository(writer), MarketRepository(writer), SocialRepository(writer)

    config = load_database_config()
    connection = connect_mysql(config)
    writer = MySqlRecordWriter(connection)
    return InstrumentRepository(writer), MarketRepository(writer), SocialRepository(writer)


def load_csv_records(args: argparse.Namespace) -> list[dict[str, Any]] | None:
    provider = CsvProvider(
        instruments_path=args.instruments_csv_path,
        daily_bars_path=args.daily_bars_csv_path,
        weekly_bars_path=args.weekly_bars_csv_path,
    )
    if args.domain == "instrument" and args.instruments_csv_path:
        return normalize_instruments(provider.fetch_instruments(), source=DataSource.CSV)
    if args.domain == "market_daily" and args.daily_bars_csv_path:
        raw = provider.fetch_daily_bars(args.symbol, args.start_date or "", args.end_date or "99999999")
        return normalize_market_bars(raw, source=DataSource.CSV, frequency=Frequency.DAILY)
    if args.domain == "market_weekly" and args.weekly_bars_csv_path:
        raw = provider.fetch_weekly_bars(args.symbol, args.start_date or "", args.end_date or "99999999")
        return normalize_market_bars(raw, source=DataSource.CSV, frequency=Frequency.WEEKLY)
    return None


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    instrument_repo, market_repo, social_repo = build_repositories(args)
    csv_records = load_csv_records(args)
    summary = run(
        domain=args.domain,
        instrument_repository=instrument_repo,
        market_repository=market_repo,
        social_repository=social_repo,
        records=csv_records,
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    payload = summary.to_dict()
    LOGGER.info("summary=%s", payload)
    if args.output_json:
        _write_json(Path(args.output_json), payload)
    return 0 if summary.passed else 1


def _load_domain_records(
    *,
    domain: str,
    instrument_repository: InstrumentRepository | None,
    market_repository: MarketRepository | None,
    social_repository: SocialRepository | None,
    records: list[Mapping[str, Any]] | None,
    symbol: str | None,
    start_date: str | None,
    end_date: str | None,
) -> list[Mapping[str, Any]]:
    if records is not None:
        return records
    if domain == "instrument":
        if instrument_repository is None:
            return []
        return instrument_repository.load_all_instruments()
    if domain == "market_daily":
        if market_repository is None:
            return []
        return market_repository.load_daily_bars(symbol=symbol, start_date=start_date, end_date=end_date)
    if domain == "market_weekly":
        if market_repository is None:
            return []
        return market_repository.load_weekly_bars(symbol=symbol, start_date=start_date, end_date=end_date)
    if domain == "social":
        if social_repository is None:
            return []
        return social_repository.load_posts()
    raise ValueError(f"Unsupported validation domain: {domain}")


def _rule(
    rule_id: str,
    domain: str,
    severity: str,
    message: str,
    records: list[Mapping[str, Any]],
    failures: list[Mapping[str, Any]],
) -> ValidationRuleResult:
    failed_count = len(failures)
    return ValidationRuleResult(
        rule_id=rule_id,
        domain=domain,
        severity=severity,
        message=message,
        passed_count=len(records) - failed_count,
        failed_count=failed_count,
        samples=[dict(row) for row in failures[:MAX_SAMPLES]],
    )


def _info(
    rule_id: str,
    domain: str,
    message: str,
    records: list[Mapping[str, Any]],
    details: dict[str, Any],
) -> ValidationRuleResult:
    return ValidationRuleResult(
        rule_id=rule_id,
        domain=domain,
        severity="info",
        message=message,
        passed_count=len(records),
        failed_count=0,
        samples=[details] if details else [],
    )


def _instrument_symbol_non_empty_unique_failures(
    records: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    counts = Counter(row.get("symbol") for row in records)
    return [
        row
        for row in records
        if _is_blank(row.get("symbol")) or counts[row.get("symbol")] > 1
    ]


def _market_key_duplicate_failures(records: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    keys = [
        (row.get("symbol"), row.get("trade_date"), row.get("frequency"), row.get("source"))
        for row in records
    ]
    counts = Counter(keys)
    return [row for row, key in zip(records, keys) if any(_is_blank(value) for value in key) or counts[key] > 1]


def _social_key_duplicate_failures(records: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    keys = [(row.get("post_id"), row.get("source")) for row in records]
    counts = Counter(keys)
    return [row for row, key in zip(records, keys) if any(_is_blank(value) for value in key) or counts[key] > 1]


def _trade_date_failures(
    records: list[Mapping[str, Any]],
    *,
    require_monday: bool,
) -> list[Mapping[str, Any]]:
    failures: list[Mapping[str, Any]] = []
    for row in records:
        trade_date = row.get("trade_date")
        if not _date_is_empty_or_valid(trade_date, allow_empty=False):
            failures.append(row)
            continue
        if require_monday and week_monday(str(trade_date)) != str(trade_date):
            failures.append(row)
    return failures


def _ohlc_relation_is_valid(row: Mapping[str, Any]) -> bool:
    open_ = _decimal_or_none(row.get("open"))
    high = _decimal_or_none(row.get("high"))
    low = _decimal_or_none(row.get("low"))
    close = _decimal_or_none(row.get("close"))
    if None in (open_, high, low, close):
        return False
    return high >= open_ and high >= close and low <= open_ and low <= close


def _pct_chg_is_valid(row: Mapping[str, Any]) -> bool:
    close = _decimal_or_none(row.get("close"))
    pre_close = _decimal_or_none(row.get("pre_close"))
    pct_chg = _decimal_or_none(row.get("pct_chg"))
    if close is None or pre_close in (None, Decimal("0")) or pct_chg is None:
        return True
    expected = (close - pre_close) / pre_close * Decimal("100")
    return abs(expected - pct_chg) <= PCT_CHG_TOLERANCE


def _delist_date_is_valid(row: Mapping[str, Any]) -> bool:
    list_date = row.get("list_date")
    delist_date = row.get("delist_date")
    if not _date_is_empty_or_valid(delist_date):
        return False
    if _is_blank(list_date) or _is_blank(delist_date):
        return True
    return str(delist_date) >= str(list_date)


def _date_is_empty_or_valid(
    value: Any,
    *,
    allow_empty: bool = True,
    max_today: bool = False,
) -> bool:
    if _is_blank(value):
        return allow_empty
    text = str(value)
    if not DATE_RE.fullmatch(text):
        return False
    try:
        datetime.strptime(text, "%Y%m%d")
    except ValueError:
        return False
    if max_today and text > datetime.now().strftime("%Y%m%d"):
        return False
    return True


def _matches(pattern: re.Pattern[str], value: Any) -> bool:
    return not _is_blank(value) and bool(pattern.fullmatch(str(value)))


def _decimal_gt_zero(value: Any) -> bool:
    decimal_value = _decimal_or_none(value)
    return decimal_value is not None and decimal_value > 0


def _decimal_gte_zero(value: Any) -> bool:
    decimal_value = _decimal_or_none(value)
    return decimal_value is not None and decimal_value >= 0


def _optional_decimal_gte_zero(value: Any) -> bool:
    decimal_value = _decimal_or_none(value)
    return decimal_value is None or decimal_value >= 0


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _datetime_is_valid(value: Any) -> bool:
    if _is_blank(value):
        return False
    text = str(value).strip()
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
