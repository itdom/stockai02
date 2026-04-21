from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from backtest.repositories.holding_return_repo import HoldingReturnRepository


def test_holding_return_repository_saves_results() -> None:
    writer = InMemoryRecordWriter()
    repo = HoldingReturnRepository(writer)

    saved = repo.save_results(
        [
            {
                "symbol": "000001.SZ",
                "signal_date": "20260102",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
                "horizon": 5,
                "return_pct": "10",
            }
        ]
    )

    assert saved == 1
    records = repo.load_results()
    assert records[0]["symbol"] == "000001.SZ"
    assert set(records[0]) == set(repo.table.fields)


def test_holding_return_repository_deletes_signal_date_window() -> None:
    writer = InMemoryRecordWriter()
    repo = HoldingReturnRepository(writer)
    repo.save_results(
        [
            {
                "symbol": "000001.SZ",
                "signal_date": "20260102",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
                "horizon": 5,
            },
            {
                "symbol": "000001.SZ",
                "signal_date": "20260202",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
                "horizon": 5,
            },
            {
                "symbol": "600000.SH",
                "signal_date": "20260102",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
                "horizon": 5,
            },
        ]
    )

    deleted = repo.delete_results_window(
        start_date="20260101",
        end_date="20260131",
        symbol="000001.SZ",
    )

    assert deleted == 1
    assert [(row["symbol"], row["signal_date"]) for row in repo.load_results()] == [
        ("000001.SZ", "20260202"),
        ("600000.SH", "20260102"),
    ]
