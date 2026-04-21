"""Summarize holding-return backtest results into a compact report."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from backtest.repositories.holding_return_repo import HoldingReturnRepository
from common.logger import configure_logging, get_logger
from data.repositories.base import InMemoryRecordWriter
from data.repositories.instrument_repo import InstrumentRepository
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class ReturnStats:
    group: str
    total_count: int
    completed_count: int
    win_count: int
    win_rate_pct: Decimal | None
    avg_return_pct: Decimal | None
    median_return_pct: Decimal | None
    p10_return_pct: Decimal | None
    p25_return_pct: Decimal | None
    p75_return_pct: Decimal | None
    p90_return_pct: Decimal | None
    min_return_pct: Decimal | None
    max_return_pct: Decimal | None


@dataclass(frozen=True)
class HoldingReturnSummary:
    start_date: str | None
    end_date: str | None
    source: str | None
    total_count: int
    completed_count: int
    by_horizon: list[ReturnStats]
    by_signal_date: list[ReturnStats]
    by_industry: list[ReturnStats]

    def to_dict(self) -> dict[str, Any]:
        return _json_ready(asdict(self))


def run(
    result_repository: HoldingReturnRepository,
    instrument_repository: InstrumentRepository | None = None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    source: str | None = None,
    output_path: str | None = None,
    output_format: str = "markdown",
) -> HoldingReturnSummary:
    LOGGER.info(
        "summarize_holding_return started start_date=%s end_date=%s source=%s",
        start_date,
        end_date,
        source,
    )
    records = _filter_results(
        result_repository.load_results(),
        start_date=start_date,
        end_date=end_date,
        source=source,
    )
    industry_by_symbol = _industry_by_symbol(instrument_repository)
    summary = HoldingReturnSummary(
        start_date=start_date,
        end_date=end_date,
        source=source,
        total_count=len(records),
        completed_count=sum(1 for row in records if _decimal_or_none(row.get("return_pct")) is not None),
        by_horizon=_group_stats(records, key="horizon"),
        by_signal_date=_group_stats(records, key="signal_date"),
        by_industry=_group_stats(
            records,
            labeler=lambda row: industry_by_symbol.get(str(row.get("symbol")), "unknown"),
        ),
    )
    if output_path:
        _write_report(Path(output_path), summary, output_format=output_format)
    LOGGER.info(
        "summarize_holding_return finished total=%s completed=%s horizons=%s",
        summary.total_count,
        summary.completed_count,
        len(summary.by_horizon),
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize holding-return backtest results")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--output-path", default=None)
    parser.add_argument("--output-format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Read MySQL. By default the task uses an empty dry-run memory repository.",
    )
    return parser


def build_repositories(args: argparse.Namespace) -> tuple[HoldingReturnRepository, InstrumentRepository]:
    if not args.write_db:
        writer = InMemoryRecordWriter()
        return HoldingReturnRepository(writer), InstrumentRepository(writer)

    config = load_database_config()
    writer = MySqlRecordWriter(connect_mysql(config))
    return HoldingReturnRepository(writer), InstrumentRepository(writer)


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    result_repository, instrument_repository = build_repositories(args)
    summary = run(
        result_repository,
        instrument_repository,
        start_date=args.start_date,
        end_date=args.end_date,
        source=args.source,
        output_path=args.output_path,
        output_format=args.output_format,
    )
    LOGGER.info("summary=%s", summary.to_dict())
    return 0


def render_markdown(summary: HoldingReturnSummary) -> str:
    lines = [
        "# Holding Return Summary",
        "",
        f"- start_date: {summary.start_date or 'all'}",
        f"- end_date: {summary.end_date or 'all'}",
        f"- source: {summary.source or 'all'}",
        f"- total_count: {summary.total_count}",
        f"- completed_count: {summary.completed_count}",
        "",
        "## By Horizon",
        _render_table(summary.by_horizon),
        "",
        "## By Signal Date",
        _render_table(summary.by_signal_date),
        "",
        "## By Industry",
        _render_table(summary.by_industry),
        "",
    ]
    return "\n".join(lines)


def _filter_results(
    records: list[Mapping[str, Any]],
    *,
    start_date: str | None,
    end_date: str | None,
    source: str | None,
) -> list[Mapping[str, Any]]:
    filtered: list[Mapping[str, Any]] = []
    for row in records:
        signal_date = row.get("signal_date")
        if source is not None and row.get("source") != source:
            continue
        if start_date is not None and signal_date is not None and signal_date < start_date:
            continue
        if end_date is not None and signal_date is not None and signal_date > end_date:
            continue
        filtered.append(row)
    return filtered


def _industry_by_symbol(repository: InstrumentRepository | None) -> dict[str, str]:
    if repository is None:
        return {}
    return {
        str(row.get("symbol")): str(row.get("industry") or "unknown")
        for row in repository.load_all_instruments()
        if row.get("symbol")
    }


def _group_stats(
    records: list[Mapping[str, Any]],
    *,
    key: str | None = None,
    labeler: Any | None = None,
) -> list[ReturnStats]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        group = str(labeler(row) if labeler is not None else row.get(key or "") or "unknown")
        groups[group].append(row)
    return [_stats(group, rows) for group, rows in sorted(groups.items(), key=lambda item: item[0])]


def _stats(group: str, records: list[Mapping[str, Any]]) -> ReturnStats:
    returns = sorted(
        value
        for value in (_decimal_or_none(row.get("return_pct")) for row in records)
        if value is not None
    )
    completed_count = len(returns)
    win_count = sum(1 for value in returns if value > 0)
    return ReturnStats(
        group=group,
        total_count=len(records),
        completed_count=completed_count,
        win_count=win_count,
        win_rate_pct=_pct(Decimal(win_count), Decimal(completed_count)) if completed_count else None,
        avg_return_pct=(sum(returns) / Decimal(completed_count)) if completed_count else None,
        median_return_pct=_percentile(returns, Decimal("0.5")),
        p10_return_pct=_percentile(returns, Decimal("0.1")),
        p25_return_pct=_percentile(returns, Decimal("0.25")),
        p75_return_pct=_percentile(returns, Decimal("0.75")),
        p90_return_pct=_percentile(returns, Decimal("0.9")),
        min_return_pct=returns[0] if returns else None,
        max_return_pct=returns[-1] if returns else None,
    )


def _percentile(values: list[Decimal], percentile: Decimal) -> Decimal | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    position = percentile * Decimal(len(values) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(values) - 1)
    weight = position - Decimal(lower_index)
    return values[lower_index] + ((values[upper_index] - values[lower_index]) * weight)


def _pct(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return (numerator / denominator) * Decimal("100")


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return Decimal(text)


def _write_report(path: Path, summary: HoldingReturnSummary, *, output_format: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "json":
        path.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return
    path.write_text(render_markdown(summary), encoding="utf-8")


def _render_table(rows: list[ReturnStats]) -> str:
    headers = (
        "group",
        "total",
        "completed",
        "wins",
        "win_rate_pct",
        "avg",
        "median",
        "p10",
        "p25",
        "p75",
        "p90",
        "min",
        "max",
    )
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        output.append(
            "| "
            + " | ".join(
                [
                    row.group,
                    str(row.total_count),
                    str(row.completed_count),
                    str(row.win_count),
                    _format_decimal(row.win_rate_pct),
                    _format_decimal(row.avg_return_pct),
                    _format_decimal(row.median_return_pct),
                    _format_decimal(row.p10_return_pct),
                    _format_decimal(row.p25_return_pct),
                    _format_decimal(row.p75_return_pct),
                    _format_decimal(row.p90_return_pct),
                    _format_decimal(row.min_return_pct),
                    _format_decimal(row.max_return_pct),
                ]
            )
            + " |"
        )
    return "\n".join(output)


def _format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    return str(value.quantize(Decimal("0.000001")))


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    raise SystemExit(main())
