"""CSV provider for local tests and backfills."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from data.providers.base import MarketDataProvider


class CsvProvider(MarketDataProvider):
    source_name = "csv"

    def __init__(
        self,
        *,
        instruments_path: str | Path | None = None,
        daily_bars_path: str | Path | None = None,
        weekly_bars_path: str | Path | None = None,
    ) -> None:
        self.instruments_path = Path(instruments_path) if instruments_path else None
        self.daily_bars_path = Path(daily_bars_path) if daily_bars_path else None
        self.weekly_bars_path = Path(weekly_bars_path) if weekly_bars_path else None

    def fetch_instruments(self) -> list[dict[str, Any]]:
        return self._read_csv(self._require_path(self.instruments_path, "instruments_path"))

    def fetch_daily_bars(
        self,
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        rows = self._read_csv(self._require_path(self.daily_bars_path, "daily_bars_path"))
        return self._filter_market_rows(rows, symbol, start_date, end_date)

    def fetch_weekly_bars(
        self,
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        rows = self._read_csv(self._require_path(self.weekly_bars_path, "weekly_bars_path"))
        return self._filter_market_rows(rows, symbol, start_date, end_date)

    @staticmethod
    def _require_path(path: Path | None, name: str) -> Path:
        if path is None:
            raise ValueError(f"CsvProvider requires {name}")
        return path

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def _filter_market_rows(
        rows: list[dict[str, Any]],
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for row in rows:
            row_symbol = row.get("symbol") or row.get("ts_code") or row.get("code")
            row_date = row.get("trade_date")
            if symbol is not None and row_symbol != symbol:
                continue
            if row_date is not None and not (start_date <= row_date <= end_date):
                continue
            filtered.append(row)
        return filtered
