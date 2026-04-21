"""Repository for standardized raw social posts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from data.repositories.base import RecordWriter
from data.storage.sinks import align_records
from data.storage.table_registry import get_table_spec


class SocialRepository:
    def __init__(self, writer: RecordWriter) -> None:
        self.writer = writer
        self.post_table = get_table_spec("raw_social_post")

    def save_posts(self, records: list[Mapping[str, Any]]) -> int:
        aligned = align_records(records, self.post_table)
        if not aligned:
            return 0
        return self.writer.upsert(self.post_table, aligned)

    def load_posts(
        self,
        *,
        start_time: str | None = None,
        end_time: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        if not hasattr(self.writer, "all_records"):
            raise NotImplementedError("Current writer does not support reads")
        records = self.writer.all_records(self.post_table.name)  # type: ignore[attr-defined]
        return _filter_posts(records, start_time=start_time, end_time=end_time, query=query)


def _filter_posts(
    records: list[dict[str, Any]],
    *,
    start_time: str | None,
    end_time: str | None,
    query: str | None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for record in records:
        if query is not None and record.get("query") != query:
            continue
        created_at = record.get("created_at")
        if start_time is not None and created_at is not None and created_at < start_time:
            continue
        if end_time is not None and created_at is not None and created_at >= end_time:
            continue
        filtered.append(record)
    return filtered
