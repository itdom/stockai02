"""Storage sink helpers shared by repositories."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from data.storage.table_registry import TableSpec


def normalize_null(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def align_record(record: Mapping[str, Any], table: TableSpec) -> dict[str, Any]:
    return {field: normalize_null(record.get(field)) for field in table.fields}


def align_records(records: list[Mapping[str, Any]], table: TableSpec) -> list[dict[str, Any]]:
    return [align_record(record, table) for record in records]
