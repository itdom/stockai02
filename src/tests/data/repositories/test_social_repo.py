from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from data.repositories.social_repo import SocialRepository


def test_save_posts_aligns_fields_and_upserts() -> None:
    writer = InMemoryRecordWriter()
    repo = SocialRepository(writer)

    saved = repo.save_posts(
        [
            {
                "post_id": "tweet-1",
                "source": "x",
                "text": "old",
                "extra": "ignored",
            },
            {
                "post_id": "tweet-1",
                "source": "x",
                "text": "new",
            },
        ]
    )

    assert saved == 2
    records = repo.load_posts()
    assert len(records) == 1
    assert records[0]["text"] == "new"
    assert "extra" not in records[0]
    assert set(records[0]) == set(repo.post_table.fields)


def test_load_posts_filters_query_and_time_window() -> None:
    writer = InMemoryRecordWriter()
    repo = SocialRepository(writer)
    repo.save_posts(
        [
            {
                "post_id": "tweet-1",
                "source": "x",
                "created_at": "2026-04-20T00:00:00+00:00",
                "query": "AI3",
            },
            {
                "post_id": "tweet-2",
                "source": "x",
                "created_at": "2026-04-21T00:00:00+00:00",
                "query": "AI3",
            },
            {
                "post_id": "tweet-3",
                "source": "x",
                "created_at": "2026-04-20T00:00:00+00:00",
                "query": "other",
            },
        ]
    )

    records = repo.load_posts(
        start_time="2026-04-20T00:00:00+00:00",
        end_time="2026-04-21T00:00:00+00:00",
        query="AI3",
    )

    assert [row["post_id"] for row in records] == ["tweet-1"]
