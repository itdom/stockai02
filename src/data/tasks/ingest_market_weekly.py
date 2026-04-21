"""Ingest standardized weekly market bars from external providers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Sequence

from common.logger import configure_logging, get_logger
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
class IngestMarketWeeklyResult:
    provider: str
    mode: str
    start_date: str
    end_date: str
    fetched_count: int
    normalized_count: int
    saved_count: int


def run(
    provider: MarketDataProvider,
    repository: MarketRepository,
    *,
    start_date: str,
    end_date: str,
    mode: str = "range",
    symbol: str | None = None,
    limit: int | None = None,
) -> IngestMarketWeeklyResult:
    LOGGER.info(
        "ingest_market_weekly started provider=%s symbol=%s mode=%s start_date=%s end_date=%s limit=%s",
        provider.source_name,
        symbol,
        mode,
        start_date,
        end_date,
        limit,
    )
    raw_rows = provider.fetch_weekly_bars(symbol, start_date, end_date)
    if limit is not None:
        raw_rows = raw_rows[:limit]

    normalized = normalize_market_bars(
        raw_rows,
        source=provider.source_name,
        frequency=Frequency.WEEKLY,
    )
    saved_count = repository.save_weekly_bars(normalized)
    result = IngestMarketWeeklyResult(
        provider=provider.source_name,
        mode=mode,
        start_date=start_date,
        end_date=end_date,
        fetched_count=len(raw_rows),
        normalized_count=len(normalized),
        saved_count=saved_count,
    )
    LOGGER.info(
        "ingest_market_weekly finished provider=%s fetched=%s normalized=%s saved=%s",
        result.provider,
        result.fetched_count,
        result.normalized_count,
        result.saved_count,
    )
    return result


def build_provider(args: argparse.Namespace) -> MarketDataProvider:
    if args.provider == "csv":
        return CsvProvider(weekly_bars_path=args.csv_path)
    if args.provider == "tushare":
        return TushareProvider()
    if args.provider == "akshare":
        return AkshareProvider()
    raise ValueError(f"Unsupported provider: {args.provider}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest A-share weekly market bars")
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
        max_trade_date = repository.get_max_weekly_trade_date(symbol=args.symbol)
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
    result = run(
        provider,
        repository,
        start_date=window.start_date,
        end_date=window.end_date,
        mode=window.mode,
        symbol=args.symbol,
        limit=args.limit,
    )
    LOGGER.info("summary=%s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
