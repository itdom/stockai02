from __future__ import annotations

from pathlib import Path
from typing import Any

from data.providers.base import MarketDataProvider
from data.providers.csv_provider import CsvProvider
from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository
from data.tasks.ingest_market_daily import (
    build_parser,
    build_repository,
    main,
    resolve_task_date_window,
    run,
    run_daily_range,
)


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


class FakeDailyProvider(MarketDataProvider):
    source_name = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str | None, str, str]] = []

    def fetch_instruments(self) -> list[dict[str, Any]]:
        return []

    def fetch_daily_bars(
        self,
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        self.calls.append((symbol, start_date, end_date))
        if start_date == "20260102":
            raise RuntimeError("temporary provider error")
        if start_date == "20260103":
            return []
        return [
            {
                "symbol": symbol or "000001.SZ",
                "trade_date": start_date,
                "open": "10",
                "high": "11",
                "low": "9",
                "close": "10",
                "source": "fake",
            }
        ]

    def fetch_weekly_bars(
        self,
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        return []


def test_run_ingest_market_daily_with_csv_provider() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    provider = CsvProvider(daily_bars_path=FIXTURES / "daily_bars.csv")

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
    assert repo.load_daily_bars()[0]["symbol"] == "000001.SZ"


def test_run_daily_range_fetches_one_calendar_date_at_a_time_and_continues_after_failure() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    provider = FakeDailyProvider()

    result = run_daily_range(
        provider,
        repo,
        start_date="20260101",
        end_date="20260103",
        symbol="000001.SZ",
    )

    assert provider.calls == [
        ("000001.SZ", "20260101", "20260101"),
        ("000001.SZ", "20260102", "20260102"),
        ("000001.SZ", "20260103", "20260103"),
    ]
    assert result.processed_dates == 3
    assert result.failed_dates == ("20260102",)
    assert result.fetched_count == 1
    assert result.saved_count == 1


def test_run_daily_range_applies_limit_across_the_whole_window() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    provider = FakeDailyProvider()

    result = run_daily_range(
        provider,
        repo,
        start_date="20260101",
        end_date="20260103",
        limit=1,
    )

    assert provider.calls == [(None, "20260101", "20260101")]
    assert result.processed_dates == 1
    assert result.fetched_count == 1


def test_main_supports_csv_provider() -> None:
    exit_code = main(
        [
            "--provider",
            "csv",
            "--csv-path",
            str(FIXTURES / "daily_bars.csv"),
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


def test_resolve_task_date_window_supports_increment_mode() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    repo.save_daily_bars(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260102",
                "frequency": "1d",
                "source": "csv",
            }
        ]
    )
    args = build_parser().parse_args(
        [
            "--provider",
            "csv",
            "--csv-path",
            str(FIXTURES / "daily_bars.csv"),
            "--mode",
            "increment",
            "--end-date",
            "20260131",
            "--symbol",
            "000001.SZ",
        ]
    )

    window = resolve_task_date_window(args, repo)

    assert window.start_date == "20260103"
    assert window.end_date == "20260131"
