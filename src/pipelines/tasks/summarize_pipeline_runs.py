"""Summarize recent pipeline execution batches."""

from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

from common.logger import configure_logging, get_logger
from data.repositories.base import InMemoryRecordWriter, RecordWriter
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql
from pipelines.repositories.run_batch_repo import PipelineRunBatchRepository


LOGGER = get_logger(__name__)


def run(
    repository: PipelineRunBatchRepository,
    *,
    limit: int = 10,
    status: str | None = None,
) -> list[dict[str, Any]]:
    LOGGER.info("summarize_pipeline_runs started limit=%s status=%s", limit, status)
    records = [_format_record(record) for record in repository.load_recent_runs(limit=limit, status=status)]
    LOGGER.info("summarize_pipeline_runs finished rows=%s", len(records))
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize recent AI3 pipeline runs")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--status", default=None)
    parser.add_argument("--output-format", choices=("table", "json"), default="table")
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Read MySQL pipeline run batches. Default uses an empty dry-run memory repository.",
    )
    return parser


def build_repository(args: argparse.Namespace) -> PipelineRunBatchRepository:
    writer: RecordWriter
    if args.write_db:
        config = load_database_config()
        writer = MySqlRecordWriter(connect_mysql(config))
    else:
        writer = InMemoryRecordWriter()
    return PipelineRunBatchRepository(writer)


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    if args.limit <= 0:
        raise ValueError("--limit must be positive")
    records = run(build_repository(args), limit=args.limit, status=args.status)
    if args.output_format == "json":
        print(json.dumps(records, ensure_ascii=False, indent=2, default=str))
    else:
        print(_render_table(records))
    return 0


def _format_record(record: dict[str, Any]) -> dict[str, Any]:
    parameters = _parse_json(record.get("parameters_json"), default={})
    metrics = _parse_json(record.get("metrics_json"), default={})
    failed_dates = _parse_json(record.get("failed_dates_json"), default=[])
    return {
        "run_id": record.get("run_id"),
        "pipeline_name": record.get("pipeline_name"),
        "started_at": record.get("started_at"),
        "finished_at": record.get("finished_at"),
        "status": record.get("status"),
        "duration_seconds": record.get("duration_seconds"),
        "provider": parameters.get("market_provider"),
        "symbol": parameters.get("symbol"),
        "start_date": parameters.get("start_date"),
        "end_date": parameters.get("end_date"),
        "fetch_mode": parameters.get("fetch_mode"),
        "overwrite": parameters.get("overwrite"),
        "validate_data": parameters.get("validate_data"),
        "daily_saved": metrics.get("daily_saved"),
        "weekly_saved": metrics.get("weekly_saved"),
        "signals_saved": metrics.get("signals_saved"),
        "holding_returns_saved": metrics.get("holding_returns_saved"),
        "failed_dates": failed_dates,
        "error_message": record.get("error_message"),
    }


def _parse_json(value: Any, *, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return default


def _render_table(records: list[dict[str, Any]]) -> str:
    columns = (
        "started_at",
        "status",
        "duration_seconds",
        "provider",
        "symbol",
        "start_date",
        "end_date",
        "fetch_mode",
        "signals_saved",
        "holding_returns_saved",
        "failed_dates",
        "run_id",
    )
    if not records:
        return "No pipeline runs found."

    rows = [
        {
            **record,
            "run_id": _short(record.get("run_id")),
            "duration_seconds": _stringify(record.get("duration_seconds")),
            "failed_dates": ",".join(str(item) for item in record.get("failed_dates") or []),
        }
        for record in records
    ]
    widths = {
        column: max(len(column), *(len(_stringify(row.get(column))) for row in rows))
        for column in columns
    }
    header = " | ".join(column.ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)
    body = [
        " | ".join(_stringify(row.get(column)).ljust(widths[column]) for column in columns)
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _short(value: Any) -> str:
    text = _stringify(value)
    return text[:8] if text else ""


def _stringify(value: Any) -> str:
    return "" if value is None else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
