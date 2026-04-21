"""Build weekly bars from standardized daily bars."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Sequence

from common.logger import configure_logging, get_logger
from common.timeutils import week_monday
from data.contracts.enums import Frequency
from data.contracts.market import MARKET_BAR_FIELDS
from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class BuildWeeklyBarsResult:
    daily_count: int
    weekly_count: int
    saved_count: int


def run(
    repository: MarketRepository,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    symbol: str | None = None,
) -> BuildWeeklyBarsResult:
    LOGGER.info(
        "build_weekly_bars started symbol=%s start_date=%s end_date=%s",
        symbol,
        start_date,
        end_date,
    )
    daily_bars = repository.load_daily_bars(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )
    weekly_bars = aggregate_daily_to_weekly(daily_bars)
    saved_count = repository.save_weekly_bars(weekly_bars)
    result = BuildWeeklyBarsResult(
        daily_count=len(daily_bars),
        weekly_count=len(weekly_bars),
        saved_count=saved_count,
    )
    LOGGER.info(
        "build_weekly_bars finished daily=%s weekly=%s saved=%s",
        result.daily_count,
        result.weekly_count,
        result.saved_count,
    )
    return result


def aggregate_daily_to_weekly(
    daily_bars: list[Mapping[str, Any]],
    *,
    ingested_at: str | None = None,
) -> list[dict[str, Any]]:
    timestamp = ingested_at or datetime.now(timezone.utc).isoformat()
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)

    for row in daily_bars:
        if row.get("frequency") != Frequency.DAILY.value:
            continue
        symbol = row.get("symbol")
        trade_date = row.get("trade_date")
        source = row.get("source")
        if not symbol or not trade_date or not source:
            continue
        groups[(str(symbol), week_monday(str(trade_date)), str(source))].append(row)

    weekly: list[dict[str, Any]] = []
    for (symbol, trade_date, source), rows in sorted(groups.items()):
        sorted_rows = sorted(rows, key=lambda item: str(item.get("trade_date")))
        pre_close = _first_non_null(sorted_rows, "pre_close")
        close = _last_non_null(sorted_rows, "close")
        change = _subtract(close, pre_close)
        weekly.append(
            {
                "symbol": symbol,
                "trade_date": trade_date,
                "frequency": Frequency.WEEKLY.value,
                "open": _first_non_null(sorted_rows, "open"),
                "high": _max_non_null(sorted_rows, "high"),
                "low": _min_non_null(sorted_rows, "low"),
                "close": close,
                "pre_close": pre_close,
                "change": change,
                "pct_chg": _pct_change(change, pre_close),
                "volume": _sum_non_null(sorted_rows, "volume"),
                "amount": _sum_non_null(sorted_rows, "amount"),
                "source": source,
                "ingested_at": timestamp,
            }
        )

    return [{field: row.get(field) for field in MARKET_BAR_FIELDS} for row in weekly]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build weekly market bars from daily bars")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Read/write MySQL. By default the task uses an empty dry-run memory repository.",
    )
    return parser


def build_repository(args: argparse.Namespace) -> MarketRepository:
    if not args.write_db:
        return MarketRepository(InMemoryRecordWriter())

    config = load_database_config()
    connection = connect_mysql(config)
    return MarketRepository(MySqlRecordWriter(connection))


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    repository = build_repository(args)
    result = run(
        repository,
        start_date=args.start_date,
        end_date=args.end_date,
        symbol=args.symbol,
    )
    LOGGER.info("summary=%s", result)
    return 0


def _first_non_null(rows: list[Mapping[str, Any]], field: str) -> Decimal | None:
    for row in rows:
        value = _decimal_or_none(row.get(field))
        if value is not None:
            return value
    return None


def _last_non_null(rows: list[Mapping[str, Any]], field: str) -> Decimal | None:
    for row in reversed(rows):
        value = _decimal_or_none(row.get(field))
        if value is not None:
            return value
    return None


def _max_non_null(rows: list[Mapping[str, Any]], field: str) -> Decimal | None:
    values = [_decimal_or_none(row.get(field)) for row in rows]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def _min_non_null(rows: list[Mapping[str, Any]], field: str) -> Decimal | None:
    values = [_decimal_or_none(row.get(field)) for row in rows]
    values = [value for value in values if value is not None]
    return min(values) if values else None


def _sum_non_null(rows: list[Mapping[str, Any]], field: str) -> Decimal | None:
    values = [_decimal_or_none(row.get(field)) for row in rows]
    values = [value for value in values if value is not None]
    return sum(values, Decimal("0")) if values else None


def _subtract(value: Any, base: Any) -> Decimal | None:
    decimal_value = _decimal_or_none(value)
    decimal_base = _decimal_or_none(base)
    if decimal_value is None or decimal_base is None:
        return None
    return decimal_value - decimal_base


def _pct_change(change: Any, base: Any) -> Decimal | None:
    decimal_change = _decimal_or_none(change)
    decimal_base = _decimal_or_none(base)
    if decimal_change is None or decimal_base in (None, Decimal("0")):
        return None
    return (decimal_change / decimal_base) * Decimal("100")


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value: {text}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
