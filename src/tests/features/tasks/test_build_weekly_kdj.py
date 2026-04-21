from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from data.repositories.market_repo import MarketRepository
from features.repositories.kdj_repo import KdjFeatureRepository
from features.tasks.build_weekly_kdj import build_parser, build_repository, main, run


def test_run_build_weekly_kdj_reads_weekly_bars() -> None:
    writer = InMemoryRecordWriter()
    repo = MarketRepository(writer)
    kdj_repo = KdjFeatureRepository(writer)
    repo.save_weekly_bars(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "20260105",
                "frequency": "1w",
                "high": "10",
                "low": "0",
                "close": "5",
                "source": "csv",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "20260112",
                "frequency": "1w",
                "high": "10",
                "low": "0",
                "close": "10",
                "source": "csv",
            },
        ]
    )

    result = run(repo, kdj_repo, symbol="000001.SZ", start_date="20260101", end_date="20260131", n=2)

    assert result.weekly_count == 2
    assert result.feature_count == 2
    assert result.saved_count == 2
    assert result.features[0]["symbol"] == "000001.SZ"
    assert len(kdj_repo.load_features(symbol="000001.SZ")) == 2


def test_main_defaults_to_empty_dry_run_repository() -> None:
    assert main([]) == 0


def test_build_repository_defaults_to_dry_run_writer() -> None:
    args = build_parser().parse_args([])

    repo = build_repository(args)

    assert isinstance(repo.writer, InMemoryRecordWriter)
