from __future__ import annotations

import json

from data.normalizers.social_normalizer import normalize_social_posts


def test_normalize_social_posts_maps_twitterapi_fields() -> None:
    rows = [
        {
            "id": "tweet-1",
            "author": {"id": "author-1", "userName": "alice"},
            "createdAt": "2026-04-20T01:02:03Z",
            "text": "AI3 test",
            "lang": "en",
            "likeCount": "3",
            "retweetCount": "4",
            "replyCount": "5",
            "quoteCount": "6",
            "viewCount": "7",
            "_ai3_query": "AI3",
            "_ai3_query_type": "Latest",
        }
    ]

    normalized = normalize_social_posts(rows, source="x", ingested_at="now")

    assert normalized == [
        {
            "post_id": "tweet-1",
            "author_id": "author-1",
            "author_username": "alice",
            "created_at": "2026-04-20T01:02:03+00:00",
            "text": "AI3 test",
            "lang": "en",
            "like_count": 3,
            "repost_count": 4,
            "reply_count": 5,
            "quote_count": 6,
            "view_count": 7,
            "query": "AI3",
            "query_type": "Latest",
            "source": "x",
            "raw_json": normalized[0]["raw_json"],
            "ingested_at": "now",
        }
    ]
    assert json.loads(normalized[0]["raw_json"])["id"] == "tweet-1"


def test_normalize_social_posts_deduplicates_by_post_id_and_source() -> None:
    rows = [
        {"id": "tweet-1", "text": "old"},
        {"id": "tweet-1", "text": "new"},
        {"id": "", "text": "skip"},
    ]

    normalized = normalize_social_posts(rows, source="x", query="AI3", query_type="Top")

    assert len(normalized) == 1
    assert normalized[0]["text"] == "new"
    assert normalized[0]["query"] == "AI3"
    assert normalized[0]["query_type"] == "Top"
