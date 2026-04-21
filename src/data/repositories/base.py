"""Shared repository writer abstractions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from data.storage.table_registry import TableSpec


class RecordWriter(Protocol):
    def upsert(self, table: TableSpec, records: list[dict[str, Any]]) -> int:
        ...

    def all_records_for_table(self, table: TableSpec) -> list[dict[str, Any]]:
        ...

    def delete_where(
        self,
        table: TableSpec,
        *,
        equals: Mapping[str, Any] | None = None,
        ranges: Mapping[str, tuple[Any | None, Any | None]] | None = None,
    ) -> int:
        ...


class InMemoryRecordWriter:
    """Small writer used by tests and dry-run task execution."""

    def __init__(self) -> None:
        self.tables: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = {}

    def upsert(self, table: TableSpec, records: list[dict[str, Any]]) -> int:
        rows = self.tables.setdefault(table.name, {})
        for record in records:
            key = tuple(record[field] for field in table.primary_key)
            rows[key] = record
        return len(records)

    def delete_where(
        self,
        table: TableSpec,
        *,
        equals: Mapping[str, Any] | None = None,
        ranges: Mapping[str, tuple[Any | None, Any | None]] | None = None,
    ) -> int:
        rows = self.tables.get(table.name, {})
        keys_to_delete = [
            key
            for key, record in rows.items()
            if _matches_filters(record, equals=equals, ranges=ranges)
        ]
        for key in keys_to_delete:
            del rows[key]
        return len(keys_to_delete)

    def all_records(self, table_name: str) -> list[dict[str, Any]]:
        rows = self.tables.get(table_name, {})
        return [rows[key] for key in sorted(rows)]

    def all_records_for_table(self, table: TableSpec) -> list[dict[str, Any]]:
        return self.all_records(table.name)


def _matches_filters(
    record: Mapping[str, Any],
    *,
    equals: Mapping[str, Any] | None,
    ranges: Mapping[str, tuple[Any | None, Any | None]] | None,
) -> bool:
    for field, expected in (equals or {}).items():
        if record.get(field) != expected:
            return False
    for field, (start, end) in (ranges or {}).items():
        value = record.get(field)
        if value is None:
            return False
        if start is not None and value < start:
            return False
        if end is not None and value > end:
            return False
    return True
