"""Date and time utilities used by ingestion and feature tasks."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
YYYYMMDD = "%Y%m%d"


def parse_yyyymmdd(value: str | int) -> date:
    return datetime.strptime(str(value), YYYYMMDD).date()


def format_yyyymmdd(value: date | datetime) -> str:
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime(YYYYMMDD)


def normalize_trade_date(value: str | int | date | datetime) -> str:
    if isinstance(value, (date, datetime)):
        return format_yyyymmdd(value)
    return format_yyyymmdd(parse_yyyymmdd(value))


def week_monday(value: str | int | date | datetime) -> str:
    day = value.date() if isinstance(value, datetime) else value
    if not isinstance(day, date):
        day = parse_yyyymmdd(day)
    monday = day - timedelta(days=day.weekday())
    return format_yyyymmdd(monday)


def to_unix_timestamp(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=SHANGHAI_TZ)
    return int(value.timestamp())


def from_unix_timestamp(value: int, tz: timezone | ZoneInfo = SHANGHAI_TZ) -> datetime:
    return datetime.fromtimestamp(value, tz=tz)


def trading_day_range(start_date: str | int, end_date: str | int) -> list[str]:
    """Return weekdays in YYYYMMDD form.

    This is a lightweight fallback. A real A-share trading calendar service
    will replace it when `src/data/services/trading_calendar.py` is built.
    """

    start = parse_yyyymmdd(start_date)
    end = parse_yyyymmdd(end_date)
    if start > end:
        return []

    days: list[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(format_yyyymmdd(current))
        current += timedelta(days=1)
    return days


def day_start(value: str | int | date, tz: timezone | ZoneInfo = SHANGHAI_TZ) -> datetime:
    day = value if isinstance(value, date) else parse_yyyymmdd(value)
    return datetime.combine(day, time.min, tzinfo=tz)
