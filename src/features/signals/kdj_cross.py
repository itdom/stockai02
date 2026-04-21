"""KDJ cross signal detection."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


SIGNAL_KDJ_GOLDEN_CROSS = "kdj_golden_cross"


def detect_kdj_golden_cross(
    kdj_rows: list[Mapping[str, Any]],
    *,
    created_at: str | None = None,
) -> list[dict[str, Any]]:
    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in kdj_rows:
        symbol = row.get("symbol")
        frequency = row.get("frequency")
        source = row.get("source")
        if not symbol or not frequency or not source:
            continue
        grouped[(str(symbol), str(frequency), str(source))].append(row)

    signals: list[dict[str, Any]] = []
    for (symbol, frequency, source), rows in sorted(grouped.items()):
        sorted_rows = sorted(rows, key=lambda item: str(item.get("trade_date")))
        previous: Mapping[str, Any] | None = None
        for row in sorted_rows:
            if previous is not None and _is_golden_cross(previous, row):
                signals.append(
                    {
                        "symbol": symbol,
                        "trade_date": row.get("trade_date"),
                        "frequency": frequency,
                        "signal_type": SIGNAL_KDJ_GOLDEN_CROSS,
                        "k": _decimal_or_none(row.get("k")),
                        "d": _decimal_or_none(row.get("d")),
                        "j": _decimal_or_none(row.get("j")),
                        "source": source,
                        "created_at": timestamp,
                    }
                )
            previous = row

    return signals


def _is_golden_cross(previous: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    prev_k = _decimal_or_none(previous.get("k"))
    prev_d = _decimal_or_none(previous.get("d"))
    curr_k = _decimal_or_none(current.get("k"))
    curr_d = _decimal_or_none(current.get("d"))
    if None in (prev_k, prev_d, curr_k, curr_d):
        return False
    return prev_k <= prev_d and curr_k > curr_d


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
