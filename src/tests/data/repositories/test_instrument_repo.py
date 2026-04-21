from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from data.repositories.instrument_repo import InstrumentRepository


def test_save_instruments_aligns_fields_and_upserts() -> None:
    writer = InMemoryRecordWriter()
    repo = InstrumentRepository(writer)

    saved = repo.save_instruments(
        [
            {"symbol": "000001.SZ", "name": "平安银行", "extra": "ignored"},
            {"symbol": "000001.SZ", "name": "平安银行A"},
        ]
    )

    assert saved == 2
    records = repo.load_all_instruments()
    assert len(records) == 1
    assert records[0]["symbol"] == "000001.SZ"
    assert records[0]["name"] == "平安银行A"
    assert "extra" not in records[0]
    assert set(records[0]) == set(repo.table.fields)
