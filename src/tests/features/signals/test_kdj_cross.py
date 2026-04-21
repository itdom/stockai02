from __future__ import annotations

from decimal import Decimal

from features.signals.kdj_cross import SIGNAL_KDJ_GOLDEN_CROSS, detect_kdj_golden_cross


def test_detect_kdj_golden_cross() -> None:
    signals = detect_kdj_golden_cross(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260105",
                "frequency": "1w",
                "k": "40",
                "d": "50",
                "j": "20",
                "source": "csv",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "20260112",
                "frequency": "1w",
                "k": "55",
                "d": "50",
                "j": "65",
                "source": "csv",
            },
        ],
        created_at="x",
    )

    assert signals == [
        {
            "symbol": "000001.SZ",
            "trade_date": "20260112",
            "frequency": "1w",
            "signal_type": SIGNAL_KDJ_GOLDEN_CROSS,
            "k": Decimal("55"),
            "d": Decimal("50"),
            "j": Decimal("65"),
            "source": "csv",
            "created_at": "x",
        }
    ]


def test_detect_kdj_golden_cross_ignores_missing_values_and_non_crosses() -> None:
    signals = detect_kdj_golden_cross(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260105",
                "frequency": "1w",
                "k": None,
                "d": "50",
                "source": "csv",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "20260112",
                "frequency": "1w",
                "k": "45",
                "d": "50",
                "source": "csv",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "20260119",
                "frequency": "1w",
                "k": "46",
                "d": "50",
                "source": "csv",
            },
        ],
        created_at="x",
    )

    assert signals == []
