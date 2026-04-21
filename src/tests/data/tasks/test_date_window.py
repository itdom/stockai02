from __future__ import annotations

from datetime import date

import pytest

from data.tasks.date_window import resolve_date_window


def test_resolve_range_requires_start_and_end_dates() -> None:
    window = resolve_date_window(mode="range", start_date="20260101", end_date="20260131")

    assert window.start_date == "20260101"
    assert window.end_date == "20260131"


def test_resolve_date_uses_single_date() -> None:
    window = resolve_date_window(mode="date", date_value="20260102")

    assert window.start_date == "20260102"
    assert window.end_date == "20260102"


def test_resolve_increment_starts_after_max_trade_date() -> None:
    window = resolve_date_window(
        mode="increment",
        max_trade_date="20260102",
        end_date="20260131",
    )

    assert window.start_date == "20260103"
    assert window.end_date == "20260131"


def test_resolve_all_and_sample_have_defaults() -> None:
    all_window = resolve_date_window(mode="all", today=date(2026, 1, 31))
    sample_window = resolve_date_window(mode="sample", end_date="20260131")

    assert all_window.start_date == "19900101"
    assert all_window.end_date == "20260131"
    assert sample_window.start_date == "20260101"
    assert sample_window.end_date == "20260131"


def test_resolve_range_raises_for_missing_dates() -> None:
    with pytest.raises(ValueError, match="start_date is required"):
        resolve_date_window(mode="range", end_date="20260131")
