"""Ingest standardized stock instruments."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Sequence

from common.logger import configure_logging, get_logger
from data.normalizers.instrument_normalizer import normalize_instruments
from data.providers.akshare_provider import AkshareProvider
from data.providers.base import MarketDataProvider
from data.providers.csv_provider import CsvProvider
from data.providers.tushare_provider import TushareProvider
from data.repositories.base import InMemoryRecordWriter
from data.repositories.instrument_repo import InstrumentRepository
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class IngestStockListResult:
    provider: str
    fetched_count: int
    normalized_count: int
    saved_count: int


def run(
    provider: MarketDataProvider,
    repository: InstrumentRepository,
    *,
    limit: int | None = None,
) -> IngestStockListResult:
    LOGGER.info("ingest_stock_list started provider=%s limit=%s", provider.source_name, limit)
    raw_rows = provider.fetch_instruments()
    if limit is not None:
        raw_rows = raw_rows[:limit]

    normalized = normalize_instruments(raw_rows, source=provider.source_name)
    saved_count = repository.save_instruments(normalized)
    result = IngestStockListResult(
        provider=provider.source_name,
        fetched_count=len(raw_rows),
        normalized_count=len(normalized),
        saved_count=saved_count,
    )
    LOGGER.info(
        "ingest_stock_list finished provider=%s fetched=%s normalized=%s saved=%s",
        result.provider,
        result.fetched_count,
        result.normalized_count,
        result.saved_count,
    )
    return result


def build_provider(args: argparse.Namespace) -> MarketDataProvider:
    if args.provider == "csv":
        return CsvProvider(instruments_path=args.csv_path)
    if args.provider == "tushare":
        return TushareProvider()
    if args.provider == "akshare":
        return AkshareProvider()
    raise ValueError(f"Unsupported provider: {args.provider}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest A-share stock list")
    parser.add_argument("--provider", choices=("csv", "tushare", "akshare"), required=True)
    parser.add_argument("--csv-path", help="CSV path used when --provider csv")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Write to MySQL. By default the task runs in dry-run memory mode.",
    )
    return parser


def build_repository(args: argparse.Namespace) -> InstrumentRepository:
    if not args.write_db:
        return InstrumentRepository(InMemoryRecordWriter())

    config = load_database_config()
    connection = connect_mysql(config)
    return InstrumentRepository(MySqlRecordWriter(connection))


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    provider = build_provider(args)
    repository = build_repository(args)
    result = run(provider, repository, limit=args.limit)
    LOGGER.info("summary=%s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
