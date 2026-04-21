from __future__ import annotations

from pathlib import Path

from data.providers.csv_provider import CsvProvider
from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository
from data.tasks.ingest_market_weekly import (
    build_parser,
    build_repository,
    main,
    resolve_task_date_window,
    run,
)


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def test_run_ingest_market_weekly_with_csv_provider() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    provider = CsvProvider(weekly_bars_path=FIXTURES / "weekly_bars.csv")

    result = run(
        provider,
        repo,
        start_date="20260101",
        end_date="20260131",
        symbol="000001.SZ",
    )

    assert result.provider == "csv"
    assert result.fetched_count == 1
    assert result.normalized_count == 1
    assert result.saved_count == 1
    assert repo.load_weekly_bars()[0]["frequency"] == "1w"
    assert repo.load_weekly_bars()[0]["trade_date"] == "20260105"


def test_main_supports_csv_provider() -> None:
    exit_code = main(
        [
            "--provider",
            "csv",
            "--csv-path",
            str(FIXTURES / "weekly_bars.csv"),
            "--start-date",
            "20260101",
            "--end-date",
            "20260131",
            "--symbol",
            "000001.SZ",
            "--limit",
            "1",
        ]
    )

    assert exit_code == 0


def test_resolve_task_date_window_supports_increment_mode() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    repo.save_weekly_bars(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260105",
                "frequency": "1w",
                "source": "csv",
            }
        ]
    )
    args = build_parser().parse_args(
        [
            "--provider",
            "csv",
            "--csv-path",
            str(FIXTURES / "weekly_bars.csv"),
            "--mode",
            "increment",
            "--end-date",
            "20260131",
            "--symbol",
            "000001.SZ",
        ]
    )

    window = resolve_task_date_window(args, repo)

    assert window.start_date == "20260106"
    assert window.end_date == "20260131"


def test_build_repository_defaults_to_dry_run_writer() -> None:
    args = build_parser().parse_args(
        [
            "--provider",
            "csv",
            "--csv-path",
            "unused.csv",
            "--start-date",
            "20260101",
            "--end-date",
            "20260131",
        ]
    )

    repo = build_repository(args)

    assert isinstance(repo.writer, InMemoryRecordWriter)
