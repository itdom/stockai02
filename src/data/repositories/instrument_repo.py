"""Repository for standardized instruments."""

from __future__ import annotations

from collections.abc import Mapping

from data.repositories.base import RecordWriter
from data.storage.sinks import align_records
from data.storage.table_registry import get_table_spec


class InstrumentRepository:
    def __init__(self, writer: RecordWriter) -> None:
        self.writer = writer
        self.table = get_table_spec("instrument")

    def save_instruments(self, records: list[Mapping[str, Any]]) -> int:
        aligned = align_records(records, self.table)
        if not aligned:
            return 0
        return self.writer.upsert(self.table, aligned)

    def load_all_instruments(self) -> list[dict[str, Any]]:
        if not hasattr(self.writer, "all_records"):
            raise NotImplementedError("Current writer does not support reads")
        return self.writer.all_records(self.table.name)  # type: ignore[attr-defined]
