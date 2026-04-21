"""Feature, signal, and backtest result contract definitions."""

from __future__ import annotations

KDJ_FEATURE_FIELDS: tuple[str, ...] = (
    "symbol",
    "trade_date",
    "frequency",
    "rsv",
    "k",
    "d",
    "j",
    "source",
    "ingested_at",
)

KDJ_FEATURE_PRIMARY_KEY: tuple[str, ...] = (
    "symbol",
    "trade_date",
    "frequency",
    "source",
)

KDJ_CROSS_SIGNAL_FIELDS: tuple[str, ...] = (
    "symbol",
    "trade_date",
    "frequency",
    "signal_type",
    "k",
    "d",
    "j",
    "source",
    "created_at",
)

KDJ_CROSS_SIGNAL_PRIMARY_KEY: tuple[str, ...] = (
    "symbol",
    "trade_date",
    "frequency",
    "signal_type",
    "source",
)

HOLDING_RETURN_FIELDS: tuple[str, ...] = (
    "symbol",
    "signal_date",
    "signal_type",
    "source",
    "entry_date",
    "entry_close",
    "horizon",
    "exit_date",
    "exit_close",
    "return_pct",
    "created_at",
)

HOLDING_RETURN_PRIMARY_KEY: tuple[str, ...] = (
    "symbol",
    "signal_date",
    "signal_type",
    "source",
    "horizon",
)
