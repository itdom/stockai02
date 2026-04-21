"""Shared mode/date-window handling for ingestion tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from common.timeutils import format_yyyymmdd, parse_yyyymmdd


DEFAULT_ALL_START_DATE = "19900101"
SAMPLE_LOOKBACK_DAYS = 30


@dataclass(frozen=True)
class DateWindow:
    mode: str
    start_date: str
    end_date: str


def resolve_date_window(
    *,
    mode: str,
    start_date: str | None = None,
    end_date: str | None = None,
    date_value: str | None = None,
    max_trade_date: str | None = None,
    today: date | None = None,
) -> DateWindow:
    today_value = today or date.today()
    today_text = format_yyyymmdd(today_value)

    if mode == "range":
        return DateWindow(mode=mode, start_date=_require(start_date, "start_date"), end_date=_require(end_date, "end_date"))

    if mode == "date":
        value = _require(date_value or start_date, "date")
        return DateWindow(mode=mode, start_date=value, end_date=value)

    if mode == "increment":
        if max_trade_date:
            resolved_start = format_yyyymmdd(parse_yyyymmdd(max_trade_date) + timedelta(days=1))
        else:
            resolved_start = _require(start_date, "start_date")
        return DateWindow(mode=mode, start_date=resolved_start, end_date=end_date or today_text)

    if mode == "all":
        return DateWindow(
            mode=mode,
            start_date=start_date or DEFAULT_ALL_START_DATE,
            end_date=end_date or today_text,
        )

    if mode == "sample":
        resolved_end = end_date or today_text
        resolved_start = start_date or format_yyyymmdd(parse_yyyymmdd(resolved_end) - timedelta(days=SAMPLE_LOOKBACK_DAYS))
        return DateWindow(mode=mode, start_date=resolved_start, end_date=resolved_end)

    raise ValueError(f"Unsupported mode: {mode}")


def _require(value: str | None, name: str) -> str:
    if value is None or value == "":
        raise ValueError(f"{name} is required")
    return value
