"""Ingest standardized daily market bars."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import timedelta
from typing import Sequence

from common.logger import configure_logging, get_logger
from common.timeutils import format_yyyymmdd, parse_yyyymmdd
from data.contracts.enums import Frequency
from data.normalizers.market_normalizer import normalize_market_bars
from data.providers.akshare_provider import AkshareProvider
from data.providers.base import MarketDataProvider
from data.providers.csv_provider import CsvProvider
from data.providers.tushare_provider import TushareProvider
from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql
from data.tasks.date_window import DateWindow, resolve_date_window


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class IngestMarketDailyResult:
    provider: str
    mode: str
    start_date: str
    end_date: str
    fetched_count: int
    normalized_count: int
    saved_count: int
    processed_dates: int = 1
    failed_dates: tuple[str, ...] = ()


def run(
    provider: MarketDataProvider,
    repository: MarketRepository,
    *,
    start_date: str,
    end_date: str,
    mode: str = "range",
    symbol: str | None = None,
    limit: int | None = None,
) -> IngestMarketDailyResult:
    LOGGER.info(
        "ingest_market_daily started provider=%s symbol=%s start_date=%s end_date=%s limit=%s",
        provider.source_name,
        symbol,
        start_date,
        end_date,
        limit,
    )
    raw_rows = provider.fetch_daily_bars(symbol, start_date, end_date)
    if limit is not None:
        raw_rows = raw_rows[:limit]

    normalized = normalize_market_bars(
        raw_rows,
        source=provider.source_name,
        frequency=Frequency.DAILY,
    )
    saved_count = repository.save_daily_bars(normalized)
    result = IngestMarketDailyResult(
        provider=provider.source_name,
        mode=mode,
        start_date=start_date,
        end_date=end_date,
        fetched_count=len(raw_rows),
        normalized_count=len(normalized),
        saved_count=saved_count,
    )
    LOGGER.info(
        "ingest_market_daily finished provider=%s fetched=%s normalized=%s saved=%s",
        result.provider,
        result.fetched_count,
        result.normalized_count,
        result.saved_count,
    )
    return result


def run_daily_range(
    provider: MarketDataProvider,
    repository: MarketRepository,
    *,
    start_date: str,
    end_date: str,
    mode: str = "range",
    symbol: str | None = None,
    limit: int | None = None,
) -> IngestMarketDailyResult:
    LOGGER.info(
        "ingest_market_daily daily-range started provider=%s symbol=%s start_date=%s end_date=%s limit=%s",
        provider.source_name,
        symbol,
        start_date,
        end_date,
        limit,
    )
    current = parse_yyyymmdd(start_date)
    end = parse_yyyymmdd(end_date)
    fetched_count = 0
    normalized_count = 0
    saved_count = 0
    processed_dates = 0
    failed_dates: list[str] = []

    while current <= end:
        trade_date = format_yyyymmdd(current)
        remaining_limit = None if limit is None else max(limit - fetched_count, 0)
        if remaining_limit == 0:
            break
        try:
            result = run(
                provider,
                repository,
                start_date=trade_date,
                end_date=trade_date,
                mode="date",
                symbol=symbol,
                limit=remaining_limit,
            )
        except Exception:
            LOGGER.exception("ingest_market_daily daily-range failed date=%s", trade_date)
            failed_dates.append(trade_date)
        else:
            fetched_count += result.fetched_count
            normalized_count += result.normalized_count
            saved_count += result.saved_count
        processed_dates += 1
        current += timedelta(days=1)

    result = IngestMarketDailyResult(
        provider=provider.source_name,
        mode=mode,
        start_date=start_date,
        end_date=end_date,
        fetched_count=fetched_count,
        normalized_count=normalized_count,
        saved_count=saved_count,
        processed_dates=processed_dates,
        failed_dates=tuple(failed_dates),
    )
    LOGGER.info(
        "ingest_market_daily daily-range finished provider=%s processed_dates=%s failed_dates=%s fetched=%s normalized=%s saved=%s",
        result.provider,
        result.processed_dates,
        len(result.failed_dates),
        result.fetched_count,
        result.normalized_count,
        result.saved_count,
    )
    return result


def build_provider(args: argparse.Namespace) -> MarketDataProvider:
    if args.provider == "csv":
        return CsvProvider(daily_bars_path=args.csv_path)
    if args.provider == "tushare":
        return TushareProvider()
    if args.provider == "akshare":
        return AkshareProvider()
    raise ValueError(f"Unsupported provider: {args.provider}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest A-share daily market bars")
    parser.add_argument("--provider", choices=("csv", "tushare", "akshare"), required=True)
    parser.add_argument("--csv-path", help="CSV path used when --provider csv")
    parser.add_argument(
        "--mode",
        choices=("range", "date", "increment", "all", "sample"),
        default="range",
    )
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--date", default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--fetch-mode",
        choices=("window", "daily"),
        default="window",
        help="window fetches the whole date window in one provider call; daily fetches one calendar date at a time.",
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Write to MySQL. By default the task runs in dry-run memory mode.",
    )
    return parser


def build_repository(args: argparse.Namespace) -> MarketRepository:
    if not args.write_db:
        return MarketRepository(InMemoryRecordWriter())

    config = load_database_config()
    connection = connect_mysql(config)
    return MarketRepository(MySqlRecordWriter(connection))


def resolve_task_date_window(args: argparse.Namespace, repository: MarketRepository) -> DateWindow:
    max_trade_date = None
    if args.mode == "increment":
        max_trade_date = repository.get_max_daily_trade_date(symbol=args.symbol)
    return resolve_date_window(
        mode=args.mode,
        start_date=args.start_date,
        end_date=args.end_date,
        date_value=args.date,
        max_trade_date=max_trade_date,
    )


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    provider = build_provider(args)
    repository = build_repository(args)
    window = resolve_task_date_window(args, repository)
    runner = run_daily_range if args.fetch_mode == "daily" else run
    result = runner(
        provider,
        repository,
        start_date=window.start_date,
        end_date=window.end_date,
        mode=window.mode,
        symbol=args.symbol,
        limit=args.limit,
    )
    LOGGER.info("summary=%s", result)
    return 1 if result.failed_dates else 0


if __name__ == "__main__":
    raise SystemExit(main())
