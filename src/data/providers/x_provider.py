"""X/Twitter provider backed by TwitterAPI.io advanced search."""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from common.config import get_env
from common.timeutils import day_start, to_unix_timestamp
from data.providers.base import SocialDataProvider


class XProvider(SocialDataProvider):
    """Fetch raw public posts only; no entity linking or signal logic lives here."""

    source_name = "x"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: Any | None = None,
        base_url: str = "https://api.twitterapi.io",
    ) -> None:
        self.api_key = api_key or get_env("X_API_KEY", required=client is None)
        self.client = client
        self.base_url = base_url.rstrip("/")

    def fetch_posts(
        self,
        query: str,
        start_time: str,
        end_time: str,
        *,
        query_type: str = "Latest",
        cursor: str | None = None,
        limit: int | None = None,
        sleep: float = 0,
    ) -> list[dict[str, Any]]:
        search_query = build_time_bounded_query(query, start_time, end_time)
        rows: list[dict[str, Any]] = []
        next_cursor = cursor or ""

        while True:
            payload = self._get_json(
                "/twitter/tweet/advanced_search",
                {
                    "query": search_query,
                    "queryType": query_type,
                    "cursor": next_cursor,
                },
            )
            tweets = _extract_tweets(payload)
            for tweet in tweets:
                record = dict(tweet)
                record["_ai3_query"] = query
                record["_ai3_query_type"] = query_type
                rows.append(record)
                if limit is not None and len(rows) >= limit:
                    return rows

            next_cursor = _extract_next_cursor(payload)
            if not next_cursor or not tweets:
                return rows
            if sleep > 0:
                time.sleep(sleep)

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.client is not None:
            response = self.client.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"x-api-key": self.api_key},
            )
            if isinstance(response, dict):
                return response
            if hasattr(response, "json"):
                return response.json()
            return dict(response)

        if not self.api_key:
            raise RuntimeError("X_API_KEY is required for XProvider")

        url = f"{self.base_url}{path}?{urlencode(params)}"
        request = Request(url, headers={"x-api-key": self.api_key})
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - explicit provider URL.
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"TwitterAPI.io request failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("TwitterAPI.io request failed") from exc


def build_time_bounded_query(query: str, start_time: str, end_time: str) -> str:
    start_ts = _to_unix_seconds(start_time)
    end_ts = _to_unix_seconds(end_time)
    return f"{query} since_time:{start_ts} until_time:{end_ts}"


def _to_unix_seconds(value: str) -> int:
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return to_unix_timestamp(day_start(text))
    if text.isdigit():
        return int(text)
    normalized = text.replace("Z", "+00:00")
    return to_unix_timestamp(datetime.fromisoformat(normalized))


def _extract_tweets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("tweets", "data", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]
    return []


def _extract_next_cursor(payload: dict[str, Any]) -> str | None:
    for key in ("next_cursor", "nextCursor", "cursor", "next"):
        value = payload.get(key)
        if value:
            return str(value)
    return None
