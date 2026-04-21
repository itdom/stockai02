"""Build weekly KDJ features from standardized weekly bars."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Sequence

from common.logger import configure_logging, get_logger
from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql
from features.indicators.kdj import calculate_kdj
from features.repositories.kdj_repo import KdjFeatureRepository


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class BuildWeeklyKdjResult:
    weekly_count: int
    feature_count: int
    saved_count: int
    features: list[dict]


def run(
    market_repository: MarketRepository,
    kdj_repository: KdjFeatureRepository | None = None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    symbol: str | None = None,
    n: int = 9,
) -> BuildWeeklyKdjResult:
    LOGGER.info(
        "build_weekly_kdj started symbol=%s start_date=%s end_date=%s n=%s",
        symbol,
        start_date,
        end_date,
        n,
    )
    weekly_bars = market_repository.load_weekly_bars(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )
    features = calculate_kdj(weekly_bars, n=n)
    saved_count = kdj_repository.save_features(features) if kdj_repository is not None else 0
    result = BuildWeeklyKdjResult(
        weekly_count=len(weekly_bars),
        feature_count=len(features),
        saved_count=saved_count,
        features=features,
    )
    LOGGER.info(
        "build_weekly_kdj finished weekly=%s features=%s saved=%s",
        result.weekly_count,
        result.feature_count,
        result.saved_count,
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build weekly KDJ features")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--n", type=int, default=9)
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Read MySQL. By default the task uses an empty dry-run memory repository.",
    )
    return parser


def build_repositories(args: argparse.Namespace) -> tuple[MarketRepository, KdjFeatureRepository | None]:
    if not args.write_db:
        writer = InMemoryRecordWriter()
        return MarketRepository(writer), KdjFeatureRepository(writer)

    config = load_database_config()
    connection = connect_mysql(config)
    writer = MySqlRecordWriter(connection)
    return MarketRepository(writer), KdjFeatureRepository(writer)


def build_repository(args: argparse.Namespace) -> MarketRepository:
    """Backward-compatible helper for tests and simple callers."""

    return build_repositories(args)[0]


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    market_repository, kdj_repository = build_repositories(args)
    result = run(
        market_repository,
        kdj_repository,
        start_date=args.start_date,
        end_date=args.end_date,
        symbol=args.symbol,
        n=args.n,
    )
    LOGGER.info(
        "summary weekly=%s features=%s saved=%s",
        result.weekly_count,
        result.feature_count,
        result.saved_count,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
