from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from pipelines.repositories.run_batch_repo import PipelineRunBatchRepository
from pipelines.tasks.summarize_pipeline_runs import main, run


def test_summarize_pipeline_runs_returns_recent_formatted_records() -> None:
    writer = InMemoryRecordWriter()
    repository = PipelineRunBatchRepository(writer)
    older = repository.start_run(
        pipeline_name="daily_refresh_pipeline",
        parameters={"market_provider": "csv", "start_date": "20260101", "end_date": "20260131"},
    )
    repository.finish_run(older, status="success")
    newer = repository.start_run(
        pipeline_name="daily_refresh_pipeline",
        parameters={
            "market_provider": "tushare",
            "symbol": "000001.SZ",
            "start_date": "20260413",
            "end_date": "20260417",
            "fetch_mode": "daily",
            "overwrite": True,
            "validate_data": True,
        },
    )
    repository.finish_run(newer, status="partial_success", failed_dates=("20260415",))

    records = run(repository, limit=1)

    assert len(records) == 1
    assert records[0]["run_id"] == newer.run_id
    assert records[0]["provider"] == "tushare"
    assert records[0]["symbol"] == "000001.SZ"
    assert records[0]["failed_dates"] == ["20260415"]
    assert records[0]["signals_saved"] is None


def test_summarize_pipeline_runs_main_supports_empty_dry_run(capsys) -> None:
    exit_code = main(["--limit", "3"])

    assert exit_code == 0
    assert "No pipeline runs found." in capsys.readouterr().out
