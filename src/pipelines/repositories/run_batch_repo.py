"""Repository for pipeline execution batch records."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from data.repositories.base import RecordWriter
from data.storage.sinks import align_records
from data.storage.table_registry import TableSpec


PIPELINE_RUN_BATCH_TABLE = TableSpec(
    name="pipeline_run_batch",
    fields=(
        "run_id",
        "pipeline_name",
        "started_at",
        "finished_at",
        "status",
        "duration_seconds",
        "parameters_json",
        "metrics_json",
        "failed_dates_json",
        "error_message",
    ),
    primary_key=("run_id",),
)


@dataclass(frozen=True)
class PipelineRunBatchHandle:
    run_id: str
    pipeline_name: str
    started_at: str
    started_monotonic: float
    parameters_json: str


class PipelineRunBatchRepository:
    def __init__(self, writer: RecordWriter) -> None:
        self.writer = writer
        self.table = PIPELINE_RUN_BATCH_TABLE

    def start_run(
        self,
        *,
        pipeline_name: str,
        parameters: Mapping[str, Any],
    ) -> PipelineRunBatchHandle:
        handle = PipelineRunBatchHandle(
            run_id=str(uuid.uuid4()),
            pipeline_name=pipeline_name,
            started_at=_now_iso(),
            started_monotonic=time.perf_counter(),
            parameters_json=_to_json(parameters),
        )
        self._save(
            {
                "run_id": handle.run_id,
                "pipeline_name": handle.pipeline_name,
                "started_at": handle.started_at,
                "finished_at": None,
                "status": "running",
                "duration_seconds": None,
                "parameters_json": handle.parameters_json,
                "metrics_json": None,
                "failed_dates_json": "[]",
                "error_message": None,
            }
        )
        return handle

    def finish_run(
        self,
        handle: PipelineRunBatchHandle,
        *,
        status: str,
        failed_dates: Sequence[str] = (),
        metrics: Mapping[str, Any] | None = None,
        error_message: str | None = None,
    ) -> int:
        duration_seconds = round(time.perf_counter() - handle.started_monotonic, 6)
        return self._save(
            {
                "run_id": handle.run_id,
                "pipeline_name": handle.pipeline_name,
                "started_at": handle.started_at,
                "finished_at": _now_iso(),
                "status": status,
                "duration_seconds": duration_seconds,
                "parameters_json": handle.parameters_json,
                "metrics_json": _to_json(metrics) if metrics is not None else None,
                "failed_dates_json": _to_json(list(failed_dates)),
                "error_message": _trim_error(error_message),
            }
        )

    def load_recent_runs(
        self,
        *,
        limit: int = 10,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        records = self.writer.all_records_for_table(self.table)
        if status is not None:
            records = [record for record in records if record.get("status") == status]
        return sorted(records, key=lambda record: str(record.get("started_at") or ""), reverse=True)[:limit]

    def _save(self, record: Mapping[str, Any]) -> int:
        aligned = align_records([record], self.table)
        return self.writer.upsert(self.table, aligned)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _trim_error(value: str | None) -> str | None:
    if value is None:
        return None
    return value[:1000]
