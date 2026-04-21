from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository
from data.services.market_data_service import MarketDataService


def test_market_data_service_reads_standardized_bars_and_max_dates() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    repo.save_daily_bars(
        [
            {"symbol": "000001.SZ", "trade_date": "20260102", "frequency": "1d", "source": "csv"},
            {"symbol": "600000.SH", "trade_date": "20260103", "frequency": "1d", "source": "csv"},
        ]
    )
    service = MarketDataService(repo)

    rows = service.get_daily_bars(symbol="000001.SZ")

    assert [row["symbol"] for row in rows] == ["000001.SZ"]
    assert service.get_max_daily_trade_date() == "20260103"


def test_market_data_service_get_daily_window_after_uses_calendar() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    repo.save_daily_bars(
        [
            {"symbol": "000001.SZ", "trade_date": "20260102", "frequency": "1d", "source": "csv"},
            {"symbol": "000001.SZ", "trade_date": "20260105", "frequency": "1d", "source": "csv"},
        ]
    )
    service = MarketDataService(repo)

    rows = service.get_daily_window_after(symbol="000001.SZ", trade_date="20260102", days=1)

    assert [row["trade_date"] for row in rows] == ["20260102", "20260105"]
