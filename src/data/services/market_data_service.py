"""Read service for standardized market data."""

from __future__ import annotations

from typing import Any

from data.repositories.market_repo import MarketRepository
from data.services.trading_calendar import TradingCalendar


class MarketDataService:
    def __init__(
        self,
        repository: MarketRepository,
        *,
        trading_calendar: TradingCalendar | None = None,
    ) -> None:
        self.repository = repository
        self.trading_calendar = trading_calendar or TradingCalendar()

    def get_daily_bars(
        self,
        *,
        symbol: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.repository.load_daily_bars(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

    def get_weekly_bars(
        self,
        *,
        symbol: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.repository.load_weekly_bars(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

    def get_daily_window_after(
        self,
        *,
        symbol: str,
        trade_date: str,
        days: int,
    ) -> list[dict[str, Any]]:
        end_date = self.trading_calendar.next_trading_day(trade_date, days=days)
        if end_date is None:
            return []
        return self.get_daily_bars(symbol=symbol, start_date=trade_date, end_date=end_date)

    def get_max_daily_trade_date(self, *, symbol: str | None = None) -> str | None:
        return self.repository.get_max_daily_trade_date(symbol=symbol)

    def get_max_weekly_trade_date(self, *, symbol: str | None = None) -> str | None:
        return self.repository.get_max_weekly_trade_date(symbol=symbol)
