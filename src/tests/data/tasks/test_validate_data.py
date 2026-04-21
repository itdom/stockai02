from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from data.repositories.instrument_repo import InstrumentRepository
from data.repositories.market_repo import MarketRepository
from data.tasks.validate_data import (
    main,
    run,
    validate_instruments,
    validate_market_bars,
    validate_social_posts,
)


def test_validate_instruments_reports_duplicate_and_bad_symbol_errors() -> None:
    records = [
        {"symbol": "000001.SZ", "name": "Ping An", "list_date": "20200101"},
        {"symbol": "000001.SZ", "name": "Duplicate", "list_date": "20200101"},
        {"symbol": "bad", "name": "", "list_date": "29990101"},
    ]

    results = validate_instruments(records)

    by_id = {result.rule_id: result for result in results}
    assert by_id["INS-001"].failed_count == 2
    assert by_id["INS-002"].failed_count == 1
    assert by_id["INS-003"].failed_count == 1
    assert by_id["INS-004"].failed_count == 1


def test_validate_daily_market_bars_reports_key_ohlc_and_pct_errors() -> None:
    records = [
        {
            "symbol": "000001.SZ",
            "trade_date": "20260413",
            "frequency": "1d",
            "open": "10",
            "high": "11",
            "low": "9",
            "close": "10.5",
            "pre_close": "10",
            "pct_chg": "5",
            "volume": "100",
            "amount": "1000",
            "source": "csv",
        },
        {
            "symbol": "000001.SZ",
            "trade_date": "20260413",
            "frequency": "1d",
            "open": "10",
            "high": "9",
            "low": "11",
            "close": "10.5",
            "pre_close": "10",
            "pct_chg": "1",
            "volume": "-1",
            "amount": "1000",
            "source": "csv",
        },
    ]

    results = validate_market_bars(records, domain="market_daily", expected_frequency="1d")

    by_id = {result.rule_id: result for result in results}
    assert by_id["DLY-001"].failed_count == 2
    assert by_id["DLY-004"].failed_count == 1
    assert by_id["DLY-005"].failed_count == 1
    assert by_id["DLY-006"].failed_count == 1


def test_validate_weekly_market_bars_requires_monday_trade_date() -> None:
    records = [
        {
            "symbol": "000001.SZ",
            "trade_date": "20260414",
            "frequency": "1w",
            "open": "10",
            "high": "11",
            "low": "9",
            "close": "10.5",
            "volume": "100",
            "amount": "1000",
            "source": "csv",
        }
    ]

    results = validate_market_bars(records, domain="market_weekly", expected_frequency="1w")

    by_id = {result.rule_id: result for result in results}
    assert by_id["WKY-001"].failed_count == 1


def test_validate_social_posts_reports_key_datetime_text_and_count_errors() -> None:
    records = [
        {
            "post_id": "tweet-1",
            "source": "x",
            "created_at": "2026-04-20T00:00:00+00:00",
            "text": "AI3",
            "like_count": 1,
        },
        {
            "post_id": "tweet-1",
            "source": "x",
            "created_at": "bad",
            "text": "",
            "like_count": -1,
        },
    ]

    results = validate_social_posts(records)

    by_id = {result.rule_id: result for result in results}
    assert by_id["SOC-001"].failed_count == 2
    assert by_id["SOC-002"].failed_count == 1
    assert by_id["SOC-003"].failed_count == 1
    assert by_id["SOC-005"].failed_count == 1


def test_run_loads_records_from_repositories() -> None:
    writer = InMemoryRecordWriter()
    instrument_repo = InstrumentRepository(writer)
    market_repo = MarketRepository(writer)
    instrument_repo.save_instruments(
        [
            {
                "symbol": "000001.SZ",
                "name": "Ping An",
                "market": "SZ",
                "exchange": "SZ",
                "asset_type": "stock",
                "source": "csv",
            }
        ]
    )

    summary = run(
        domain="instrument",
        instrument_repository=instrument_repo,
        market_repository=market_repo,
    )

    assert summary.checked_count == 1
    assert summary.error_count == 0
    assert summary.passed is True


def test_main_validates_csv_fixture_and_empty_dry_run_repository() -> None:
    exit_code = main(
        [
            "--domain",
            "market_daily",
            "--daily-bars-csv-path",
            "src/tests/fixtures/daily_bars.csv",
            "--start-date",
            "20260101",
            "--end-date",
            "20260131",
            "--symbol",
            "000001.SZ",
        ]
    )

    assert exit_code == 0
    assert main(["--domain", "market_daily"]) == 0
