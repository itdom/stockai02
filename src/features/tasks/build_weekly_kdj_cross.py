"""Build weekly KDJ golden-cross signals from KDJ feature records."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Sequence

from common.logger import configure_logging, get_logger
from data.repositories.base import InMemoryRecordWriter
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql
from features.repositories.kdj_repo import KdjFeatureRepository
from features.repositories.signal_repo import KdjCrossSignalRepository
from features.signals.kdj_cross import detect_kdj_golden_cross


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class BuildWeeklyKdjCrossResult:
    feature_count: int
    signal_count: int
    saved_count: int
    deleted_count: int
    signals: list[dict]


def run(
    kdj_repository: KdjFeatureRepository,
    signal_repository: KdjCrossSignalRepository | None = None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    symbol: str | None = None,
    overwrite: bool = False,
) -> BuildWeeklyKdjCrossResult:
    LOGGER.info(
        "build_weekly_kdj_cross started symbol=%s start_date=%s end_date=%s",
        symbol,
        start_date,
        end_date,
    )
    features = kdj_repository.load_features(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        frequency="1w",
    )
    signals = detect_kdj_golden_cross(features)
    deleted_count = 0
    if overwrite and signal_repository is not None:
        _require_overwrite_window(start_date, end_date)
        deleted_count = signal_repository.delete_signals_window(
            start_date=start_date or "",
            end_date=end_date or "",
            frequency="1w",
            symbol=symbol,
        )
    saved_count = signal_repository.save_signals(signals) if signal_repository is not None else 0
    result = BuildWeeklyKdjCrossResult(
        feature_count=len(features),
        signal_count=len(signals),
        saved_count=saved_count,
        deleted_count=deleted_count,
        signals=signals,
    )
    LOGGER.info(
        "build_weekly_kdj_cross finished features=%s signals=%s deleted=%s saved=%s",
        result.feature_count,
        result.signal_count,
        result.deleted_count,
        result.saved_count,
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build weekly KDJ golden-cross signals")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete existing signal rows in the requested window before writing recomputed signals.",
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Read/write MySQL. By default the task uses an empty dry-run memory repository.",
    )
    return parser


def build_repositories(args: argparse.Namespace) -> tuple[KdjFeatureRepository, KdjCrossSignalRepository]:
    if not args.write_db:
        writer = InMemoryRecordWriter()
        return KdjFeatureRepository(writer), KdjCrossSignalRepository(writer)

    config = load_database_config()
    connection = connect_mysql(config)
    writer = MySqlRecordWriter(connection)
    return KdjFeatureRepository(writer), KdjCrossSignalRepository(writer)


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    kdj_repository, signal_repository = build_repositories(args)
    result = run(
        kdj_repository,
        signal_repository,
        start_date=args.start_date,
        end_date=args.end_date,
        symbol=args.symbol,
        overwrite=args.overwrite,
    )
    LOGGER.info(
        "summary features=%s signals=%s deleted=%s saved=%s",
        result.feature_count,
        result.signal_count,
        result.deleted_count,
        result.saved_count,
    )
    return 0


def _require_overwrite_window(start_date: str | None, end_date: str | None) -> None:
    if not start_date or not end_date:
        raise ValueError("--overwrite requires both --start-date and --end-date")


if __name__ == "__main__":
    raise SystemExit(main())
