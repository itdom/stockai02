from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository


def test_save_daily_bars_aligns_fields_and_upserts() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)

    saved = repo.save_daily_bars(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260102",
                "frequency": "1d",
                "source": "csv",
                "close": "10",
                "extra": "ignored",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "20260102",
                "frequency": "1d",
                "source": "csv",
                "close": "10.1",
            },
        ]
    )

    assert saved == 2
    records = repo.load_daily_bars()
    assert len(records) == 1
    assert records[0]["close"] == "10.1"
    assert "extra" not in records[0]
    assert set(records[0]) == set(repo.daily_table.fields)


def test_load_daily_bars_filters_symbol_and_dates() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    repo.save_daily_bars(
        [
            {"symbol": "000001.SZ", "trade_date": "20260102", "frequency": "1d", "source": "csv"},
            {"symbol": "000001.SZ", "trade_date": "20260103", "frequency": "1d", "source": "csv"},
            {"symbol": "600000.SH", "trade_date": "20260103", "frequency": "1d", "source": "csv"},
        ]
    )

    records = repo.load_daily_bars(
        symbol="000001.SZ",
        start_date="20260103",
        end_date="20260131",
    )

    assert [(row["symbol"], row["trade_date"]) for row in records] == [
        ("000001.SZ", "20260103")
    ]


def test_get_max_trade_dates() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    repo.save_daily_bars(
        [
            {"symbol": "000001.SZ", "trade_date": "20260102", "frequency": "1d", "source": "csv"},
            {"symbol": "000001.SZ", "trade_date": "20260103", "frequency": "1d", "source": "csv"},
        ]
    )
    repo.save_weekly_bars(
        [
            {"symbol": "000001.SZ", "trade_date": "20260105", "frequency": "1w", "source": "csv"},
            {"symbol": "600000.SH", "trade_date": "20260112", "frequency": "1w", "source": "csv"},
        ]
    )

    assert repo.get_max_daily_trade_date(symbol="000001.SZ") == "20260103"
    assert repo.get_max_weekly_trade_date() == "20260112"
