from __future__ import annotations

from data.providers.x_provider import XProvider, build_time_bounded_query


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self):
        self.calls = []

    def get(self, url, params, headers):
        self.calls.append((url, params, headers))
        if len(self.calls) == 1:
            return FakeResponse(
                {
                    "tweets": [{"id": "1", "text": "first"}],
                    "next_cursor": "cursor-2",
                }
            )
        return FakeResponse({"tweets": [{"id": "2", "text": "second"}]})


def test_build_time_bounded_query_uses_unix_time_filters() -> None:
    query = build_time_bounded_query("AI", "1700000000", "1700003600")

    assert query == "AI since_time:1700000000 until_time:1700003600"


def test_x_provider_fetch_posts_paginates_and_adds_query_metadata() -> None:
    client = FakeClient()
    provider = XProvider(api_key="key", client=client, base_url="https://example.test")

    rows = provider.fetch_posts("AI", "1700000000", "1700003600", limit=2, sleep=0)

    assert [row["id"] for row in rows] == ["1", "2"]
    assert rows[0]["_ai3_query"] == "AI"
    assert rows[0]["_ai3_query_type"] == "Latest"
    assert len(client.calls) == 2
    url, params, headers = client.calls[0]
    assert url == "https://example.test/twitter/tweet/advanced_search"
    assert params["query"] == "AI since_time:1700000000 until_time:1700003600"
    assert params["queryType"] == "Latest"
    assert headers == {"x-api-key": "key"}
