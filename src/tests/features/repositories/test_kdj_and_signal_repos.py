from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from features.repositories.kdj_repo import KdjFeatureRepository
from features.repositories.signal_repo import KdjCrossSignalRepository


def test_kdj_feature_repository_saves_and_filters() -> None:
    writer = InMemoryRecordWriter()
    repo = KdjFeatureRepository(writer)

    saved = repo.save_features(
        [
            {"symbol": "000001.SZ", "trade_date": "20260105", "frequency": "1w", "source": "csv", "k": "40"},
            {"symbol": "000001.SZ", "trade_date": "20260112", "frequency": "1w", "source": "csv", "k": "50"},
            {"symbol": "600000.SH", "trade_date": "20260112", "frequency": "1w", "source": "csv", "k": "60"},
        ]
    )

    assert saved == 3
    records = repo.load_features(symbol="000001.SZ", start_date="20260110", frequency="1w")
    assert [(row["symbol"], row["trade_date"], row["k"]) for row in records] == [
        ("000001.SZ", "20260112", "50")
    ]
    assert set(records[0]) == set(repo.table.fields)


def test_signal_repository_saves_and_filters() -> None:
    writer = InMemoryRecordWriter()
    repo = KdjCrossSignalRepository(writer)

    saved = repo.save_signals(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260105",
                "frequency": "1w",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
            },
            {
                "symbol": "600000.SH",
                "trade_date": "20260112",
                "frequency": "1w",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
            },
        ]
    )

    assert saved == 2
    records = repo.load_signals(symbol="000001.SZ", frequency="1w")
    assert len(records) == 1
    assert records[0]["symbol"] == "000001.SZ"
    assert set(records[0]) == set(repo.table.fields)


def test_signal_repository_deletes_window() -> None:
    writer = InMemoryRecordWriter()
    repo = KdjCrossSignalRepository(writer)
    repo.save_signals(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260105",
                "frequency": "1w",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "20260202",
                "frequency": "1w",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "20260112",
                "frequency": "1d",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
            },
        ]
    )

    deleted = repo.delete_signals_window(
        start_date="20260101",
        end_date="20260131",
        frequency="1w",
    )

    assert deleted == 1
    assert [(row["trade_date"], row["frequency"]) for row in repo.load_signals()] == [
        ("20260112", "1d"),
        ("20260202", "1w"),
    ]
