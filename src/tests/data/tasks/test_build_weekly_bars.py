from __future__ import annotations

from decimal import Decimal

from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository
from data.tasks.build_weekly_bars import (
    aggregate_daily_to_weekly,
    build_parser,
    build_repository,
    main,
    run,
)


def test_aggregate_daily_to_weekly_uses_monday_and_ohlcv_rules() -> None:
    daily = [
        {
            "symbol": "000001.SZ",
            "trade_date": "20260413",
            "frequency": "1d",
            "open": None,
            "high": Decimal("10"),
            "low": Decimal("9"),
            "close": Decimal("9.5"),
            "pre_close": Decimal("10"),
            "volume": None,
            "amount": Decimal("100"),
            "source": "csv",
        },
        {
            "symbol": "000001.SZ",
            "trade_date": "20260414",
            "frequency": "1d",
            "open": Decimal("9.6"),
            "high": None,
            "low": Decimal("9.4"),
            "close": None,
            "pre_close": None,
            "volume": Decimal("100"),
            "amount": None,
            "source": "csv",
        },
        {
            "symbol": "000001.SZ",
            "trade_date": "20260417",
            "frequency": "1d",
            "open": Decimal("10"),
            "high": Decimal("12"),
            "low": None,
            "close": Decimal("11.5"),
            "pre_close": Decimal("9.5"),
            "volume": Decimal("200"),
            "amount": Decimal("300"),
            "source": "csv",
        },
    ]

    weekly = aggregate_daily_to_weekly(daily, ingested_at="x")

    assert weekly == [
        {
            "symbol": "000001.SZ",
            "trade_date": "20260413",
            "frequency": "1w",
            "open": Decimal("9.6"),
            "high": Decimal("12"),
            "low": Decimal("9"),
            "close": Decimal("11.5"),
            "pre_close": Decimal("10"),
            "change": Decimal("1.5"),
            "pct_chg": Decimal("15.00"),
            "volume": Decimal("300"),
            "amount": Decimal("400"),
            "source": "csv",
            "ingested_at": "x",
        }
    ]


def test_aggregate_daily_to_weekly_keeps_all_missing_aggregates_empty() -> None:
    weekly = aggregate_daily_to_weekly(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260413",
                "frequency": "1d",
                "source": "csv",
            }
        ],
        ingested_at="x",
    )

    assert weekly[0]["open"] is None
    assert weekly[0]["high"] is None
    assert weekly[0]["low"] is None
    assert weekly[0]["close"] is None
    assert weekly[0]["volume"] is None
    assert weekly[0]["amount"] is None


def test_aggregate_daily_to_weekly_groups_symbol_week_and_source() -> None:
    weekly = aggregate_daily_to_weekly(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260413",
                "frequency": "1d",
                "close": "10",
                "source": "csv",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "20260414",
                "frequency": "1d",
                "close": "11",
                "source": "tushare",
            },
            {
                "symbol": "600000.SH",
                "trade_date": "20260415",
                "frequency": "1d",
                "close": "12",
                "source": "csv",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "20260415",
                "frequency": "1w",
                "close": "99",
                "source": "csv",
            },
        ],
        ingested_at="x",
    )

    assert [(row["symbol"], row["source"], row["close"]) for row in weekly] == [
        ("000001.SZ", "csv", Decimal("10")),
        ("000001.SZ", "tushare", Decimal("11")),
        ("600000.SH", "csv", Decimal("12")),
    ]


def test_run_build_weekly_bars_reads_daily_and_saves_weekly() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    repo.save_daily_bars(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260413",
                "frequency": "1d",
                "open": "10",
                "high": "11",
                "low": "9",
                "close": "10.5",
                "source": "csv",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "20260414",
                "frequency": "1d",
                "open": "10.5",
                "high": "12",
                "low": "10",
                "close": "11",
                "source": "csv",
            },
        ]
    )

    result = run(repo, symbol="000001.SZ", start_date="20260401", end_date="20260430")

    assert result.daily_count == 2
    assert result.weekly_count == 1
    assert result.saved_count == 1
    assert repo.load_weekly_bars()[0]["trade_date"] == "20260413"
    assert repo.load_weekly_bars()[0]["high"] == Decimal("12")


def test_main_defaults_to_empty_dry_run_repository() -> None:
    assert main([]) == 0


def test_build_repository_defaults_to_dry_run_writer() -> None:
    args = build_parser().parse_args([])

    repo = build_repository(args)

    assert isinstance(repo.writer, InMemoryRecordWriter)
