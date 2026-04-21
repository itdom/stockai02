"""Normalize instrument rows into the internal instrument contract."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from data.contracts.enums import AssetType, DataSource, Market
from data.contracts.instrument import INSTRUMENT_FIELDS


SYMBOL_PATTERN = re.compile(r"^(?P<code>\d{6})(?:[.](?P<market>SZ|SH|BJ))?$", re.IGNORECASE)


def normalize_instruments(
    rows: list[Mapping[str, Any]],
    *,
    source: str | DataSource,
    ingested_at: str | None = None,
) -> list[dict[str, Any]]:
    timestamp = ingested_at or datetime.now(timezone.utc).isoformat()
    source_value = str(source)
    normalized: dict[str, dict[str, Any]] = {}

    for row in rows:
        symbol = normalize_symbol(_first_value(row, "symbol", "ts_code", "code"))
        if symbol is None:
            continue

        record = {
            "symbol": symbol,
            "name": _first_value(row, "name", "stock_name", "fullname"),
            "market": _first_value(row, "market", "exchange") or symbol.split(".")[1],
            "exchange": _first_value(row, "exchange") or symbol.split(".")[1],
            "asset_type": _first_value(row, "asset_type") or AssetType.STOCK.value,
            "list_status": _first_value(row, "list_status", "status"),
            "list_date": normalize_date(_first_value(row, "list_date")),
            "delist_date": normalize_date(_first_value(row, "delist_date")),
            "industry": _first_value(row, "industry"),
            "source": source_value,
            "ingested_at": timestamp,
        }
        normalized[symbol] = {field: record.get(field) for field in INSTRUMENT_FIELDS}

    return [normalized[symbol] for symbol in sorted(normalized)]


def normalize_symbol(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip().upper()
    if not text:
        return None

    text = text.replace("_", ".")
    match = SYMBOL_PATTERN.match(text)
    if not match:
        return None

    code = match.group("code")
    market = match.group("market")
    if market is None:
        market = infer_market(code)
    return f"{code}.{market}"


def infer_market(code: str) -> str:
    if code.startswith(("60", "68", "90")):
        return Market.SH.value
    if code.startswith(("00", "30", "20")):
        return Market.SZ.value
    if code.startswith(("43", "83", "87", "88", "92")):
        return Market.BJ.value
    raise ValueError(f"Cannot infer market for symbol code: {code}")


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if re.fullmatch(r"\d{8}", text):
        return text
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return datetime.strptime(text, "%Y-%m-%d").strftime("%Y%m%d")
    raise ValueError(f"Invalid date format: {text}")


def _first_value(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return None
