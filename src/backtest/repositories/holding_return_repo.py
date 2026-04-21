"""Repository for holding return backtest results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from data.repositories.base import RecordWriter
from data.storage.sinks import align_records
from data.storage.table_registry import get_table_spec


class HoldingReturnRepository:
    def __init__(self, writer: RecordWriter) -> None:
        self.writer = writer
        self.table = get_table_spec("backtest_holding_return")

    def save_results(self, records: list[Mapping[str, Any]]) -> int:
        aligned = align_records(records, self.table)
        if not aligned:
            return 0
        return self.writer.upsert(self.table, aligned)

    def delete_results_window(
        self,
        *,
        start_date: str,
        end_date: str,
        symbol: str | None = None,
    ) -> int:
        equals: dict[str, Any] = {}
        if symbol is not None:
            equals["symbol"] = symbol
        return self.writer.delete_where(
            self.table,
            equals=equals,
            ranges={"signal_date": (start_date, end_date)},
        )

    def load_results(self) -> list[dict[str, Any]]:
        if not hasattr(self.writer, "all_records"):
            raise NotImplementedError("Current writer does not support reads")
        return self.writer.all_records(self.table.name)  # type: ignore[attr-defined]
