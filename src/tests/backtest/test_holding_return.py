from __future__ import annotations

from decimal import Decimal

import pytest

from backtest.holding_return import calculate_holding_returns


def test_calculate_holding_returns_uses_first_bar_on_or_after_signal() -> None:
    signals = [
        {
            "symbol": "000001.SZ",
            "trade_date": "20260102",
            "signal_type": "kdj_golden_cross",
            "source": "csv",
        }
    ]
    daily_bars = [
        {"symbol": "000001.SZ", "trade_date": "20260101", "close": "9", "source": "csv"},
        {"symbol": "000001.SZ", "trade_date": "20260105", "close": "10", "source": "csv"},
        {"symbol": "000001.SZ", "trade_date": "20260106", "close": "11", "source": "csv"},
        {"symbol": "000001.SZ", "trade_date": "20260107", "close": "12", "source": "csv"},
    ]

    result = calculate_holding_returns(signals, daily_bars, horizons=(1, 2, 5), created_at="x")

    assert result == [
        {
            "symbol": "000001.SZ",
            "signal_date": "20260102",
            "signal_type": "kdj_golden_cross",
            "source": "csv",
            "entry_date": "20260105",
            "entry_close": Decimal("10"),
            "horizon": 1,
            "exit_date": "20260106",
            "exit_close": Decimal("11"),
            "return_pct": Decimal("10.0"),
            "created_at": "x",
        },
        {
            "symbol": "000001.SZ",
            "signal_date": "20260102",
            "signal_type": "kdj_golden_cross",
            "source": "csv",
            "entry_date": "20260105",
            "entry_close": Decimal("10"),
            "horizon": 2,
            "exit_date": "20260107",
            "exit_close": Decimal("12"),
            "return_pct": Decimal("20.0"),
            "created_at": "x",
        },
        {
            "symbol": "000001.SZ",
            "signal_date": "20260102",
            "signal_type": "kdj_golden_cross",
            "source": "csv",
            "entry_date": "20260105",
            "entry_close": Decimal("10"),
            "horizon": 5,
            "exit_date": None,
            "exit_close": None,
            "return_pct": None,
            "created_at": "x",
        },
    ]


def test_calculate_holding_returns_skips_missing_entry_close() -> None:
    result = calculate_holding_returns(
        [{"symbol": "000001.SZ", "trade_date": "20260102", "signal_type": "x", "source": "csv"}],
        [{"symbol": "000001.SZ", "trade_date": "20260102", "source": "csv"}],
    )

    assert result == []


def test_calculate_holding_returns_rejects_bad_close() -> None:
    with pytest.raises(ValueError, match="Invalid numeric value"):
        calculate_holding_returns(
            [{"symbol": "000001.SZ", "trade_date": "20260102", "signal_type": "x", "source": "csv"}],
            [{"symbol": "000001.SZ", "trade_date": "20260102", "close": "bad", "source": "csv"}],
        )
