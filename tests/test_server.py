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
