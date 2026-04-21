from __future__ import annotations

import pytest

from data.repositories.base import InMemoryRecordWriter
from features.repositories.kdj_repo import KdjFeatureRepository
from features.repositories.signal_repo import KdjCrossSignalRepository
from features.tasks.build_weekly_kdj_cross import build_repositories, main, run, build_parser


def test_run_build_weekly_kdj_cross_saves_signals() -> None:
    writer = InMemoryRecordWriter()
    kdj_repo = KdjFeatureRepository(writer)
    signal_repo = KdjCrossSignalRepository(writer)
    kdj_repo.save_features(
        [
            {"symbol": "000001.SZ", "trade_date": "20260105", "frequency": "1w", "k": "40", "d": "50", "source": "csv"},
            {"symbol": "000001.SZ", "trade_date": "20260112", "frequency": "1w", "k": "55", "d": "50", "source": "csv"},
        ]
    )

    result = run(kdj_repo, signal_repo, symbol="000001.SZ")

    assert result.feature_count == 2
    assert result.signal_count == 1
    assert result.saved_count == 1
    assert signal_repo.load_signals()[0]["trade_date"] == "20260112"


def test_main_defaults_to_empty_dry_run_repository() -> None:
    assert main([]) == 0


def test_build_repositories_defaults_to_dry_run_writer() -> None:
    args = build_parser().parse_args([])
    kdj_repo, signal_repo = build_repositories(args)

    assert isinstance(kdj_repo.writer, InMemoryRecordWriter)
    assert signal_repo.writer is kdj_repo.writer


def test_run_build_weekly_kdj_cross_overwrite_deletes_window_before_save() -> None:
    writer = InMemoryRecordWriter()
    kdj_repo = KdjFeatureRepository(writer)
    signal_repo = KdjCrossSignalRepository(writer)
    signal_repo.save_signals(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260112",
                "frequency": "1w",
                "signal_type": "kdj_golden_cross",
                "source": "csv",
            }
        ]
    )
    kdj_repo.save_features(
        [
            {"symbol": "000001.SZ", "trade_date": "20260105", "frequency": "1w", "k": "60", "d": "50", "source": "csv"},
            {"symbol": "000001.SZ", "trade_date": "20260112", "frequency": "1w", "k": "55", "d": "50", "source": "csv"},
        ]
    )

    result = run(
        kdj_repo,
        signal_repo,
        start_date="20260105",
        end_date="20260112",
        overwrite=True,
    )

    assert result.deleted_count == 1
    assert result.signal_count == 0
    assert signal_repo.load_signals() == []


def test_run_build_weekly_kdj_cross_overwrite_requires_window() -> None:
    writer = InMemoryRecordWriter()

    with pytest.raises(ValueError, match="--overwrite requires"):
        run(
            KdjFeatureRepository(writer),
            KdjCrossSignalRepository(writer),
            overwrite=True,
        )
