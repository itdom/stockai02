"""Instrument contract definitions."""

from __future__ import annotations

INSTRUMENT_FIELDS: tuple[str, ...] = (
    "symbol",
    "name",
    "market",
    "exchange",
    "asset_type",
    "list_status",
    "list_date",
    "delist_date",
    "industry",
    "source",
    "ingested_at",
)

INSTRUMENT_PRIMARY_KEY: tuple[str, ...] = ("symbol",)
