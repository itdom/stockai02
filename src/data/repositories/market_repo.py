"""Repository for standardized market bars."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from data.repositories.base import RecordWriter
from data.storage.sinks import align_records
from data.storage.table_registry import get_table_spec


class MarketRepository:
    def __init__(self, writer: RecordWriter) -> None:
        self.writer = writer
        self.daily_table = get_table_spec("market_bar_daily")
        self.weekly_table = get_table_spec("market_bar_weekly")

    def save_daily_bars(self, records: list[Mapping[str, Any]]) -> int:
        aligned = align_records(records, self.daily_table)
        if not aligned:
            return 0
        return self.writer.upsert(self.daily_table, aligned)

    def save_weekly_bars(self, records: list[Mapping[str, Any]]) -> int:
        aligned = align_records(records, self.weekly_table)
        if not aligned:
            return 0
        return self.writer.upsert(self.weekly_table, aligned)

    def load_daily_bars(
        self,
        *,
        symbol: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        if not hasattr(self.writer, "all_records"):
            raise NotImplementedError("Current writer does not support reads")
        records = self.writer.all_records(self.daily_table.name)  # type: ignore[attr-defined]
        return _filter_market_records(records, symbol=symbol, start_date=start_date, end_date=end_date)

    def load_weekly_bars(
        self,
        *,
        symbol: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        if not hasattr(self.writer, "all_records"):
            raise NotImplementedError("Current writer does not support reads")
        records = self.writer.all_records(self.weekly_table.name)  # type: ignore[attr-defined]
        return _filter_market_records(records, symbol=symbol, start_date=start_date, end_date=end_date)

    def get_max_daily_trade_date(self, *, symbol: str | None = None) -> str | None:
        return _max_trade_date(self.load_daily_bars(symbol=symbol))

    def get_max_weekly_trade_date(self, *, symbol: str | None = None) -> str | None:
        return _max_trade_date(self.load_weekly_bars(symbol=symbol))


def _filter_market_records(
    records: list[dict[str, Any]],
    *,
    symbol: str | None,
    start_date: str | None,
    end_date: str | None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for record in records:
        if symbol is not None and record.get("symbol") != symbol:
            continue
        trade_date = record.get("trade_date")
        if start_date is not None and trade_date is not None and trade_date < start_date:
            continue
        if end_date is not None and trade_date is not None and trade_date > end_date:
            continue
        filtered.append(record)
    return filtered


def _max_trade_date(records: list[dict[str, Any]]) -> str | None:
    dates = [str(record.get("trade_date")) for record in records if record.get("trade_date")]
    return max(dates) if dates else None
