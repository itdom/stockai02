from __future__ import annotations

import pytest

from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository
from features.repositories.signal_repo import KdjCrossSignalRepository
from backtest.repositories.holding_return_repo import HoldingReturnRepository
from backtest.tasks.run_holding_return import build_repositories, build_parser, main, parse_horizons, run


def test_run_holding_return_saves_results() -> None:
    writer = InMemoryRecordWriter()
    signal_repo = KdjCrossSignalRepository(writer)
    market_repo = MarketRepository(writer)
    result_repo = HoldingReturnRepository(writer)
    signal_repo.save_signals(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260102",
                "frequency": "1w",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
            }
        ]
    )
    market_repo.save_daily_bars(
        [
            {"symbol": "000001.SZ", "trade_date": "20260102", "frequency": "1d", "close": "10", "source": "csv"},
            {"symbol": "000001.SZ", "trade_date": "20260105", "frequency": "1d", "close": "11", "source": "csv"},
        ]
    )

    result = run(signal_repo, market_repo, result_repo, horizons=(1,))

    assert result.signal_count == 1
    assert result.daily_count == 2
    assert result.result_count == 1
    assert result.saved_count == 1
    assert result_repo.load_results()[0]["return_pct"] == 10


def test_parse_horizons() -> None:
    assert parse_horizons("5,10,20") == (5, 10, 20)


def test_main_defaults_to_empty_dry_run_repository() -> None:
    assert main([]) == 0


def test_build_repositories_defaults_to_dry_run_writer() -> None:
    args = build_parser().parse_args([])
    signal_repo, market_repo, result_repo = build_repositories(args)

    assert isinstance(signal_repo.writer, InMemoryRecordWriter)
    assert market_repo.writer is signal_repo.writer
    assert result_repo.writer is signal_repo.writer


def test_run_holding_return_overwrite_deletes_window_before_save() -> None:
    writer = InMemoryRecordWriter()
    signal_repo = KdjCrossSignalRepository(writer)
    market_repo = MarketRepository(writer)
    result_repo = HoldingReturnRepository(writer)
    result_repo.save_results(
        [
            {
                "symbol": "000001.SZ",
                "signal_date": "20260102",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
                "horizon": 1,
                "return_pct": "10",
            }
        ]
    )

    result = run(
        signal_repo,
        market_repo,
        result_repo,
        start_date="20260101",
        end_date="20260131",
        horizons=(1,),
        overwrite=True,
    )

    assert result.deleted_count == 1
    assert result.result_count == 0
    assert result_repo.load_results() == []


def test_run_holding_return_overwrite_requires_window() -> None:
    writer = InMemoryRecordWriter()

    with pytest.raises(ValueError, match="--overwrite requires"):
        run(
            KdjCrossSignalRepository(writer),
            MarketRepository(writer),
            HoldingReturnRepository(writer),
            overwrite=True,
        )
