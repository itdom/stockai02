"""Read service for standardized social data."""

from __future__ import annotations

from typing import Any

from data.repositories.social_repo import SocialRepository


class SocialDataService:
    def __init__(self, repository: SocialRepository) -> None:
        self.repository = repository

    def get_posts(
        self,
        *,
        start_time: str | None = None,
        end_time: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.repository.load_posts(start_time=start_time, end_time=end_time, query=query)
