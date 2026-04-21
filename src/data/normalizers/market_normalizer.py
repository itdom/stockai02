"""Normalize market bar rows into the internal market contract."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from common.timeutils import normalize_trade_date, week_monday
from data.contracts.enums import DataSource, Frequency
from data.contracts.market import MARKET_BAR_FIELDS
from data.normalizers.instrument_normalizer import normalize_symbol


def normalize_market_bars(
    rows: list[Mapping[str, Any]],
    *,
    source: str | DataSource,
    frequency: str | Frequency,
    ingested_at: str | None = None,
) -> list[dict[str, Any]]:
    timestamp = ingested_at or datetime.now(timezone.utc).isoformat()
    frequency_value = str(frequency)
    source_value = str(source)
    normalized: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    for row in rows:
        symbol = normalize_symbol(_first_value(row, "symbol", "ts_code", "code", "股票代码"))
        if symbol is None:
            continue

        trade_date_value = _first_value(row, "trade_date", "date", "日期")
        if trade_date_value is None:
            continue
        trade_date = _normalize_market_trade_date(trade_date_value)
        if frequency_value == Frequency.WEEKLY.value:
            trade_date = week_monday(trade_date)

        record = {
            "symbol": symbol,
            "trade_date": trade_date,
            "frequency": frequency_value,
            "open": _decimal(_first_value(row, "open", "开盘")),
            "high": _decimal(_first_value(row, "high", "最高")),
            "low": _decimal(_first_value(row, "low", "最低")),
            "close": _decimal(_first_value(row, "close", "收盘")),
            "pre_close": _decimal(_first_value(row, "pre_close", "preclose")),
            "change": _decimal(_first_value(row, "change", "涨跌额")),
            "pct_chg": _decimal(_first_value(row, "pct_chg", "pct_change", "涨跌幅")),
            "volume": _decimal(_first_value(row, "volume", "vol", "成交量")),
            "amount": _decimal(_first_value(row, "amount", "成交额")),
            "source": source_value,
            "ingested_at": timestamp,
        }
        key = (symbol, trade_date, frequency_value, source_value)
        normalized[key] = {field: record.get(field) for field in MARKET_BAR_FIELDS}

    return [normalized[key] for key in sorted(normalized)]


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value: {text}") from exc


def _normalize_market_trade_date(value: Any) -> str:
    text = str(value).strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return datetime.strptime(text, "%Y-%m-%d").strftime("%Y%m%d")
    return normalize_trade_date(value)


def _first_value(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return None
