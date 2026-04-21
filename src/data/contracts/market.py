"""Market data contract definitions."""

from __future__ import annotations

MARKET_BAR_FIELDS: tuple[str, ...] = (
    "symbol",
    "trade_date",
    "frequency",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "volume",
    "amount",
    "source",
    "ingested_at",
)

MARKET_BAR_PRIMARY_KEY: tuple[str, ...] = (
    "symbol",
    "trade_date",
    "frequency",
    "source",
)
