"""Trading calendar service used by data services and backtests."""

from __future__ import annotations

from datetime import timedelta

from common.timeutils import format_yyyymmdd, parse_yyyymmdd
from common.timeutils import trading_day_range


class TradingCalendar:
    """Lightweight weekday calendar until an exchange calendar source is added."""

    def trading_days(self, start_date: str, end_date: str) -> list[str]:
        return trading_day_range(start_date, end_date)

    def is_trading_day(self, value: str) -> bool:
        return value in trading_day_range(value, value)

    def next_trading_day(self, value: str, *, days: int = 1) -> str | None:
        current = parse_yyyymmdd(value)
        found = 0
        while found < days:
            current += timedelta(days=1)
            text = format_yyyymmdd(current)
            if self.is_trading_day(text):
                found += 1
        return format_yyyymmdd(current)

    def previous_trading_day(self, value: str, *, days: int = 1) -> str | None:
        current = parse_yyyymmdd(value)
        found = 0
        while found < days:
            current -= timedelta(days=1)
            text = format_yyyymmdd(current)
            if self.is_trading_day(text):
                found += 1
        return format_yyyymmdd(current)
