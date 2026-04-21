from __future__ import annotations

from data.services.trading_calendar import TradingCalendar


def test_trading_calendar_uses_weekday_fallback() -> None:
    calendar = TradingCalendar()

    assert calendar.trading_days("20260102", "20260105") == ["20260102", "20260105"]
    assert calendar.is_trading_day("20260103") is False
    assert calendar.next_trading_day("20260102") == "20260105"
    assert calendar.previous_trading_day("20260105") == "20260102"
