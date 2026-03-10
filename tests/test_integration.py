import time
from collections.abc import AsyncGenerator
from typing import Any, Dict, Optional

import httpx
import pytest
import respx

import hnmcp.server as server_mod


def _assert_signals(payload: Dict[str, Any]) -> None:
    assert "signals" in payload
    assert isinstance(payload["signals"], dict)


async def _call_tool(name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result = await server_mod.mcp.call_tool(name, args or {})
    payload = result.structured_content
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(autouse=True)
async def reset_server_state() -> AsyncGenerator[None, None]:
    if hasattr(server_mod, "_reset_for_tests"):
        await server_mod._reset_for_tests()
    yield
    if hasattr(server_mod, "_reset_for_tests"):
        await server_mod._reset_for_tests()


@pytest.mark.asyncio
async def test_full_workflow_discover_to_brief() -> None:
    now = int(time.time())

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/topstories.json").respond(json=[1001, 1002])
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/1001.json").respond(
            json={
                "id": 1001,
                "type": "story",
                "title": "Practical security lessons",
                "by": "alice",
                "score": 120,
                "time": now - 300,
                "kids": [2001],
                "text": "in production rollout details",
            }
        )
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/1002.json").respond(
            json={
                "id": 1002,
                "type": "story",
                "title": "General frontend notes",
                "by": "bob",
                "score": 20,
                "time": now - 300,
                "kids": [],
                "text": "",
            }
        )
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/2001.json").respond(
            json={
                "id": 2001,
                "type": "comment",
                "by": "mentor",
                "text": "I built this migration at scale with 40% improvement.",
                "time": now - 100,
                "parent": 1001,
            }
        )

        discover = await _call_tool("discover_stories", {"keywords": "security", "limit": 5})
        assert discover["ok"] is True
        assert len(discover["stories"]) >= 1
        top_story = discover["stories"][0]

        brief = await _call_tool("story_brief", {"story_id": int(top_story["id"])})
        assert brief["ok"] is True
        _assert_signals(discover)
        _assert_signals(brief)
        assert brief["story"]["id"] == top_story["id"]
        assert "practitioner_depth" in brief["signals"]
        assert "expert_involvement" in brief["signals"]


@pytest.mark.asyncio
async def test_expert_discovery_to_content() -> None:
    now = int(time.time())

    def algolia_side_effect(request: httpx.Request) -> httpx.Response:
        tags = request.url.params.get("tags", "")
        if tags == "comment":
            return httpx.Response(
                200,
                json={
                    "hits": [
                        {"author": "sec_guru", "comment_text": "I built this", "points": 25},
                        {"author": "random", "comment_text": "maybe", "points": 1},
                    ]
                },
            )
        if tags == "comment,author_sec_guru":
            return httpx.Response(
                200,
                json={
                    "hits": [
                        {
                            "author": "sec_guru",
                            "comment_text": "we used this in production",
                            "points": 20,
                            "created_at_i": now - 100,
                            "objectID": "8801",
                            "story_id": "1001",
                            "story_title": "Security checklist",
                        }
                    ]
                },
            )
        if tags == "comment,author_random":
            return httpx.Response(200, json={"hits": []})
        return httpx.Response(200, json={"hits": []})

    with respx.mock(assert_all_called=False) as mock:
        mock.get(server_mod.ALGOLIA_URL).mock(side_effect=algolia_side_effect)
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/user/sec_guru.json").respond(
            json={"id": "sec_guru", "karma": 9000}
        )

        experts = await _call_tool("find_experts", {"topic": "security", "limit": 5})
        assert experts["ok"] is True
        assert experts["experts"]
        top = experts["experts"][0]["username"]

        brief = await _call_tool("expert_brief", {"username": top, "topic": "security"})
        assert brief["ok"] is True
        assert brief["username"] == "sec_guru"
        assert isinstance(brief["trust_score"], float)
        _assert_signals(experts)
        _assert_signals(brief)


@pytest.mark.asyncio
async def test_profile_affects_ranking(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    class FakeProfile:
        keywords = ["security", "incident"]
        experts = []
        min_score = 0
        time_hours = 24
        weights = {}

    monkeypatch.setattr(server_mod, "load_profile", lambda path=None: FakeProfile())

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/topstories.json").respond(json=[3001, 3002])
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/3001.json").respond(
            json={
                "id": 3001,
                "type": "story",
                "title": "Security incident postmortem",
                "by": "a1",
                "score": 10,
                "time": now - 60,
                "kids": [],
            }
        )
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/3002.json").respond(
            json={
                "id": 3002,
                "type": "story",
                "title": "CSS animation gallery",
                "by": "a2",
                "score": 80,
                "time": now - 60,
                "kids": [],
            }
        )

        payload = await _call_tool("discover_stories", {"limit": 5})
        assert payload["ok"] is True
        assert payload["stories"][0]["id"] == 3001
        _assert_signals(payload)


