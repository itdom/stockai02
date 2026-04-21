from __future__ import annotations

from datetime import date

from common.timeutils import normalize_trade_date, trading_day_range, week_monday


def test_normalize_trade_date() -> None:
    assert normalize_trade_date(date(2026, 4, 19)) == "20260419"
    assert normalize_trade_date("20260419") == "20260419"


def test_week_monday() -> None:
    assert week_monday("20260419") == "20260413"


def test_trading_day_range_uses_weekdays() -> None:
    assert trading_day_range("20260418", "20260421") == ["20260420", "20260421"]
