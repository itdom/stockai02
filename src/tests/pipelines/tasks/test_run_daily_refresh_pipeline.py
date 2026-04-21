from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from backtest.repositories.holding_return_repo import HoldingReturnRepository
from data.providers.csv_provider import CsvProvider
from data.repositories.base import InMemoryRecordWriter
from data.repositories.instrument_repo import InstrumentRepository
from data.repositories.market_repo import MarketRepository
from features.repositories.kdj_repo import KdjFeatureRepository
from features.repositories.signal_repo import KdjCrossSignalRepository
from pipelines.repositories.run_batch_repo import PipelineRunBatchRepository
from pipelines.tasks.run_daily_refresh_pipeline import (
    PipelineRepositories,
    build_parser,
    build_repositories,
    main,
    parse_validation_domains,
    run,
    summarize_result,
)


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def test_daily_refresh_pipeline_runs_csv_end_to_end() -> None:
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
        overwrite=True,
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


def test_daily_refresh_pipeline_can_validate_data_domains() -> None:
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
        validate_data=True,
    )

    assert [summary.domain for summary in result.validation_summaries] == [
        "instrument",
        "market_daily",
        "market_weekly",
    ]
    assert all(summary.passed for summary in result.validation_summaries)


def test_daily_refresh_pipeline_records_batch_status_and_parameters() -> None:
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
        pipeline_run_repository=PipelineRunBatchRepository(writer),
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
        overwrite=True,
        validate_data=True,
    )

    records = writer.all_records("pipeline_run_batch")
    assert len(records) == 1
    record = records[0]
    assert record["run_id"] == result.pipeline_run_id
    assert record["pipeline_name"] == "daily_refresh_pipeline"
    assert record["status"] == "success"
    assert record["finished_at"] is not None
    assert record["duration_seconds"] is not None
    assert json.loads(record["failed_dates_json"]) == []
    parameters = json.loads(record["parameters_json"])
    metrics = json.loads(record["metrics_json"])
    assert parameters["market_provider"] == "csv"
    assert parameters["start_date"] == "20260101"
    assert parameters["end_date"] == "20260131"
    assert parameters["symbol"] == "000001.SZ"
    assert parameters["overwrite"] is True
    assert parameters["validate_data"] is True
    assert metrics["signals_saved"] == 1
    assert metrics["holding_returns_saved"] == 2


def test_daily_refresh_pipeline_main_supports_csv_fixture() -> None:
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
            "--overwrite",
            "--validate-data",
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
    assert repositories.pipeline_run_repository is not None


def test_parse_validation_domains_rejects_domains_outside_pipeline_data_scope() -> None:
    assert parse_validation_domains("instrument,market_daily") == ("instrument", "market_daily")

    try:
        parse_validation_domains("social")
    except ValueError as exc:
        assert "Unsupported pipeline validation domain" in str(exc)
    else:
        raise AssertionError("Expected unsupported validation domain to fail")


def test_summarize_result_omits_large_feature_and_return_payloads() -> None:
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

    summary = summarize_result(result)

    assert summary["kdj_saved"] == 3
    assert summary["signals_saved"] == 1
    assert summary["holding_returns_saved"] == 2
    assert "features" not in summary
    assert "results" not in summary
