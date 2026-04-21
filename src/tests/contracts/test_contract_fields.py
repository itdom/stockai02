from __future__ import annotations

from data.contracts.instrument import INSTRUMENT_FIELDS
from data.contracts.market import MARKET_BAR_FIELDS
from data.contracts.social import SOCIAL_POST_FIELDS
from data.contracts.feature import (
    HOLDING_RETURN_FIELDS,
    KDJ_CROSS_SIGNAL_FIELDS,
    KDJ_FEATURE_FIELDS,
)
from data.storage.table_registry import get_table_spec


def test_market_bar_fields_are_fixed() -> None:
    assert MARKET_BAR_FIELDS == (
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


def test_instrument_fields_are_fixed() -> None:
    assert INSTRUMENT_FIELDS == (
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


def test_social_post_fields_are_fixed() -> None:
    assert SOCIAL_POST_FIELDS == (
        "post_id",
        "author_id",
        "author_username",
        "created_at",
        "text",
        "lang",
        "like_count",
        "repost_count",
        "reply_count",
        "quote_count",
        "view_count",
        "query",
        "query_type",
        "source",
        "raw_json",
        "ingested_at",
    )


def test_table_registry_uses_contract_fields() -> None:
    assert get_table_spec("market_bar_daily").fields == MARKET_BAR_FIELDS
    assert get_table_spec("instrument").fields == INSTRUMENT_FIELDS
    assert get_table_spec("raw_social_post").fields == SOCIAL_POST_FIELDS
    assert get_table_spec("feature_kdj").fields == KDJ_FEATURE_FIELDS
    assert get_table_spec("signal_kdj_cross").fields == KDJ_CROSS_SIGNAL_FIELDS
    assert get_table_spec("backtest_holding_return").fields == HOLDING_RETURN_FIELDS
