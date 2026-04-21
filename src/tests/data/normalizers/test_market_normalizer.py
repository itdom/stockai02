from __future__ import annotations

from decimal import Decimal

import pytest

from data.contracts.enums import Frequency
from data.normalizers.market_normalizer import normalize_market_bars


def test_normalize_market_bars_maps_fields_and_numbers() -> None:
    rows = [
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260102",
            "open": "9.90",
            "high": "10.20",
            "low": "9.80",
            "close": "10.00",
            "pre_close": "9.90",
            "change": "0.10",
            "pct_chg": "1.01",
            "vol": "1000",
            "amount": "10000",
        }
    ]

    result = normalize_market_bars(
        rows,
        source="csv",
        frequency=Frequency.DAILY,
        ingested_at="2026-04-19T00:00:00+00:00",
    )

    assert result == [
        {
            "symbol": "000001.SZ",
            "trade_date": "20260102",
            "frequency": "1d",
            "open": Decimal("9.90"),
            "high": Decimal("10.20"),
            "low": Decimal("9.80"),
            "close": Decimal("10.00"),
            "pre_close": Decimal("9.90"),
            "change": Decimal("0.10"),
            "pct_chg": Decimal("1.01"),
            "volume": Decimal("1000"),
            "amount": Decimal("10000"),
            "source": "csv",
            "ingested_at": "2026-04-19T00:00:00+00:00",
        }
    ]


def test_normalize_market_bars_deduplicates_and_sorts() -> None:
    rows = [
        {"symbol": "600000.SH", "trade_date": "20260102", "close": "10"},
        {"symbol": "000001.SZ", "trade_date": "20260102", "close": "9"},
        {"symbol": "000001.SZ", "trade_date": "20260102", "close": "9.1"},
    ]

    result = normalize_market_bars(rows, source="csv", frequency="1d", ingested_at="x")

    assert [row["symbol"] for row in result] == ["000001.SZ", "600000.SH"]
    assert result[0]["close"] == Decimal("9.1")


def test_normalize_market_bars_maps_akshare_fields() -> None:
    rows = [
        {
            "股票代码": "000001",
            "日期": "2024-01-02",
            "开盘": "9.39",
            "收盘": "9.21",
            "最高": "9.42",
            "最低": "9.16",
            "涨跌幅": "-1.81",
            "涨跌额": "-0.17",
            "成交量": "123",
            "成交额": "456",
        }
    ]

    result = normalize_market_bars(rows, source="akshare", frequency=Frequency.DAILY, ingested_at="x")

    assert result[0]["symbol"] == "000001.SZ"
    assert result[0]["trade_date"] == "20240102"
    assert result[0]["open"] == Decimal("9.39")
    assert result[0]["close"] == Decimal("9.21")


def test_normalize_weekly_bars_uses_monday() -> None:
    result = normalize_market_bars(
        [{"symbol": "000001.SZ", "trade_date": "20260419", "close": "10"}],
        source="csv",
        frequency=Frequency.WEEKLY,
        ingested_at="x",
    )

    assert result[0]["trade_date"] == "20260413"


def test_normalize_market_bars_rejects_bad_number() -> None:
    with pytest.raises(ValueError, match="Invalid numeric value"):
        normalize_market_bars(
            [{"symbol": "000001.SZ", "trade_date": "20260102", "close": "bad"}],
            source="csv",
            frequency="1d",
        )
