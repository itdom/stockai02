from __future__ import annotations

from decimal import Decimal

import pytest

from features.indicators.kdj import calculate_kdj


class FakeDataFrame:
    def __init__(self, rows):
        self.rows = rows

    def to_dict(self, orient):
        assert orient == "records"
        return self.rows


def test_calculate_kdj_uses_standard_smoothing() -> None:
    rows = [
        {
            "symbol": "000001.SZ",
            "trade_date": "20260105",
            "frequency": "1w",
            "high": "10",
            "low": "0",
            "close": "5",
            "source": "csv",
        },
        {
            "symbol": "000001.SZ",
            "trade_date": "20260112",
            "frequency": "1w",
            "high": "10",
            "low": "0",
            "close": "10",
            "source": "csv",
        },
    ]

    result = calculate_kdj(rows, n=2, ingested_at="x")

    assert result[0]["rsv"] == Decimal("50")
    assert result[0]["k"] == Decimal("50")
    assert result[0]["d"] == Decimal("50")
    assert result[0]["j"] == Decimal("50")
    assert result[1]["rsv"] == Decimal("100")
    assert result[1]["k"] == Decimal("66.66666666666666666666666667")
    assert result[1]["d"] == Decimal("55.55555555555555555555555557")
    assert result[1]["j"] == Decimal("88.8888888888888888888888889")


def test_calculate_kdj_accepts_dataframe_like_input() -> None:
    result = calculate_kdj(
        FakeDataFrame(
            [
                {
                    "symbol": "000001.SZ",
                    "trade_date": "20260105",
                    "frequency": "1w",
                    "high": "10",
                    "low": "10",
                    "close": "10",
                    "source": "csv",
                }
            ]
        ),
        ingested_at="x",
    )

    assert result[0]["rsv"] == Decimal("50")


def test_calculate_kdj_skips_missing_required_identity_fields() -> None:
    result = calculate_kdj(
        [
            {"trade_date": "20260105", "frequency": "1w", "source": "csv"},
            {"symbol": "000001.SZ", "trade_date": "20260105", "frequency": "1w", "source": "csv"},
        ],
        ingested_at="x",
    )

    assert len(result) == 1
    assert result[0]["rsv"] is None
    assert result[0]["k"] is None


def test_calculate_kdj_validates_periods() -> None:
    with pytest.raises(ValueError, match="n must be greater than 0"):
        calculate_kdj([], n=0)
