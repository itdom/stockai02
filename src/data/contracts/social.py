"""Social data contract definitions."""

from __future__ import annotations

SOCIAL_POST_FIELDS: tuple[str, ...] = (
    "post_id",
    "author_id",
    "author_username",
    "created_at",
    "text",
    "lang",
    "like_count",
    "repost_count",
    "reply_count",
    "quote_count",
    "view_count",
    "query",
    "query_type",
    "source",
    "raw_json",
    "ingested_at",
)

SOCIAL_POST_PRIMARY_KEY: tuple[str, ...] = ("post_id", "source")

SOCIAL_ENTITY_MENTION_FIELDS: tuple[str, ...] = (
    "post_id",
    "entity_type",
    "entity_id",
    "entity_name",
    "match_text",
    "match_method",
    "confidence",
    "source",
    "created_at",
)
