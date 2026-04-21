from __future__ import annotations

from data.repositories.base import InMemoryRecordWriter
from data.repositories.social_repo import SocialRepository
from data.services.social_data_service import SocialDataService


def test_social_data_service_reads_standardized_posts() -> None:
    writer = InMemoryRecordWriter()
    repo = SocialRepository(writer)
    repo.save_posts(
        [
            {
                "post_id": "tweet-1",
                "source": "x",
                "query": "AI3",
                "created_at": "2026-04-20T00:00:00+00:00",
            }
        ]
    )
    service = SocialDataService(repo)

    rows = service.get_posts(query="AI3")

    assert [row["post_id"] for row in rows] == ["tweet-1"]
