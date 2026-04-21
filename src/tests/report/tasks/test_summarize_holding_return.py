from __future__ import annotations

import json
from pathlib import Path

from backtest.repositories.holding_return_repo import HoldingReturnRepository
from data.repositories.base import InMemoryRecordWriter
from data.repositories.instrument_repo import InstrumentRepository
from report.tasks.summarize_holding_return import build_parser, build_repositories, main, render_markdown, run


def test_run_summarizes_holding_returns_by_horizon_date_and_industry() -> None:
    writer = InMemoryRecordWriter()
    result_repo = HoldingReturnRepository(writer)
    instrument_repo = InstrumentRepository(writer)
    instrument_repo.save_instruments(
        [
            {"symbol": "000001.SZ", "industry": "bank", "source": "csv"},
            {"symbol": "000002.SZ", "industry": "property", "source": "csv"},
        ]
    )
    result_repo.save_results(
        [
            {
                "symbol": "000001.SZ",
                "signal_date": "20260105",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
                "horizon": 5,
                "return_pct": "10",
            },
            {
                "symbol": "000002.SZ",
                "signal_date": "20260105",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
                "horizon": 5,
                "return_pct": "-5",
            },
            {
                "symbol": "000002.SZ",
                "signal_date": "20260112",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
                "horizon": 10,
                "return_pct": None,
            },
        ]
    )

    summary = run(
        result_repo,
        instrument_repo,
        start_date="20260101",
        end_date="20260131",
        source="csv",
    )

    assert summary.total_count == 3
    assert summary.completed_count == 2
    horizon_5 = {row.group: row for row in summary.by_horizon}["5"]
    assert horizon_5.total_count == 2
    assert horizon_5.completed_count == 2
    assert horizon_5.win_count == 1
    assert str(horizon_5.win_rate_pct) == "50.0"
    assert str(horizon_5.median_return_pct) == "2.5"
    assert {row.group for row in summary.by_signal_date} == {"20260105", "20260112"}
    assert {row.group for row in summary.by_industry} == {"bank", "property"}


def test_render_markdown_contains_expected_sections() -> None:
    writer = InMemoryRecordWriter()
    result_repo = HoldingReturnRepository(writer)
    result_repo.save_results(
        [
            {
                "symbol": "000001.SZ",
                "signal_date": "20260105",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
                "horizon": 5,
                "return_pct": "10",
            }
        ]
    )

    markdown = render_markdown(run(result_repo, None))

    assert "# Holding Return Summary" in markdown
    assert "## By Horizon" in markdown
    assert "## By Signal Date" in markdown
    assert "## By Industry" in markdown


def test_main_writes_json_report() -> None:
    output_path = Path("src/tests/fixtures/generated_holding_return_summary.json")

    try:
        exit_code = main(["--output-path", str(output_path), "--output-format", "json"])

        assert exit_code == 0
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload["total_count"] == 0
    finally:
        if output_path.exists():
            output_path.unlink()


def test_build_repositories_defaults_to_dry_run_writer() -> None:
    args = build_parser().parse_args([])

    result_repo, instrument_repo = build_repositories(args)

    assert isinstance(result_repo.writer, InMemoryRecordWriter)
    assert instrument_repo.writer is result_repo.writer
