from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from backtest.repositories.holding_return_repo import HoldingReturnRepository
from data.providers.csv_provider import CsvProvider
from data.repositories.base import InMemoryRecordWriter
from data.repositories.instrument_repo import InstrumentRepository
from data.repositories.market_repo import MarketRepository
from features.repositories.kdj_repo import KdjFeatureRepository
from features.repositories.signal_repo import KdjCrossSignalRepository
from strategy.tasks.run_weekly_kdj_backtest_pipeline import (
    PipelineRepositories,
    build_parser,
    build_repositories,
    main,
    run,
)


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def test_weekly_kdj_backtest_pipeline_runs_csv_end_to_end() -> None:
    writer = InMemoryRecordWriter()
    provider = CsvProvider(
        instruments_path=FIXTURES / "e2e_instruments.csv",
        daily_bars_path=FIXTURES / "e2e_daily_bars.csv",
    )
    repositories = PipelineRepositories(
        instrument_repository=InstrumentRepository(writer),
        market_repository=MarketRepository(writer),
        kdj_repository=KdjFeatureRepository(writer),
        signal_repository=KdjCrossSignalRepository(writer),
        holding_return_repository=HoldingReturnRepository(writer),
    )

    result = run(
        stock_provider=provider,
        market_provider=provider,
        repositories=repositories,
        start_date="20260101",
        end_date="20260131",
        symbol="000001.SZ",
        kdj_n=2,
        horizons=(1, 2),
    )

    assert result.stock_list.saved_count == 1
    assert result.market_daily.saved_count == 5
    assert result.weekly_bars.saved_count == 3
    assert result.weekly_kdj.saved_count == 3
    assert result.weekly_kdj_cross.saved_count == 1
    assert result.holding_return.saved_count == 2
    assert result.weekly_kdj_cross.signals[0]["trade_date"] == "20260119"
    assert [row["return_pct"] for row in result.holding_return.results] == [
        Decimal("10.0"),
        Decimal("20.0"),
    ]


def test_pipeline_main_supports_csv_fixture() -> None:
    exit_code = main(
        [
            "--provider",
            "csv",
            "--instruments-csv-path",
            str(FIXTURES / "e2e_instruments.csv"),
            "--daily-bars-csv-path",
            str(FIXTURES / "e2e_daily_bars.csv"),
            "--start-date",
            "20260101",
            "--end-date",
            "20260131",
            "--symbol",
            "000001.SZ",
            "--kdj-n",
            "2",
            "--horizons",
            "1,2",
        ]
    )

    assert exit_code == 0


def test_build_repositories_defaults_to_dry_run_writer() -> None:
    args = build_parser().parse_args(
        [
            "--provider",
            "csv",
            "--start-date",
            "20260101",
            "--end-date",
            "20260131",
        ]
    )

    repositories = build_repositories(args)

    assert isinstance(repositories.market_repository.writer, InMemoryRecordWriter)
