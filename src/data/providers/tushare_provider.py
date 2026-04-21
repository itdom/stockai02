"""Tushare provider adapter."""

from __future__ import annotations

from typing import Any

from common.config import get_env
from data.providers.base import MarketDataProvider


class TushareProvider(MarketDataProvider):
    source_name = "tushare"

    def __init__(self, token: str | None = None, *, client: Any | None = None) -> None:
        if client is not None:
            self.client = client
            return

        token_value = token or get_env("TUSHARE_TOKEN", required=True)
        try:
            import tushare as ts  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("tushare is required for TushareProvider") from exc

        self.client = ts.pro_api(token_value)

    def fetch_instruments(self) -> list[dict[str, Any]]:
        data = self.client.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,area,industry,list_date",
        )
        return _to_records(data)

    def fetch_daily_bars(
        self,
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        data = self.client.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
        return _to_records(data)

    def fetch_weekly_bars(
        self,
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        data = self.client.weekly(ts_code=symbol, start_date=start_date, end_date=end_date)
        return _to_records(data)


def _to_records(data: Any) -> list[dict[str, Any]]:
    if hasattr(data, "to_dict"):
        return data.to_dict("records")
    return list(data)
