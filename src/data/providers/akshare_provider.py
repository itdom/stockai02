"""Akshare provider adapter."""

from __future__ import annotations

from typing import Any

from data.providers.base import MarketDataProvider


class AkshareProvider(MarketDataProvider):
    source_name = "akshare"

    def __init__(self, *, client: Any | None = None) -> None:
        if client is not None:
            self.client = client
            return

        try:
            import akshare as ak  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("akshare is required for AkshareProvider") from exc

        self.client = ak

    def fetch_instruments(self) -> list[dict[str, Any]]:
        data = self.client.stock_info_a_code_name()
        return _to_records(data)

    def fetch_daily_bars(
        self,
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        if symbol is None:
            raise ValueError("AkshareProvider.fetch_daily_bars requires a symbol")
        data = self.client.stock_zh_a_hist(
            symbol=symbol.split(".")[0],
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="",
        )
        return _to_records(data)

    def fetch_weekly_bars(
        self,
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        if symbol is None:
            raise ValueError("AkshareProvider.fetch_weekly_bars requires a symbol")
        data = self.client.stock_zh_a_hist(
            symbol=symbol.split(".")[0],
            period="weekly",
            start_date=start_date,
            end_date=end_date,
            adjust="",
        )
        return _to_records(data)


def _to_records(data: Any) -> list[dict[str, Any]]:
    if hasattr(data, "to_dict"):
        return data.to_dict("records")
    return list(data)
