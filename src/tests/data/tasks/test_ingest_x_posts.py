from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from data.repositories.social_repo import SocialRepository
from data.tasks.ingest_x_posts import build_parser, build_repository, run


class FakeSocialProvider:
    source_name = "x"

    def __init__(self) -> None:
        self.calls = []

    def fetch_posts(
        self,
        query,
        start_time,
        end_time,
        *,
        query_type="Latest",
        cursor=None,
        limit=None,
        sleep=0,
    ):
        self.calls.append((query, start_time, end_time, query_type, cursor, limit, sleep))
        return [
            {
                "id": "tweet-1",
                "text": "AI3",
                "createdAt": "2026-04-20T00:00:00Z",
                "likeCount": 1,
            }
        ]


def test_run_ingest_x_posts_normalizes_and_saves_raw_posts() -> None:
    writer = InMemoryRecordWriter()
    repo = SocialRepository(writer)
    provider = FakeSocialProvider()

    result = run(
        provider,
        repo,
        query="AI3",
        start_time="20260420",
        end_time="20260421",
        query_type="Latest",
        limit=10,
        sleep=0,
    )

    assert result.provider == "x"
    assert result.fetched_count == 1
    assert result.normalized_count == 1
    assert result.saved_count == 1
    assert provider.calls == [("AI3", "20260420", "20260421", "Latest", None, 10, 0)]
    assert repo.load_posts()[0]["query"] == "AI3"


def test_build_repository_defaults_to_dry_run_writer() -> None:
    args = build_parser().parse_args(
        [
            "--query",
            "AI3",
            "--start-time",
            "20260420",
            "--end-time",
            "20260421",
        ]
    )

    repo = build_repository(args)

    assert isinstance(repo.writer, InMemoryRecordWriter)
