"""Repository for KDJ feature records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from data.repositories.base import RecordWriter
from data.storage.sinks import align_records
from data.storage.table_registry import get_table_spec


class KdjFeatureRepository:
    def __init__(self, writer: RecordWriter) -> None:
        self.writer = writer
        self.table = get_table_spec("feature_kdj")

    def save_features(self, records: list[Mapping[str, Any]]) -> int:
        aligned = align_records(records, self.table)
        if not aligned:
            return 0
        return self.writer.upsert(self.table, aligned)

    def load_features(
        self,
        *,
        symbol: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        frequency: str | None = None,
    ) -> list[dict[str, Any]]:
        if not hasattr(self.writer, "all_records"):
            raise NotImplementedError("Current writer does not support reads")
        records = self.writer.all_records(self.table.name)  # type: ignore[attr-defined]
        return _filter_records(
            records,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
        )


def _filter_records(
    records: list[dict[str, Any]],
    *,
    symbol: str | None,
    start_date: str | None,
    end_date: str | None,
    frequency: str | None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for record in records:
        if symbol is not None and record.get("symbol") != symbol:
            continue
        if frequency is not None and record.get("frequency") != frequency:
            continue
        trade_date = record.get("trade_date")
        if start_date is not None and trade_date is not None and trade_date < start_date:
            continue
        if end_date is not None and trade_date is not None and trade_date > end_date:
            continue
        filtered.append(record)
    return filtered
