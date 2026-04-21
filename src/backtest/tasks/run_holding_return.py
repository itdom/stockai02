"""Run holding return backtest from KDJ cross signals and daily bars."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Sequence

from backtest.holding_return import DEFAULT_HORIZONS, calculate_holding_returns
from backtest.repositories.holding_return_repo import HoldingReturnRepository
from common.logger import configure_logging, get_logger
from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql
from features.repositories.signal_repo import KdjCrossSignalRepository


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class RunHoldingReturnResult:
    signal_count: int
    daily_count: int
    result_count: int
    saved_count: int
    deleted_count: int
    results: list[dict]


def run(
    signal_repository: KdjCrossSignalRepository,
    market_repository: MarketRepository,
    result_repository: HoldingReturnRepository | None = None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    symbol: str | None = None,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    overwrite: bool = False,
) -> RunHoldingReturnResult:
    LOGGER.info(
        "run_holding_return started symbol=%s start_date=%s end_date=%s horizons=%s",
        symbol,
        start_date,
        end_date,
        horizons,
    )
    signals = signal_repository.load_signals(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        frequency="1w",
    )
    daily_bars = market_repository.load_daily_bars(symbol=symbol)
    results = calculate_holding_returns(signals, daily_bars, horizons=horizons)
    deleted_count = 0
    if overwrite and result_repository is not None:
        _require_overwrite_window(start_date, end_date)
        deleted_count = result_repository.delete_results_window(
            start_date=start_date or "",
            end_date=end_date or "",
            symbol=symbol,
        )
    saved_count = result_repository.save_results(results) if result_repository is not None else 0
    result = RunHoldingReturnResult(
        signal_count=len(signals),
        daily_count=len(daily_bars),
        result_count=len(results),
        saved_count=saved_count,
        deleted_count=deleted_count,
        results=results,
    )
    LOGGER.info(
        "run_holding_return finished signals=%s daily=%s results=%s deleted=%s saved=%s",
        result.signal_count,
        result.daily_count,
        result.result_count,
        result.deleted_count,
        result.saved_count,
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run holding return backtest")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--horizons", default="5,10,20,60")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete existing result rows in the requested signal-date window before writing recomputed results.",
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Read/write MySQL. By default the task uses an empty dry-run memory repository.",
    )
    return parser


def parse_horizons(value: str) -> tuple[int, ...]:
    horizons = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not horizons or any(item <= 0 for item in horizons):
        raise ValueError("horizons must contain positive integers")
    return horizons


def build_repositories(
    args: argparse.Namespace,
) -> tuple[KdjCrossSignalRepository, MarketRepository, HoldingReturnRepository]:
    if not args.write_db:
        writer = InMemoryRecordWriter()
        return (
            KdjCrossSignalRepository(writer),
            MarketRepository(writer),
            HoldingReturnRepository(writer),
        )

    config = load_database_config()
    connection = connect_mysql(config)
    writer = MySqlRecordWriter(connection)
    return (
        KdjCrossSignalRepository(writer),
        MarketRepository(writer),
        HoldingReturnRepository(writer),
    )


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    signal_repository, market_repository, result_repository = build_repositories(args)
    result = run(
        signal_repository,
        market_repository,
        result_repository,
        start_date=args.start_date,
        end_date=args.end_date,
        symbol=args.symbol,
        horizons=parse_horizons(args.horizons),
        overwrite=args.overwrite,
    )
    LOGGER.info(
        "summary results=%s deleted=%s saved=%s",
        result.result_count,
        result.deleted_count,
        result.saved_count,
    )
    return 0


def _require_overwrite_window(start_date: str | None, end_date: str | None) -> None:
    if not start_date or not end_date:
        raise ValueError("--overwrite requires both --start-date and --end-date")


if __name__ == "__main__":
    raise SystemExit(main())
