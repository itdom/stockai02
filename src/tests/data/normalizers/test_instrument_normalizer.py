from __future__ import annotations

import pytest

from data.normalizers.instrument_normalizer import (
    infer_market,
    normalize_date,
    normalize_instruments,
    normalize_symbol,
)


def test_normalize_symbol() -> None:
    assert normalize_symbol("000001") == "000001.SZ"
    assert normalize_symbol("600000") == "600000.SH"
    assert normalize_symbol("830799") == "830799.BJ"
    assert normalize_symbol("000001.sz") == "000001.SZ"


def test_infer_market_rejects_unknown_prefix() -> None:
    with pytest.raises(ValueError, match="Cannot infer market"):
        infer_market("110000")


def test_normalize_date() -> None:
    assert normalize_date("2026-04-19") == "20260419"
    assert normalize_date("20260419") == "20260419"
    assert normalize_date("") is None


def test_normalize_instruments_deduplicates_and_sorts() -> None:
    rows = [
        {"ts_code": "600000.SH", "name": "浦发银行", "list_date": "1999-11-10"},
        {"symbol": "000001.SZ", "name": "平安银行", "industry": "银行"},
        {"symbol": "000001.SZ", "name": "平安银行A", "industry": "银行"},
    ]

    result = normalize_instruments(rows, source="csv", ingested_at="2026-04-19T00:00:00+00:00")

    assert [row["symbol"] for row in result] == ["000001.SZ", "600000.SH"]
    assert result[0]["name"] == "平安银行A"
    assert result[0]["market"] == "SZ"
    assert result[0]["asset_type"] == "stock"
    assert result[0]["source"] == "csv"
    assert result[1]["list_date"] == "19991110"
