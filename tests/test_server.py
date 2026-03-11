import asyncio
import time
from typing import Any, Dict, Optional

import httpx
import pytest

import hnmcp.server as server_mod


def _assert_signals(payload: Dict[str, Any]) -> None:
    assert "signals" in payload
    assert isinstance(payload["signals"], dict)


async def _call_tool(name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result = await server_mod.mcp.call_tool(name, args or {})
    return result.structured_content


@pytest.fixture(autouse=True)
async def reset_server_state() -> None:
    if hasattr(server_mod, "_reset_for_tests"):
        await server_mod._reset_for_tests()
    yield
    if hasattr(server_mod, "_reset_for_tests"):
        await server_mod._reset_for_tests()


@pytest.mark.asyncio
async def test_discover_top_stories(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/topstories.json"):
            return [101, 102]
        if url.endswith("/item/101.json"):
            return {
                "id": 101,
                "type": "story",
                "title": "Practical AI lessons",
                "by": "alice",
                "score": 90,
                "time": now - 300,
                "kids": [201],
                "text": "",
            }
        if url.endswith("/item/102.json"):
            return {
                "id": 102,
                "type": "story",
                "title": "Systems design writeup",
                "by": "bob",
                "score": 70,
                "time": now - 400,
                "kids": [],
                "text": "",
            }
        if url.endswith("/item/201.json"):
            return {
                "id": 201,
                "type": "comment",
                "by": "mentor",
                "text": "I built this in production",
                "time": now - 200,
                "parent": 101,
            }
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    payload = await _call_tool("discover_stories", {"limit": 5})

    assert payload["ok"] is True
    _assert_signals(payload)
    assert len(payload["stories"]) == 2
    assert all("signals" in story for story in payload["stories"])


@pytest.mark.asyncio
async def test_discover_personalized(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    class FakeProfile:
        keywords = ["security"]
        experts = ["trusted_expert"]
        min_score = 0
        time_hours = 24
        weights = {}

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/topstories.json"):
            return [1, 2]
        if url.endswith("/item/1.json"):
            return {
                "id": 1,
                "type": "story",
                "title": "Security postmortem at scale",
                "by": "trusted_expert",
                "score": 20,
                "time": now - 100,
                "kids": [],
            }
        if url.endswith("/item/2.json"):
            return {
                "id": 2,
                "type": "story",
                "title": "Frontend layout ideas",
                "by": "random_user",
                "score": 80,
                "time": now - 100,
                "kids": [],
            }
        return None

    monkeypatch.setattr(server_mod, "load_profile", lambda path=None: FakeProfile())
    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    payload = await _call_tool("discover_stories", {"limit": 10})
    titles = [story["title"] for story in payload["stories"]]

    assert payload["ok"] is True
    _assert_signals(payload)
    assert "Security postmortem at scale" in titles
    assert payload["stories"][0]["by"] == "trusted_expert"


@pytest.mark.asyncio
async def test_discover_search(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        if "algolia" in url:
            return {
                "hits": [
                    {
                        "objectID": "2001",
                        "story_id": "501",
                        "author": "builder",
                        "story_title": "Database migration lessons",
                        "comment_text": "I built this migration path in production.",
                        "created_at_i": int(time.time()) - 50,
                        "points": 35,
                    }
                ]
            }
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    practical = await _call_tool("search", {"query": "database", "focus": "practical", "limit": 5})
    debate = await _call_tool("search", {"query": "database", "focus": "debate", "limit": 5})
    expert = await _call_tool("search", {"query": "database", "focus": "expert", "limit": 5})

    assert practical["ok"] is True
    assert practical["focus"] == "practical"
    assert debate["focus"] == "debate"
    assert expert["focus"] == "expert"
    _assert_signals(practical)


@pytest.mark.asyncio
async def test_trust_find_experts(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        if "algolia" in url:
            return {
                "hits": [
                    {"author": "alice", "comment_text": "I built this", "points": 20},
                    {"author": "alice", "comment_text": "We used this", "points": 15},
                    {"author": "bob", "comment_text": "Interesting", "points": 2},
                ]
            }
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    payload = await _call_tool("find_experts", {"topic": "security", "limit": 5})

    assert payload["ok"] is True
    _assert_signals(payload)
    assert payload["experts"][0]["username"] == "alice"
    assert "trust_score" in payload["experts"][0]


@pytest.mark.asyncio
async def test_trust_expert_content_boosted(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    class FakeProfile:
        keywords = []
        experts = ["seed_expert"]
        min_score = 0
        time_hours = 24
        weights = {}

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/topstories.json"):
            return [11, 12]
        if url.endswith("/item/11.json"):
            return {
                "id": 11,
                "type": "story",
                "title": "Non expert story",
                "by": "other",
                "score": 80,
                "time": now - 100,
                "kids": [],
            }
        if url.endswith("/item/12.json"):
            return {
                "id": 12,
                "type": "story",
                "title": "Expert story",
                "by": "seed_expert",
                "score": 20,
                "time": now - 100,
                "kids": [],
            }
        return None

    monkeypatch.setattr(server_mod, "load_profile", lambda path=None: FakeProfile())
    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    payload = await _call_tool("discover_stories", {"limit": 5})
    assert payload["stories"][0]["title"] == "Expert story"


@pytest.mark.asyncio
async def test_understand_story_brief(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    class FakeProfile:
        keywords = []
        experts = ["expert_user"]
        min_score = 0
        time_hours = 24
        weights = {}

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/item/300.json"):
            return {
                "id": 300,
                "type": "story",
                "title": "Storage migration",
                "by": "author",
                "score": 100,
                "time": now - 100,
                "kids": [301, 302],
            }
        if url.endswith("/item/301.json"):
            return {
                "id": 301,
                "type": "comment",
                "by": "expert_user",
                "text": "I built this in production with benchmarks.",
                "time": now - 80,
                "parent": 300,
            }
        if url.endswith("/item/302.json"):
            return {
                "id": 302,
                "type": "comment",
                "by": "other",
                "text": "Thanks for sharing",
                "time": now - 70,
                "parent": 300,
            }
        return None

    monkeypatch.setattr(server_mod, "load_profile", lambda path=None: FakeProfile())
    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    payload = await _call_tool("story_brief", {"story_id": 300})
    assert payload["ok"] is True
    _assert_signals(payload)
    assert payload["story"]["id"] == 300
    assert len(payload["top_comments"]) == 2
    assert payload["expert_highlights"][0]["by"] == "expert_user"


@pytest.mark.asyncio
async def test_understand_signals_present(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        if url.endswith("/topstories.json"):
            return [501]
        if url.endswith("/item/501.json"):
            return {
                "id": 501,
                "type": "story",
                "title": "Story",
                "by": "u1",
                "score": 5,
                "time": now - 20,
                "kids": [],
            }
        if url.endswith("/item/777.json"):
            return {
                "id": 777,
                "type": "story",
                "title": "Thread",
                "by": "u1",
                "score": 5,
                "time": now - 20,
                "kids": [],
            }
        if "algolia" in url:
            return {"hits": [{"author": "u1", "comment_text": "I built this", "points": 3}]}
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    outputs = [
        await _call_tool("discover_stories", {"limit": 3}),
        await _call_tool("search", {"query": "x"}),
        await _call_tool("find_experts", {"topic": "x"}),
        await _call_tool("expert_brief", {"username": "u1", "topic": "x"}),
        await _call_tool("story_brief", {"story_id": 777}),
        await _call_tool("thread_analysis", {"story_id": 777}),
    ]
    for output in outputs:
        _assert_signals(output)


@pytest.mark.asyncio
async def test_error_handling_404(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/topstories.json"):
            raise httpx.HTTPStatusError(
                "not found", request=httpx.Request("GET", url), response=httpx.Response(404)
            )
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    payload = await _call_tool("discover_stories", {"limit": 3})

    assert payload["ok"] is False
    _assert_signals(payload)
    assert payload["error"]["type"] == "http_error"
    assert payload["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_error_handling_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        if "algolia" in url:
            raise httpx.TimeoutException("timeout")
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    payload = await _call_tool("search", {"query": "timeout"})

    assert payload["ok"] is False
    _assert_signals(payload)
    assert payload["error"]["type"] == "timeout"


@pytest.mark.asyncio
async def test_error_handling_null_item(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/topstories.json"):
            return [9001, 9002]
        if url.endswith("/item/9001.json"):
            return None
        if url.endswith("/item/9002.json"):
            return {
                "id": 9002,
                "type": "story",
                "title": "Valid story",
                "by": "user",
                "score": 3,
                "time": now - 10,
                "kids": [],
            }
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    payload = await _call_tool("discover_stories", {"limit": 5})

    assert payload["ok"] is True
    assert len(payload["stories"]) == 1
    assert payload["stories"][0]["id"] == 9002


@pytest.mark.asyncio
async def test_concurrent_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())
    active = 0
    peak = 0

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        nonlocal active, peak
        if url.endswith("/topstories.json"):
            return [6001, 6002, 6003, 6004]
        if "/item/" in url:
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.02)
            active -= 1
            story_id = int(url.rsplit("/", 1)[-1].split(".")[0])
            return {
                "id": story_id,
                "type": "story",
                "title": f"Story {story_id}",
                "by": "u",
                "score": 1,
                "time": now - 5,
                "kids": [],
            }
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    payload = await _call_tool("discover_stories", {"limit": 4})

    assert payload["ok"] is True
    assert peak >= 2


@pytest.mark.asyncio
async def test_lifespan_shared_client(monkeypatch: pytest.MonkeyPatch) -> None:
    init_calls = 0

    class CountingClient(httpx.AsyncClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            nonlocal init_calls
            init_calls += 1
            super().__init__(*args, **kwargs)

    now = int(time.time())

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        if url.endswith("/topstories.json"):
            return [7001]
        if url.endswith("/item/7001.json"):
            return {
                "id": 7001,
                "type": "story",
                "title": "Shared client",
                "by": "u",
                "score": 1,
                "time": now - 1,
                "kids": [],
            }
        if "algolia" in url:
            return {"hits": []}
        return None

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", CountingClient)
    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    await _call_tool("discover_stories", {"limit": 1})
    await _call_tool("search", {"query": "x", "limit": 1})

    assert init_calls == 1

    tools = await server_mod.mcp.list_tools()
    resources = await server_mod.mcp.list_resources()
    assert len(tools) == 6
    assert len(resources) == 2


@pytest.mark.asyncio
async def test_error_format_variations(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if "topstories" in url:
            raise httpx.TimeoutException("Request timeout")
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    result = await _call_tool("discover_stories", {"limit": 1})
    assert result["ok"] is False
    assert result["error"]["type"] == "timeout"


@pytest.mark.asyncio
async def test_http_error_format(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if "topstories" in url:
            raise Exception("HTTP 500 Internal Server Error")
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    result = await _call_tool("discover_stories", {"limit": 1})
    assert result["ok"] is False
    assert result["error"]["type"] == "http_error"


@pytest.mark.asyncio
async def test_generic_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if "topstories" in url:
            raise ValueError("Invalid data format")
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    result = await _call_tool("discover_stories", {"limit": 1})
    assert result["ok"] is False
    assert result["error"]["type"] == "tool_error"


@pytest.mark.asyncio
async def test_fetch_json_http_status_error() -> None:
    client = httpx.AsyncClient()

    class MockResponse:
        status_code = 500

        def raise_for_status(self):
            raise httpx.HTTPStatusError("500 error", request=None, response=self)

    async def mock_get(url: str, **kwargs: Any) -> MockResponse:
        return MockResponse()

    client.get = mock_get

    result = await server_mod._fetch_json(client, "https://example.com/test")
    assert result["ok"] is False
    assert "HTTP 500" in result["error"]


@pytest.mark.asyncio
async def test_fetch_json_timeout() -> None:
    client = httpx.AsyncClient()

    async def mock_get(url: str, **kwargs: Any) -> None:
        raise httpx.TimeoutException("timeout")

    client.get = mock_get

    result = await server_mod._fetch_json(client, "https://example.com/test")
    assert result["ok"] is False
    assert "timeout" in result["error"].lower()


@pytest.mark.asyncio
async def test_fetch_json_generic_exception() -> None:
    client = httpx.AsyncClient()

    async def mock_get(url: str, **kwargs: Any) -> None:
        raise ConnectionError("Network error")

    client.get = mock_get

    result = await server_mod._fetch_json(client, "https://example.com/test")
    assert result["ok"] is False
    assert "Network error" in result["error"]


@pytest.mark.asyncio
async def test_fetch_json_success() -> None:
    client = httpx.AsyncClient()

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": "test"}

    async def mock_get(url: str, **kwargs: Any) -> MockResponse:
        return MockResponse()

    client.get = mock_get

    result = await server_mod._fetch_json(client, "https://example.com/test")
    assert result == {"data": "test"}


@pytest.mark.asyncio
async def test_fetch_json_404_returns_none() -> None:
    client = httpx.AsyncClient()

    class Mock404Response:
        status_code = 404

        def raise_for_status(self):
            raise httpx.HTTPStatusError("404 not found", request=None, response=self)

    async def mock_get(url: str, **kwargs: Any) -> Mock404Response:
        return Mock404Response()

    client.get = mock_get

    result = await server_mod._fetch_json(client, "https://example.com/test")
    assert result is None


@pytest.mark.asyncio
async def test_discover_with_focus_practical(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/topstories.json"):
            return [101]
        if url.endswith("/item/101.json"):
            return {
                "id": 101,
                "type": "story",
                "title": "Test story",
                "by": "alice",
                "score": 50,
                "time": now - 300,
                "text": "I built this in production",
            }
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    result = await _call_tool("discover_stories", {"limit": 1, "focus": "practical"})
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_search_with_keywords(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if "algolia" in url:
            return {
                "hits": [
                    {
                        "objectID": "201",
                        "title": "AI story",
                        "author": "bob",
                        "points": 60,
                        "created_at_i": now - 600,
                    }
                ]
            }
        if url.endswith("/item/201.json"):
            return {
                "id": 201,
                "type": "story",
                "title": "AI story",
                "by": "bob",
                "score": 60,
                "time": now - 600,
            }
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    result = await _call_tool("search", {"query": "AI", "limit": 1})
    assert result["ok"] is True
    assert "results" in result


@pytest.mark.asyncio
async def test_thread_analysis_with_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/item/301.json"):
            return {
                "id": 301,
                "type": "story",
                "title": "Thread test",
                "by": "alice",
                "score": 50,
                "time": now - 300,
                "kids": [401, 402],
            }
        if url.endswith("/item/401.json"):
            return {
                "id": 401,
                "type": "comment",
                "by": "bob",
                "text": "First comment",
                "time": now - 200,
                "parent": 301,
                "kids": [501],
            }
        if url.endswith("/item/402.json"):
            return {
                "id": 402,
                "type": "comment",
                "by": "charlie",
                "text": "Second comment",
                "time": now - 100,
                "parent": 301,
            }
        if url.endswith("/item/501.json"):
            return {
                "id": 501,
                "type": "comment",
                "by": "dave",
                "text": "Nested comment",
                "time": now - 50,
                "parent": 401,
            }
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    result = await _call_tool("thread_analysis", {"story_id": 301, "max_depth": 3})
    assert result["ok"] is True
    assert result["comment_count"] == 3


@pytest.mark.asyncio
async def test_lifespan_initializes_runtime() -> None:
    async with server_mod._lifespan(server_mod.mcp) as runtime:
        assert "client" in runtime
        assert "cache" in runtime
        assert "profile" in runtime
        assert "trust_scores" in runtime
        assert "semaphore" in runtime


@pytest.mark.asyncio
async def test_get_runtime_populates_missing_lifespan_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server_mod, "load_profile", lambda: object())
    monkeypatch.setattr(server_mod, "load_trust_cache", lambda _path: {})

    class Ctx:
        lifespan_context = {}

    runtime = await server_mod._get_runtime(Ctx())

    assert "client" in runtime
    assert "cache" in runtime
    assert "profile" in runtime
    assert "trust_scores" in runtime
    assert "semaphore" in runtime


@pytest.mark.asyncio
async def test_fetch_items_parallel_skips_deleted_and_exceptions() -> None:
    class FakeCache:
        async def get_or_fetch(self, key: str, _fn: Any, _ttl: int) -> Any:
            if key.endswith(":1"):
                return {"id": 1, "type": "story", "deleted": True}
            if key.endswith(":2"):
                return {"id": 2, "type": "story", "dead": True}
            if key.endswith(":3"):
                raise RuntimeError("boom")
            return {"id": 4, "type": "story"}

    items = await server_mod._fetch_items_parallel(
        httpx.AsyncClient(), [1, 2, 3, 4], FakeCache(), asyncio.Semaphore(5)
    )
    assert [item["id"] for item in items] == [4]


def test_story_age_ok_false_for_non_int_time() -> None:
    assert server_mod._story_age_ok({"time": "bad"}, 1) is False


def test_aggregate_signals_skips_non_dict_signal_entries() -> None:
    agg = server_mod._aggregate_signals(
        [{"signals": "bad"}, {"signals": {"velocity": {"score": 1.0}}}]
    )
    assert agg["velocity"]["score"] == 0.5


def test_build_comment_depth_map_handles_orphans_and_invalid_parents() -> None:
    depth_map = server_mod._build_comment_depth_map(
        100,
        [
            {"id": 1, "parent": 100},
            {"id": 2, "parent": 9999},
            {"id": 3, "parent": "invalid"},
        ],
    )
    assert depth_map[1] == 1
    assert depth_map[2] == 1
    assert depth_map[3] == 1


@pytest.mark.asyncio
async def test_fetch_comment_subtree_handles_error_payload_and_child_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeCache:
        async def get_or_fetch(self, key: str, _fn: Any, _ttl: int) -> Any:
            if key.endswith(":900"):
                return {"ok": False, "error": {"x": 1}}
            if key.endswith(":1"):
                return {"id": 1, "type": "story", "kids": [2, 3]}
            if key.endswith(":2"):
                return {"id": 2, "type": "comment", "text": "ok"}
            raise RuntimeError("child failure")

    result1 = await server_mod._fetch_comment_subtree(
        httpx.AsyncClient(), FakeCache(), asyncio.Semaphore(5), 900
    )
    result2 = await server_mod._fetch_comment_subtree(
        httpx.AsyncClient(), FakeCache(), asyncio.Semaphore(5), 1
    )

    assert result1 == []
    assert len(result2) == 1
    assert result2[0]["id"] == 2


@pytest.mark.asyncio
async def test_discover_stories_non_list_topstories_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/topstories.json"):
            return {"bad": True}
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    payload = await _call_tool("discover_stories", {"limit": 3})
    assert payload["ok"] is False


@pytest.mark.asyncio
async def test_search_invalid_algolia_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        if "non_dict" in str(params.get("query")):
            return []
        return {"hits": "bad"}

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    non_dict_payload = await _call_tool("search", {"query": "non_dict"})
    bad_hits_payload = await _call_tool("search", {"query": "bad_hits"})

    assert non_dict_payload["ok"] is False
    assert bad_hits_payload["ok"] is False


@pytest.mark.asyncio
async def test_search_skips_invalid_hits_and_low_points(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        return {
            "hits": [
                "not-a-dict",
                {"objectID": "1", "author": "a", "points": 1, "created_at_i": int(time.time())},
                {
                    "objectID": "2",
                    "author": "seed",
                    "points": 100,
                    "created_at_i": int(time.time()),
                },
            ]
        }

    class FakeProfile:
        keywords = []
        experts = ["seed"]
        min_score = 10
        time_hours = 24
        weights = {}

    monkeypatch.setattr(server_mod, "load_profile", lambda path=None: FakeProfile())
    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    payload = await _call_tool("search", {"query": "x", "limit": 10})
    assert payload["ok"] is True
    assert len(payload["results"]) == 1
    assert payload["results"][0]["by"] == "seed"


@pytest.mark.asyncio
async def test_find_experts_error_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        query = params.get("query") if isinstance(params, dict) else ""
        if query == "non_dict":
            return []
        if query == "bad_hits":
            return {"hits": "bad"}
        return {"hits": [{"author": "x"}, "bad"]}

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    payload1 = await _call_tool("find_experts", {"topic": "non_dict"})
    payload2 = await _call_tool("find_experts", {"topic": "bad_hits"})

    assert payload1["ok"] is False
    assert payload2["ok"] is False


@pytest.mark.asyncio
async def test_expert_brief_error_shapes_and_filtering(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        if "/user/" in url:
            return {"id": "u"}
        query = params.get("query") if isinstance(params, dict) else ""
        if query == "non_dict":
            return []
        if query == "bad_hits":
            return {"hits": "bad"}
        return {
            "hits": [
                "bad",
                {
                    "author": "other",
                    "objectID": "1",
                    "comment_text": "x",
                    "created_at_i": int(time.time()),
                },
                {
                    "author": "u",
                    "objectID": "2",
                    "comment_text": "y",
                    "created_at_i": int(time.time()),
                },
            ]
        }

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    payload1 = await _call_tool("expert_brief", {"username": "u", "topic": "non_dict"})
    payload2 = await _call_tool("expert_brief", {"username": "u", "topic": "bad_hits"})
    payload3 = await _call_tool("expert_brief", {"username": "u", "topic": "ok"})

    assert payload1["ok"] is False
    assert payload2["ok"] is False
    assert payload3["ok"] is True
    assert len(payload3["recent_comments"]) == 1


@pytest.mark.asyncio
async def test_story_brief_and_thread_analysis_not_found_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if "/item/999.json" in url:
            return {"id": 999, "type": "comment"}
        if "/item/1000.json" in url:
            return {"id": 1000, "type": "comment"}
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    brief = await _call_tool("story_brief", {"story_id": 999})
    thread = await _call_tool("thread_analysis", {"story_id": 1000})

    assert brief["ok"] is False
    assert thread["ok"] is False


@pytest.mark.asyncio
async def test_thread_analysis_depth_and_expert_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    class FakeProfile:
        keywords = []
        experts = ["expert"]
        min_score = 0
        time_hours = 24
        weights = {}

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/item/2000.json"):
            return {"id": 2000, "type": "story", "by": "s", "time": now, "kids": [2001, 2002]}
        if url.endswith("/item/2001.json"):
            return {"id": 2001, "type": "comment", "by": "expert", "parent": 2000, "time": now}
        if url.endswith("/item/2002.json"):
            return {"id": 2002, "type": "comment", "by": "other", "parent": 2001, "time": now}
        return None

    monkeypatch.setattr(server_mod, "load_profile", lambda path=None: FakeProfile())
    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    payload = await _call_tool(
        "thread_analysis", {"story_id": 2000, "expert_only": True, "max_depth": 1}
    )
    assert payload["ok"] is True
    assert payload["comment_count"] == 1


@pytest.mark.asyncio
async def test_get_config_and_get_trust_resources() -> None:
    class Ctx:
        lifespan_context = {
            "profile": type(
                "P",
                (),
                {
                    "keywords": ["ai"],
                    "experts": ["x"],
                    "min_score": 1,
                    "time_hours": 2,
                    "weights": {"w": 1.0},
                },
            )(),
            "trust_scores": "bad",
        }

    config_json = await server_mod.get_config(Ctx())
    trust_json = await server_mod.get_trust(Ctx())

    assert '"keywords": ["ai"]' in config_json
    assert trust_json == "{}"


def test_server_main_calls_mcp_run(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"run": False}

    class FakeMCP:
        def run(self) -> None:
            called["run"] = True

    monkeypatch.setattr(server_mod, "mcp", FakeMCP())
    server_mod.main()
    assert called["run"] is True


@pytest.mark.asyncio
async def test_init_runtime_fallback_double_check_inside_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await server_mod._reset_for_tests()

    class FakeLock:
        async def __aenter__(self) -> None:
            server_mod._RUNTIME_FALLBACK["client"] = object()

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

    monkeypatch.setattr(server_mod, "_RUNTIME_LOCK", FakeLock())
    runtime = await server_mod._init_runtime_fallback()
    assert "client" in runtime


@pytest.mark.asyncio
async def test_get_runtime_adds_profile_and_trust_to_partial_lifespan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server_mod, "load_profile", lambda: {"profile": True})
    monkeypatch.setattr(server_mod, "load_trust_cache", lambda _path: {"alice": 0.2})

    class Ctx:
        lifespan_context = {
            "client": httpx.AsyncClient(),
            "cache": server_mod.TTLCache(),
            "semaphore": asyncio.Semaphore(1),
        }

    runtime = await server_mod._get_runtime(Ctx())
    assert runtime["profile"] == {"profile": True}
    assert runtime["trust_scores"] == {"alice": 0.2}


def test_build_comment_depth_map_marks_unresolved_cycles() -> None:
    depth_map = server_mod._build_comment_depth_map(
        5000,
        [
            {"id": 1, "parent": 2},
            {"id": 2, "parent": 1},
        ],
    )
    assert depth_map[1] == 1
    assert depth_map[2] == 1


@pytest.mark.asyncio
async def test_discover_stories_filters_non_story_low_score_and_old(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = int(time.time())

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/topstories.json"):
            return [100, 101, 102, 103]
        if url.endswith("/item/100.json"):
            return {"id": 100, "type": "comment", "score": 99, "time": now, "title": "x", "by": "u"}
        if url.endswith("/item/101.json"):
            return {"id": 101, "type": "story", "score": 1, "time": now, "title": "x", "by": "u"}
        if url.endswith("/item/102.json"):
            return {
                "id": 102,
                "type": "story",
                "score": 99,
                "time": now - 3600 * 100,
                "title": "x",
                "by": "u",
            }
        if url.endswith("/item/103.json"):
            return {
                "id": 103,
                "type": "story",
                "score": 99,
                "time": now,
                "title": "valid",
                "by": "u",
            }
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    payload = await _call_tool("discover_stories", {"limit": 10, "min_score": 10, "hours": 24})
    assert payload["ok"] is True
    assert [story["id"] for story in payload["stories"]] == [103]


@pytest.mark.asyncio
async def test_find_experts_handles_error_payload_and_nested_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        tags = params.get("tags") if isinstance(params, dict) else ""
        query = params.get("query") if isinstance(params, dict) else ""
        if query == "error_payload":
            return {"ok": False, "error": "boom", "context": {"status_code": 500}}
        if tags == "comment":
            return {"hits": [{"author": "seed"}, "skip"]}
        if tags == "comment,author_seed":
            return {"hits": "bad"}
        return {"ok": False, "error": "nested"}

    class FakeProfile:
        keywords = []
        experts = ["seed"]
        min_score = 0
        time_hours = 24
        weights = {}

    monkeypatch.setattr(server_mod, "load_profile", lambda path=None: FakeProfile())
    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    error_payload = await _call_tool("find_experts", {"topic": "error_payload"})
    ok_payload = await _call_tool("find_experts", {"topic": "normal"})

    assert error_payload["ok"] is False
    assert ok_payload["ok"] is True


@pytest.mark.asyncio
async def test_expert_brief_error_payload_for_user_and_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_json(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        query = params.get("query") if isinstance(params, dict) else ""
        if "/user/" in url:
            return {"ok": False, "error": "user", "context": {"status_code": 500}}
        if query == "activity_error":
            return {"ok": False, "error": "activity", "context": {"status_code": 500}}
        return {"hits": []}

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)

    user_err = await _call_tool("expert_brief", {"username": "u", "topic": "x"})
    activity_err = await _call_tool("expert_brief", {"username": "v", "topic": "activity_error"})

    assert user_err["ok"] is False
    assert activity_err["ok"] is False


@pytest.mark.asyncio
async def test_story_brief_handles_comment_exception_and_non_int_comment_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = int(time.time())

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/item/7100.json"):
            return {"id": 7100, "type": "story", "by": "s", "time": now, "kids": [7101, 7102]}
        if url.endswith("/item/7101.json"):
            return {"id": "not-int", "type": "comment", "by": "a", "parent": 7100, "time": now}
        if url.endswith("/item/7102.json"):
            raise RuntimeError("boom")
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    payload = await _call_tool("story_brief", {"story_id": 7100})
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_thread_analysis_error_payload_and_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    async def fake_fetch_json(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/item/7200.json"):
            return {"ok": False, "error": "bad", "context": {"status_code": 500}}
        if url.endswith("/item/7201.json"):
            return {"id": 7201, "type": "story", "by": "s", "time": now, "kids": [7202, 7203]}
        if url.endswith("/item/7202.json"):
            return {"id": "bad", "type": "comment", "by": "expert", "parent": 7201, "time": now}
        if url.endswith("/item/7203.json"):
            raise RuntimeError("boom")
        return None

    monkeypatch.setattr(server_mod, "_fetch_json", fake_fetch_json)
    err_payload = await _call_tool("thread_analysis", {"story_id": 7200})
    ok_payload = await _call_tool("thread_analysis", {"story_id": 7201, "expert_only": True})

    assert err_payload["ok"] is False
    assert ok_payload["ok"] is True


@pytest.mark.asyncio
async def test_find_experts_author_payload_error_and_exception_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_safe_fetch(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        tags = params.get("tags") if isinstance(params, dict) else ""
        if tags == "comment":
            return {"hits": [{"author": "u1"}, {"author": "u2"}]}
        if tags == "comment,author_u1":
            return {"ok": False, "error": "bad", "context": {"status_code": 500}}
        if tags == "comment,author_u2":
            raise RuntimeError("boom")
        return {"hits": []}

    monkeypatch.setattr(server_mod, "_safe_fetch_json", fake_safe_fetch)
    payload = await _call_tool("find_experts", {"topic": "x", "limit": 5})
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_find_experts_expert_bonus_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_safe_fetch(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        tags = params.get("tags") if isinstance(params, dict) else ""
        if tags == "comment":
            return {"hits": [{"author": "seed"}]}
        if tags == "comment,author_seed":
            return {
                "hits": [
                    {
                        "author": "seed",
                        "objectID": "1",
                        "comment_text": "I built this",
                        "created_at_i": int(time.time()),
                        "points": 10,
                    }
                ]
            }
        return {"hits": []}

    class FakeProfile:
        keywords = []
        experts = ["seed"]
        min_score = 0
        time_hours = 24
        weights = {}

    monkeypatch.setattr(server_mod, "load_profile", lambda path=None: FakeProfile())
    monkeypatch.setattr(server_mod, "_safe_fetch_json", fake_safe_fetch)

    payload = await _call_tool("find_experts", {"topic": "x", "limit": 5})
    assert payload["ok"] is True
    assert payload["experts"][0]["username"] == "seed"


@pytest.mark.asyncio
async def test_expert_brief_comments_error_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_safe_fetch(client: httpx.AsyncClient, url: str, params=None, **_: Any) -> Any:
        if "/user/" in url:
            return {"id": "u"}
        return {"ok": False, "error": "activity failed", "context": {"status_code": 500}}

    monkeypatch.setattr(server_mod, "_safe_fetch_json", fake_safe_fetch)
    payload = await _call_tool("expert_brief", {"username": "u", "topic": "x"})
    assert payload["ok"] is False


@pytest.mark.asyncio
async def test_story_brief_comment_gather_exception_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    async def fake_safe_fetch(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/item/8100.json"):
            return {"id": 8100, "type": "story", "by": "s", "time": now, "kids": [8101, 8102]}
        return None

    async def fake_subtree(_client: Any, _cache: Any, _sem: Any, item_id: int) -> Any:
        if item_id == 8101:
            raise RuntimeError("boom")
        return [{"id": 8102, "type": "comment", "by": "u", "parent": 8100, "time": now}]

    monkeypatch.setattr(server_mod, "_safe_fetch_json", fake_safe_fetch)
    monkeypatch.setattr(server_mod, "_fetch_comment_subtree", fake_subtree)

    payload = await _call_tool("story_brief", {"story_id": 8100})
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_thread_analysis_comment_gather_exception_and_expert_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = int(time.time())

    async def fake_safe_fetch(client: httpx.AsyncClient, url: str, **_: Any) -> Any:
        if url.endswith("/item/8200.json"):
            return {"id": 8200, "type": "story", "by": "s", "time": now, "kids": [8201, 8202]}
        return None

    async def fake_subtree(_client: Any, _cache: Any, _sem: Any, item_id: int) -> Any:
        if item_id == 8201:
            raise RuntimeError("boom")
        return [{"id": 8202, "type": "comment", "by": "non_expert", "parent": 8200, "time": now}]

    class FakeProfile:
        keywords = []
        experts = ["expert"]
        min_score = 0
        time_hours = 24
        weights = {}

    monkeypatch.setattr(server_mod, "load_profile", lambda path=None: FakeProfile())
    monkeypatch.setattr(server_mod, "_safe_fetch_json", fake_safe_fetch)
    monkeypatch.setattr(server_mod, "_fetch_comment_subtree", fake_subtree)

    payload = await _call_tool("thread_analysis", {"story_id": 8200, "expert_only": True})
    assert payload["ok"] is True
    assert payload["comment_count"] == 0
