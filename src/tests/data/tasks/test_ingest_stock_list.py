from __future__ import annotations

from pathlib import Path

from data.providers.csv_provider import CsvProvider
from data.repositories.base import InMemoryRecordWriter
from data.repositories.instrument_repo import InstrumentRepository
from data.tasks.ingest_stock_list import build_parser, build_repository, main, run


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def test_run_ingest_stock_list_with_csv_provider() -> None:
    writer = InMemoryRecordWriter()
    repo = InstrumentRepository(writer)
    provider = CsvProvider(instruments_path=FIXTURES / "instruments.csv")

    result = run(provider, repo)

    assert result.provider == "csv"
    assert result.fetched_count == 1
    assert result.normalized_count == 1
    assert result.saved_count == 1
    assert repo.load_all_instruments()[0]["symbol"] == "000001.SZ"


def test_main_supports_csv_provider() -> None:
    exit_code = main(
        [
            "--provider",
            "csv",
            "--csv-path",
            str(FIXTURES / "instruments.csv"),
            "--limit",
            "1",
        ]
    )

    assert exit_code == 0


def test_build_repository_defaults_to_dry_run_writer() -> None:
    args = build_parser().parse_args(["--provider", "csv", "--csv-path", "unused.csv"])

    repo = build_repository(args)

    assert isinstance(repo.writer, InMemoryRecordWriter)
