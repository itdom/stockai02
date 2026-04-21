"""Ingest raw X/Twitter posts into the standardized social repository."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Sequence

from common.logger import configure_logging, get_logger
from data.normalizers.social_normalizer import normalize_social_posts
from data.providers.base import SocialDataProvider
from data.providers.x_provider import XProvider
from data.repositories.base import InMemoryRecordWriter
from data.repositories.social_repo import SocialRepository
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class IngestXPostsResult:
    provider: str
    fetched_count: int
    normalized_count: int
    saved_count: int


def run(
    provider: SocialDataProvider,
    repository: SocialRepository,
    *,
    query: str,
    start_time: str,
    end_time: str,
    query_type: str = "Latest",
    cursor: str | None = None,
    limit: int | None = None,
    sleep: float = 0,
) -> IngestXPostsResult:
    LOGGER.info(
        "ingest_x_posts started provider=%s query=%s query_type=%s start_time=%s end_time=%s limit=%s",
        provider.source_name,
        query,
        query_type,
        start_time,
        end_time,
        limit,
    )
    raw_rows = provider.fetch_posts(
        query,
        start_time,
        end_time,
        query_type=query_type,
        cursor=cursor,
        limit=limit,
        sleep=sleep,
    )
    normalized = normalize_social_posts(
        raw_rows,
        source=provider.source_name,
        query=query,
        query_type=query_type,
    )
    saved_count = repository.save_posts(normalized)
    result = IngestXPostsResult(
        provider=provider.source_name,
        fetched_count=len(raw_rows),
        normalized_count=len(normalized),
        saved_count=saved_count,
    )
    LOGGER.info(
        "ingest_x_posts finished provider=%s fetched=%s normalized=%s saved=%s",
        result.provider,
        result.fetched_count,
        result.normalized_count,
        result.saved_count,
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest raw X/Twitter posts")
    parser.add_argument("--query", required=True)
    parser.add_argument("--start-time", required=True)
    parser.add_argument("--end-time", required=True)
    parser.add_argument("--query-type", choices=("Latest", "Top"), default="Latest")
    parser.add_argument("--cursor", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=5)
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Write to MySQL. By default the task runs in dry-run memory mode.",
    )
    return parser


def build_provider(_: argparse.Namespace) -> SocialDataProvider:
    return XProvider()


def build_repository(args: argparse.Namespace) -> SocialRepository:
    if not args.write_db:
        return SocialRepository(InMemoryRecordWriter())

    config = load_database_config()
    connection = connect_mysql(config)
    return SocialRepository(MySqlRecordWriter(connection))


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    provider = build_provider(args)
    repository = build_repository(args)
    result = run(
        provider,
        repository,
        query=args.query,
        start_time=args.start_time,
        end_time=args.end_time,
        query_type=args.query_type,
        cursor=args.cursor,
        limit=args.limit,
        sleep=args.sleep,
    )
    LOGGER.info("summary=%s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
