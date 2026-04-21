"""Holding-period return calculation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


DEFAULT_HORIZONS: tuple[int, ...] = (5, 10, 20, 60)


def calculate_holding_returns(
    signals: list[Mapping[str, Any]],
    daily_bars: list[Mapping[str, Any]],
    *,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    created_at: str | None = None,
) -> list[dict[str, Any]]:
    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    bars_by_key: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for bar in daily_bars:
        symbol = bar.get("symbol")
        source = bar.get("source")
        trade_date = bar.get("trade_date")
        if not symbol or not source or not trade_date:
            continue
        bars_by_key[(str(symbol), str(source))].append(bar)

    for key in bars_by_key:
        bars_by_key[key] = sorted(bars_by_key[key], key=lambda row: str(row.get("trade_date")))

    results: list[dict[str, Any]] = []
    for signal in sorted(signals, key=lambda row: (str(row.get("symbol")), str(row.get("trade_date")))):
        symbol = signal.get("symbol")
        source = signal.get("source")
        signal_date = signal.get("trade_date")
        signal_type = signal.get("signal_type")
        if not symbol or not source or not signal_date or not signal_type:
            continue

        bars = bars_by_key.get((str(symbol), str(source)), [])
        entry_index = _find_first_bar_index_on_or_after(bars, str(signal_date))
        if entry_index is None:
            continue

        entry_bar = bars[entry_index]
        entry_close = _decimal_or_none(entry_bar.get("close"))
        if entry_close is None:
            continue

        for horizon in horizons:
            exit_index = entry_index + horizon
            exit_bar = bars[exit_index] if exit_index < len(bars) else None
            exit_close = _decimal_or_none(exit_bar.get("close")) if exit_bar is not None else None
            return_pct = None
            if exit_close is not None and entry_close != Decimal("0"):
                return_pct = ((exit_close - entry_close) / entry_close) * Decimal("100")

            results.append(
                {
                    "symbol": str(symbol),
                    "signal_date": str(signal_date),
                    "signal_type": str(signal_type),
                    "source": str(source),
                    "entry_date": entry_bar.get("trade_date"),
                    "entry_close": entry_close,
                    "horizon": horizon,
                    "exit_date": exit_bar.get("trade_date") if exit_bar is not None else None,
                    "exit_close": exit_close,
                    "return_pct": return_pct,
                    "created_at": timestamp,
                }
            )

    return results


def _find_first_bar_index_on_or_after(
    bars: list[Mapping[str, Any]],
    signal_date: str,
) -> int | None:
    for index, bar in enumerate(bars):
        trade_date = bar.get("trade_date")
        if trade_date is not None and str(trade_date) >= signal_date:
            return index
    return None


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
