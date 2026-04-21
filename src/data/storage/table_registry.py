"""Physical table registry for standardized data."""

from __future__ import annotations

from dataclasses import dataclass

from data.contracts.feature import (
    HOLDING_RETURN_FIELDS,
    HOLDING_RETURN_PRIMARY_KEY,
    KDJ_CROSS_SIGNAL_FIELDS,
    KDJ_CROSS_SIGNAL_PRIMARY_KEY,
    KDJ_FEATURE_FIELDS,
    KDJ_FEATURE_PRIMARY_KEY,
)
from data.contracts.instrument import INSTRUMENT_FIELDS, INSTRUMENT_PRIMARY_KEY
from data.contracts.market import MARKET_BAR_FIELDS, MARKET_BAR_PRIMARY_KEY
from data.contracts.social import SOCIAL_POST_FIELDS, SOCIAL_POST_PRIMARY_KEY


@dataclass(frozen=True)
class TableSpec:
    name: str
    fields: tuple[str, ...]
    primary_key: tuple[str, ...]
    unique_key: tuple[str, ...] = ()
    partition_key: str | None = None


TABLES: dict[str, TableSpec] = {
    "instrument": TableSpec(
        name="instrument",
        fields=INSTRUMENT_FIELDS,
        primary_key=INSTRUMENT_PRIMARY_KEY,
    ),
    "market_bar_daily": TableSpec(
        name="market_bar_daily",
        fields=MARKET_BAR_FIELDS,
        primary_key=MARKET_BAR_PRIMARY_KEY,
        partition_key="trade_date",
    ),
    "market_bar_weekly": TableSpec(
        name="market_bar_weekly",
        fields=MARKET_BAR_FIELDS,
        primary_key=MARKET_BAR_PRIMARY_KEY,
        partition_key="trade_date",
    ),
    "raw_social_post": TableSpec(
        name="raw_social_post",
        fields=SOCIAL_POST_FIELDS,
        primary_key=SOCIAL_POST_PRIMARY_KEY,
        partition_key="created_at",
    ),
    "feature_kdj": TableSpec(
        name="feature_kdj",
        fields=KDJ_FEATURE_FIELDS,
        primary_key=KDJ_FEATURE_PRIMARY_KEY,
        partition_key="trade_date",
    ),
    "signal_kdj_cross": TableSpec(
        name="signal_kdj_cross",
        fields=KDJ_CROSS_SIGNAL_FIELDS,
        primary_key=KDJ_CROSS_SIGNAL_PRIMARY_KEY,
        partition_key="trade_date",
    ),
    "backtest_holding_return": TableSpec(
        name="backtest_holding_return",
        fields=HOLDING_RETURN_FIELDS,
        primary_key=HOLDING_RETURN_PRIMARY_KEY,
        partition_key="signal_date",
    ),
}


def get_table_spec(name: str) -> TableSpec:
    try:
        return TABLES[name]
    except KeyError as exc:
        raise KeyError(f"Unknown table spec: {name}") from exc
