"""Normalize raw social post rows into the internal social contract."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from typing import Any

from data.contracts.enums import DataSource
from data.contracts.social import SOCIAL_POST_FIELDS


def normalize_social_posts(
    rows: list[Mapping[str, Any]],
    *,
    source: str | DataSource,
    query: str | None = None,
    query_type: str | None = None,
    ingested_at: str | None = None,
) -> list[dict[str, Any]]:
    timestamp = ingested_at or datetime.now(timezone.utc).isoformat()
    source_value = str(source)
    normalized: dict[tuple[str, str], dict[str, Any]] = {}

    for row in rows:
        post_id = _text(_first_value(row, "post_id", "tweet_id", "tweetId", "id", "id_str"))
        if post_id is None:
            continue
        record = {
            "post_id": post_id,
            "author_id": _author_id(row),
            "author_username": _author_username(row),
            "created_at": _normalize_created_at(_first_value(row, "created_at", "createdAt", "created_time")),
            "text": _text(_first_value(row, "text", "full_text", "tweetText")),
            "lang": _text(_first_value(row, "lang", "language")),
            "like_count": _int_or_none(_first_value(row, "like_count", "likeCount", "likes")),
            "repost_count": _int_or_none(
                _first_value(row, "repost_count", "retweet_count", "retweetCount", "reposts")
            ),
            "reply_count": _int_or_none(_first_value(row, "reply_count", "replyCount", "replies")),
            "quote_count": _int_or_none(_first_value(row, "quote_count", "quoteCount", "quotes")),
            "view_count": _int_or_none(_first_value(row, "view_count", "viewCount", "views")),
            "query": query or _text(row.get("_ai3_query")),
            "query_type": query_type or _text(row.get("_ai3_query_type")),
            "source": source_value,
            "raw_json": json.dumps(dict(row), ensure_ascii=False, sort_keys=True, default=str),
            "ingested_at": timestamp,
        }
        normalized[(post_id, source_value)] = {field: record.get(field) for field in SOCIAL_POST_FIELDS}

    return [normalized[key] for key in sorted(normalized)]


def _author_username(row: Mapping[str, Any]) -> str | None:
    value = _first_value(row, "author_username", "authorUserName", "userName", "username")
    if value is not None:
        return _text(value)
    author = row.get("author")
    if isinstance(author, Mapping):
        return _text(_first_value(author, "userName", "username", "screen_name"))
    user = row.get("user")
    if isinstance(user, Mapping):
        return _text(_first_value(user, "userName", "username", "screen_name"))
    return None


def _author_id(row: Mapping[str, Any]) -> str | None:
    value = _first_value(row, "author_id", "authorId", "user_id", "userId")
    if value is not None:
        return _text(value)
    author = row.get("author")
    if isinstance(author, Mapping):
        return _text(_first_value(author, "id", "authorId", "user_id", "userId"))
    user = row.get("user")
    if isinstance(user, Mapping):
        return _text(_first_value(user, "id", "user_id", "userId"))
    return None


def _normalize_created_at(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if text.isdigit():
        return datetime.fromtimestamp(int(text), tz=timezone.utc).isoformat()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return int(Decimal(text))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid integer value: {text}") from None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_value(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return None
