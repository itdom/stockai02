"""KDJ indicator calculation for standardized market bars."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


KDJ_FIELDS: tuple[str, ...] = (
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


def calculate_kdj(
    bars: Any,
    *,
    n: int = 9,
    k_period: int = 3,
    d_period: int = 3,
    initial_k: Decimal | int | str = Decimal("50"),
    initial_d: Decimal | int | str = Decimal("50"),
    ingested_at: str | None = None,
) -> list[dict[str, Any]]:
    if n <= 0:
        raise ValueError("n must be greater than 0")
    if k_period <= 0 or d_period <= 0:
        raise ValueError("k_period and d_period must be greater than 0")

    records = _to_records(bars)
    timestamp = ingested_at or datetime.now(timezone.utc).isoformat()
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        symbol = row.get("symbol")
        frequency = row.get("frequency")
        source = row.get("source")
        if not symbol or not frequency or not source:
            continue
        grouped[(str(symbol), str(frequency), str(source))].append(row)

    output: list[dict[str, Any]] = []
    for (symbol, frequency, source), rows in sorted(grouped.items()):
        sorted_rows = sorted(rows, key=lambda item: str(item.get("trade_date")))
        previous_k = _decimal(initial_k)
        previous_d = _decimal(initial_d)
        for index, row in enumerate(sorted_rows):
            window = sorted_rows[max(0, index - n + 1) : index + 1]
            rsv = _calculate_rsv(window, row)
            if rsv is None:
                k_value = None
                d_value = None
                j_value = None
            else:
                k_value = _smooth(rsv, previous_k, k_period)
                d_value = _smooth(k_value, previous_d, d_period)
                j_value = (Decimal("3") * k_value) - (Decimal("2") * d_value)
                previous_k = k_value
                previous_d = d_value

            output.append(
                {
                    "symbol": symbol,
                    "trade_date": row.get("trade_date"),
                    "frequency": frequency,
                    "rsv": rsv,
                    "k": k_value,
                    "d": d_value,
                    "j": j_value,
                    "source": source,
                    "ingested_at": timestamp,
                }
            )

    return [{field: row.get(field) for field in KDJ_FIELDS} for row in output]


def _calculate_rsv(window: list[Mapping[str, Any]], current: Mapping[str, Any]) -> Decimal | None:
    close = _decimal_or_none(current.get("close"))
    lows = [_decimal_or_none(row.get("low")) for row in window]
    highs = [_decimal_or_none(row.get("high")) for row in window]
    lows = [value for value in lows if value is not None]
    highs = [value for value in highs if value is not None]
    if close is None or not lows or not highs:
        return None

    lowest_low = min(lows)
    highest_high = max(highs)
    if highest_high == lowest_low:
        return Decimal("50")
    return ((close - lowest_low) / (highest_high - lowest_low)) * Decimal("100")


def _smooth(current: Decimal, previous: Decimal, period: int) -> Decimal:
    period_value = Decimal(period)
    return ((period_value - Decimal("1")) * previous + current) / period_value


def _to_records(data: Any) -> list[Mapping[str, Any]]:
    if hasattr(data, "to_dict"):
        return data.to_dict("records")
    return list(data)


def _decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value: {text}") from exc
