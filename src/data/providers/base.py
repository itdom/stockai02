"""Provider abstraction layer.

Providers fetch raw external data only. They must not write storage, calculate
features, or decide strategy signals.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


RawFrame = Any


class MarketDataProvider(ABC):
    source_name: str

    @abstractmethod
    def fetch_instruments(self) -> RawFrame:
        raise NotImplementedError

    @abstractmethod
    def fetch_daily_bars(
        self,
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> RawFrame:
        raise NotImplementedError

    @abstractmethod
    def fetch_weekly_bars(
        self,
        symbol: str | None,
        start_date: str,
        end_date: str,
    ) -> RawFrame:
        raise NotImplementedError


class SocialDataProvider(ABC):
    source_name: str

    @abstractmethod
    def fetch_posts(
        self,
        query: str,
        start_time: str,
        end_time: str,
        *,
        query_type: str = "Latest",
        cursor: str | None = None,
        limit: int | None = None,
        sleep: float = 0,
    ) -> RawFrame:
        raise NotImplementedError