@pytest.mark.asyncio
async def test_cache_hit_on_repeat() -> None:
    now = int(time.time())

    with respx.mock(assert_all_called=False) as mock:
        top_route = mock.get(f"{server_mod.FIREBASE_BASE_URL}/topstories.json").respond(json=[4001])
        item_route = mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/4001.json").respond(
            json={
                "id": 4001,
                "type": "story",
                "title": "Caching test story",
                "by": "cache_user",
                "score": 15,
                "time": now - 50,
                "kids": [],
            }
        )

        first = await _call_tool("discover_stories", {"limit": 1})
        second = await _call_tool("discover_stories", {"limit": 1})

        assert first["ok"] is True
        assert second["ok"] is True
        assert top_route.call_count == 1
        assert item_route.call_count == 1


@pytest.mark.asyncio
async def test_embeddings_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())

    def block_embeddings(name: str, globals=None, locals=None, fromlist=(), level=0):
        if name == "sentence_transformers":
            raise ImportError("missing optional dependency")
        return original_import(name, globals, locals, fromlist, level)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", block_embeddings)

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/topstories.json").respond(json=[5001])
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/5001.json").respond(
            json={
                "id": 5001,
                "type": "story",
                "title": "No embeddings required",
                "by": "user",
                "score": 8,
                "time": now - 30,
                "kids": [],
            }
        )
        mock.get(server_mod.ALGOLIA_URL).respond(json={"hits": []})

        discover = await _call_tool("discover_stories", {"limit": 1})
        search = await _call_tool("search", {"query": "security", "limit": 1})

        assert discover["ok"] is True
        assert search["ok"] is True


@pytest.mark.asyncio
async def test_error_recovery() -> None:
    now = int(time.time())

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/topstories.json").respond(json=[6001, 6002, 6003])
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/6001.json").respond(
            json={
                "id": 6001,
                "type": "story",
                "title": "Healthy story",
                "by": "ok1",
                "score": 50,
                "time": now - 30,
                "kids": [],
            }
        )
        failing_route = mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/6002.json").respond(
            status_code=500
        )
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/6003.json").respond(
            json={
                "id": 6003,
                "type": "story",
                "title": "Still returned",
                "by": "ok2",
                "score": 40,
                "time": now - 30,
                "kids": [],
            }
        )

        payload = await _call_tool("discover_stories", {"limit": 5})
        assert payload["ok"] is True
        returned_ids = {story["id"] for story in payload["stories"]}
        assert returned_ids == {6001, 6003}
        assert failing_route.called is True

        single_error = await _call_tool("story_brief", {"story_id": 6002})
        assert single_error["ok"] is False
        assert single_error["error"]["type"] == "http_error"
        assert single_error["context"]["status_code"] == 500


@pytest.mark.asyncio
async def test_deleted_items_handled() -> None:
    now = int(time.time())

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/7001.json").respond(
            json={
                "id": 7001,
                "type": "story",
                "title": "Deleted nodes in thread",
                "by": "author",
                "score": 70,
                "time": now - 40,
                "kids": [7101, 7102, 7103],
            }
        )
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/7101.json").respond(
            json={
                "id": 7101,
                "type": "comment",
                "by": "good",
                "text": "I built this in production",
                "time": now - 20,
                "parent": 7001,
            }
        )
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/7102.json").respond(
            json={
                "id": 7102,
                "type": "comment",
                "by": "deleted_user",
                "text": "removed",
                "time": now - 19,
                "parent": 7001,
                "deleted": True,
            }
        )
        mock.get(f"{server_mod.FIREBASE_BASE_URL}/item/7103.json").respond(
            json={
                "id": 7103,
                "type": "comment",
                "by": "dead_user",
                "text": "dead",
                "time": now - 18,
                "parent": 7001,
                "dead": True,
            }
        )

        payload = await _call_tool("story_brief", {"story_id": 7001})
        assert payload["ok"] is True
        assert payload["total_comments"] == 1
        assert len(payload["top_comments"]) == 1
        assert payload["top_comments"][0]["id"] == 7101
        _assert_signals(payload)
