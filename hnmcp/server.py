import asyncio
import json
import time

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import httpx

from fastmcp import Context, FastMCP

from hnmcp.cache import ITEM_TTL, STORY_TTL, TTLCache
from hnmcp.profiles import load_profile
from hnmcp.quality import calculate_quality_score, calculate_signals
from hnmcp.trust import get_trust_score, load_trust_cache


FIREBASE_BASE_URL = "https://hacker-news.firebaseio.com/v0"
ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"
DEFAULT_TIMEOUT = 30.0
TRUST_CACHE_PATH = str(Path("~/.hnmcp/trust_cache.json").expanduser())


mcp = FastMCP("hnmcp")

_RUNTIME_FALLBACK: Dict[str, Any] = {}
_RUNTIME_LOCK = asyncio.Lock()


def _empty_signals() -> Dict[str, Any]:
    return {
        "practitioner_depth": {"score": 0.0, "markers": []},
        "velocity": {"score": 0.0, "points_per_hour": 0.0},
        "reference_density": {"score": 0.0, "link_count": 0},
        "thread_depth": {"score": 0.0, "max_depth": 0},
        "expert_involvement": {"score": 0.0, "experts": [], "trust_scores": {}},
    }


def _error_payload(error: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    error_context = context or {}
    lowered_error = error.lower()
    if "status_code" in error_context:
        error_type = "http_error"
    elif "timeout" in lowered_error:
        error_type = "timeout"
    elif lowered_error.startswith("http "):
        error_type = "http_error"
    else:
        error_type = "tool_error"

    return {
        "ok": False,
        "error": {
            "type": error_type,
            "message": error,
            "status_code": error_context.get("status_code"),
        },
        "context": error_context,
        "signals": _empty_signals(),
    }


def _is_error_response(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("ok") is False and "error" in payload


@asynccontextmanager
async def _lifespan(_: FastMCP):
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        yield {
            "client": client,
            "cache": TTLCache(),
            "profile": load_profile(),
            "trust_scores": load_trust_cache(TRUST_CACHE_PATH) or {},
            "semaphore": asyncio.Semaphore(10),
        }


mcp_with_lifespan = FastMCP("hnmcp", lifespan=_lifespan)
mcp = mcp_with_lifespan


async def _init_runtime_fallback() -> Dict[str, Any]:
    if _RUNTIME_FALLBACK:
        return _RUNTIME_FALLBACK

    async with _RUNTIME_LOCK:
        if _RUNTIME_FALLBACK:
            return _RUNTIME_FALLBACK
        _RUNTIME_FALLBACK["client"] = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        _RUNTIME_FALLBACK["cache"] = TTLCache()
        _RUNTIME_FALLBACK["profile"] = load_profile()
        _RUNTIME_FALLBACK["trust_scores"] = load_trust_cache(TRUST_CACHE_PATH) or {}
        _RUNTIME_FALLBACK["semaphore"] = asyncio.Semaphore(10)
        return _RUNTIME_FALLBACK


async def _get_runtime(ctx: Context) -> Dict[str, Any]:
    if ctx.lifespan_context:
        runtime = ctx.lifespan_context
        if "client" not in runtime:
            runtime["client"] = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        if "cache" not in runtime:
            runtime["cache"] = TTLCache()
        if "profile" not in runtime:
            runtime["profile"] = load_profile()
        if "trust_scores" not in runtime:
            runtime["trust_scores"] = load_trust_cache(TRUST_CACHE_PATH) or {}
        if "semaphore" not in runtime:
            runtime["semaphore"] = asyncio.Semaphore(10)
        return runtime
    return await _init_runtime_fallback()


async def _fetch_json(client: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
    try:
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        return {
            "ok": False,
            "error": f"HTTP {exc.response.status_code}",
            "context": {"url": url, "status_code": exc.response.status_code},
        }
    except httpx.TimeoutException:
        return {"ok": False, "error": "Request timeout", "context": {"url": url}}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "context": {"url": url}}


async def _safe_fetch_json(client: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
    try:
        return await _fetch_json(client, url, **kwargs)
    except httpx.HTTPStatusError as exc:
        return {
            "ok": False,
            "error": f"HTTP {exc.response.status_code}",
            "context": {"url": url, "status_code": exc.response.status_code},
        }
    except httpx.TimeoutException:
        return {"ok": False, "error": "Request timeout", "context": {"url": url}}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "context": {"url": url}}


async def _fetch_items_parallel(
    client: httpx.AsyncClient,
    ids: List[int],
    cache: TTLCache,
    semaphore: asyncio.Semaphore,
) -> List[Dict[str, Any]]:
    async def fetch_one(item_id: int) -> Optional[Dict[str, Any]]:
        async with semaphore:
            data = await cache.get_or_fetch(
                f"item:{item_id}",
                lambda: _safe_fetch_json(client, f"{FIREBASE_BASE_URL}/item/{item_id}.json"),
                ITEM_TTL,
            )

        if _is_error_response(data):
            return None
        if not isinstance(data, dict):
            return None
        if data.get("deleted") or data.get("dead"):
            return None
        return data

    results = await asyncio.gather(*(fetch_one(item_id) for item_id in ids), return_exceptions=True)
    items: List[Dict[str, Any]] = []
    for result in results:
        if isinstance(result, BaseException):
            continue
        if result is not None:
            items.append(cast(Dict[str, Any], result))
    return items


def _story_age_ok(story: Dict[str, Any], cutoff: int) -> bool:
    story_time = story.get("time")
    if not isinstance(story_time, int):
        return False
    return story_time >= cutoff


def _keyword_match_score(text: str, keywords: List[str]) -> float:
    lowered = text.lower()
    matches = 0
    for keyword in keywords:
        if keyword and keyword.lower() in lowered:
            matches += 1
    if not keywords:
        return 0.0
    return float(matches) / float(len(keywords))


def _aggregate_signals(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not items:
        return _empty_signals()

    signals = _empty_signals()
    marker_set = set()
    expert_set = set()
    trust_scores: Dict[str, float] = {}

    for item in items:
        item_signals = item.get("signals")
        if not isinstance(item_signals, dict):
            continue
        signals["practitioner_depth"]["score"] += float(
            item_signals.get("practitioner_depth", {}).get("score", 0.0)
        )
        marker_set.update(item_signals.get("practitioner_depth", {}).get("markers", []))
        signals["velocity"]["score"] += float(item_signals.get("velocity", {}).get("score", 0.0))
        signals["velocity"]["points_per_hour"] += float(
            item_signals.get("velocity", {}).get("points_per_hour", 0.0)
        )
        signals["reference_density"]["score"] += float(
            item_signals.get("reference_density", {}).get("score", 0.0)
        )
        signals["reference_density"]["link_count"] += int(
            item_signals.get("reference_density", {}).get("link_count", 0)
        )
        signals["thread_depth"]["score"] += float(
            item_signals.get("thread_depth", {}).get("score", 0.0)
        )
        signals["thread_depth"]["max_depth"] = max(
            int(signals["thread_depth"]["max_depth"]),
            int(item_signals.get("thread_depth", {}).get("max_depth", 0)),
        )
        signals["expert_involvement"]["score"] += float(
            item_signals.get("expert_involvement", {}).get("score", 0.0)
        )
        expert_set.update(item_signals.get("expert_involvement", {}).get("experts", []))
        trust_scores.update(item_signals.get("expert_involvement", {}).get("trust_scores", {}))

    count = float(len(items))
    signals["practitioner_depth"]["score"] /= count
    signals["practitioner_depth"]["markers"] = sorted(marker_set)
    signals["velocity"]["score"] /= count
    signals["velocity"]["points_per_hour"] /= count
    signals["reference_density"]["score"] /= count
    signals["thread_depth"]["score"] /= count
    signals["expert_involvement"]["score"] /= count
    signals["expert_involvement"]["experts"] = sorted(expert_set)
    signals["expert_involvement"]["trust_scores"] = trust_scores
    return signals


def _to_int_ids(values: Any) -> List[int]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, int)]


def _build_comment_depth_map(story_id: int, comments: List[Dict[str, Any]]) -> Dict[int, int]:
    depth_map: Dict[int, int] = {story_id: 0}
    comment_by_id: Dict[int, Dict[str, Any]] = {}
    for comment in comments:
        comment_id = comment.get("id")
        if isinstance(comment_id, int):
            comment_by_id[comment_id] = comment

    unresolved = set(comment_by_id.keys())
    progress = True
    while unresolved and progress:
        progress = False
        for comment_id in list(unresolved):
            comment = comment_by_id[comment_id]
            parent_id = comment.get("parent")
            if not isinstance(parent_id, int):
                depth_map[comment_id] = 1
                unresolved.remove(comment_id)
                progress = True
                continue
            parent_depth = depth_map.get(parent_id)
            if parent_depth is None:
                if parent_id not in comment_by_id:
                    parent_depth = 0
                else:
                    continue
            depth_map[comment_id] = int(parent_depth) + 1
            unresolved.remove(comment_id)
            progress = True

    for comment_id in unresolved:
        depth_map[comment_id] = 1
    return depth_map


async def _fetch_comment_subtree(
    client: httpx.AsyncClient,
    cache: TTLCache,
    semaphore: asyncio.Semaphore,
    item_id: int,
) -> List[Dict[str, Any]]:
    async with semaphore:
        item = await cache.get_or_fetch(
            f"item:{item_id}",
            lambda: _safe_fetch_json(client, f"{FIREBASE_BASE_URL}/item/{item_id}.json"),
            ITEM_TTL,
        )

    if _is_error_response(item) or not isinstance(item, dict):
        return []
    if item.get("deleted") or item.get("dead"):
        return []

    subtree: List[Dict[str, Any]] = []
    if item.get("type") == "comment":
        subtree.append(item)

    kid_ids = _to_int_ids(item.get("kids"))
    if not kid_ids:
        return subtree

    child_lists = await asyncio.gather(
        *(_fetch_comment_subtree(client, cache, semaphore, kid_id) for kid_id in kid_ids),
        return_exceptions=True,
    )
    for child_list in child_lists:
        if isinstance(child_list, BaseException):
            continue
        subtree.extend(cast(List[Dict[str, Any]], child_list))
    return subtree


@mcp.tool()
async def discover_stories(
    ctx: Context,
    keywords: str = "",
    min_score: int = 0,
    hours: int = 24,
    limit: int = 10,
    focus: str = "all",
) -> Dict[str, Any]:
    runtime = await _get_runtime(ctx)
    client = runtime["client"]
    cache = runtime["cache"]
    profile = runtime["profile"]
    trust_scores = runtime["trust_scores"]
    semaphore = runtime["semaphore"]

    profile_keywords = list(getattr(profile, "keywords", []))
    dynamic_keywords = [value.strip() for value in keywords.split(",") if value.strip()]
    all_keywords = dynamic_keywords or profile_keywords
    effective_min_score = max(min_score, int(getattr(profile, "min_score", 0)))
    effective_hours = hours if hours > 0 else int(getattr(profile, "time_hours", 24))
    cutoff = int(time.time()) - (effective_hours * 3600)
    experts = list(getattr(profile, "experts", []))

    top_ids = await cache.get_or_fetch(
        "topstories",
        lambda: _safe_fetch_json(client, f"{FIREBASE_BASE_URL}/topstories.json"),
        STORY_TTL,
    )
    if _is_error_response(top_ids):
        return _error_payload(
            str(top_ids.get("error", "Failed to fetch top stories")), top_ids.get("context")
        )
    if not isinstance(top_ids, list):
        return _error_payload("Failed to fetch top stories", {"source": "firebase"})

    id_list = [story_id for story_id in top_ids[: max(limit * 4, 20)] if isinstance(story_id, int)]
    stories = await _fetch_items_parallel(client, id_list, cache, semaphore)

    story_payloads: List[Dict[str, Any]] = []
    for story in stories:
        if story.get("type") != "story":
            continue
        score = story.get("score")
        if not isinstance(score, int) or score < effective_min_score:
            continue
        if not _story_age_ok(story, cutoff):
            continue

        title = str(story.get("title") or "")
        text = str(story.get("text") or "")
        full_text = f"{title} {text}".strip()
        keyword_score = _keyword_match_score(full_text, all_keywords)

        signal_context = {
            "now": int(time.time()),
            "experts": experts,
            "trust_scores": trust_scores,
            "thread_depth_map": {story.get("id"): 0},
        }
        signals = calculate_signals(story, signal_context)

        story_author = story.get("by")
        expert_boost = 0.0
        if isinstance(story_author, str) and story_author in experts:
            expert_boost += 0.25
        if isinstance(story_author, str):
            expert_boost += min(0.3, get_trust_score(story_author, trust_scores))

        ranking_score = calculate_quality_score(signals, getattr(profile, "weights", {}))
        ranking_score += keyword_score * 0.45
        ranking_score += expert_boost

        story_payload = dict(story)
        story_payload["signals"] = signals
        story_payload["ranking_score"] = ranking_score
        story_payload["focus"] = focus
        story_payloads.append(story_payload)

    story_payloads.sort(key=lambda item: float(item.get("ranking_score", 0.0)), reverse=True)
    story_payloads = story_payloads[:limit]
    return {
        "ok": True,
        "focus": focus,
        "signals": _aggregate_signals(story_payloads),
        "stories": story_payloads,
    }


@mcp.tool()
async def search(
    ctx: Context,
    query: str,
    min_score: int = 0,
    hours: int = 24,
    limit: int = 10,
    focus: str = "all",
) -> Dict[str, Any]:
    runtime = await _get_runtime(ctx)
    client = runtime["client"]
    profile = runtime["profile"]
    trust_scores = runtime["trust_scores"]

    effective_min_score = max(min_score, int(getattr(profile, "min_score", 0)))
    effective_hours = hours if hours > 0 else int(getattr(profile, "time_hours", 24))
    cutoff = int(time.time()) - (effective_hours * 3600)
    experts = list(getattr(profile, "experts", []))

    params = {
        "query": query,
        "tags": "story",
        "hitsPerPage": max(1, min(limit * 3, 100)),
        "numericFilters": f"created_at_i>{cutoff}",
    }
    payload = await _safe_fetch_json(client, ALGOLIA_URL, params=params)
    if _is_error_response(payload):
        return _error_payload(str(payload.get("error", "Search failed")), payload.get("context"))
    if not isinstance(payload, dict):
        return _error_payload("Search failed", {"source": "algolia"})

    hits = payload.get("hits")
    if not isinstance(hits, list):
        return _error_payload("Search failed", {"source": "algolia", "reason": "missing hits"})

    results: List[Dict[str, Any]] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        points = hit.get("points", 0)
        if isinstance(points, int) and points < effective_min_score:
            continue

        story_title = str(hit.get("story_title") or "")
        comment_text = str(hit.get("comment_text") or "")
        author = str(hit.get("author") or "")
        created_at = hit.get("created_at_i")
        created_at_i = int(created_at) if isinstance(created_at, int) else int(time.time())

        pseudo_item = {
            "id": int(hit.get("objectID") or 0),
            "type": "comment",
            "by": author,
            "text": comment_text,
            "time": created_at_i,
            "score": points if isinstance(points, int) else 0,
            "depth": 1,
            "title": story_title,
        }
        signal_context = {
            "now": int(time.time()),
            "experts": experts,
            "trust_scores": trust_scores,
            "comment_depth_map": {pseudo_item["id"]: 1},
        }
        signals = calculate_signals(pseudo_item, signal_context)

        ranking_score = calculate_quality_score(signals, getattr(profile, "weights", {}))
        if author in experts:
            ranking_score += 0.25
        ranking_score += min(0.3, get_trust_score(author, trust_scores))

        item = {
            "id": pseudo_item["id"],
            "story_id": hit.get("story_id"),
            "title": story_title,
            "by": author,
            "text": comment_text,
            "points": points,
            "created_at_i": created_at_i,
            "signals": signals,
            "ranking_score": ranking_score,
        }
        results.append(item)

    results.sort(key=lambda item: float(item.get("ranking_score", 0.0)), reverse=True)
    results = results[:limit]
    return {
        "ok": True,
        "focus": focus,
        "query": query,
        "signals": _aggregate_signals(results),
        "results": results,
    }


@mcp.tool()
async def find_experts(ctx: Context, topic: str, limit: int = 10) -> Dict[str, Any]:
    runtime = await _get_runtime(ctx)
    client = runtime["client"]
    profile = runtime["profile"]
    trust_scores = runtime["trust_scores"]
    experts = list(getattr(profile, "experts", []))

    seed_params = {
        "query": topic,
        "tags": "comment",
        "hitsPerPage": 100,
    }
    payload = await _safe_fetch_json(client, ALGOLIA_URL, params=seed_params)
    if _is_error_response(payload):
        return _error_payload(
            str(payload.get("error", "Failed to discover experts")), payload.get("context")
        )
    if not isinstance(payload, dict):
        return _error_payload("Failed to discover experts", {"source": "algolia"})

    seed_hits = payload.get("hits")
    if not isinstance(seed_hits, list):
        return _error_payload(
            "Failed to discover experts", {"source": "algolia", "reason": "missing hits"}
        )

    candidate_usernames: List[str] = []
    seen = set()
    for hit in seed_hits:
        if not isinstance(hit, dict):
            continue
        author = hit.get("author")
        if isinstance(author, str) and author and author not in seen:
            seen.add(author)
            candidate_usernames.append(author)

    async def fetch_author_hits(username: str) -> List[Dict[str, Any]]:
        params = {
            "query": topic,
            "tags": f"comment,author_{username}",
            "hitsPerPage": 100,
        }
        author_payload = await _safe_fetch_json(client, ALGOLIA_URL, params=params)
        if _is_error_response(author_payload) or not isinstance(author_payload, dict):
            return []
        hits = author_payload.get("hits")
        if not isinstance(hits, list):
            return []
        filtered: List[Dict[str, Any]] = []
        for hit in hits:
            if isinstance(hit, dict) and hit.get("author") == username:
                filtered.append(hit)
        return filtered

    author_hits_results = await asyncio.gather(
        *(fetch_author_hits(username) for username in candidate_usernames), return_exceptions=True
    )

    expert_rows: List[Dict[str, Any]] = []
    signal_items: List[Dict[str, Any]] = []
    now_ts = int(time.time())
    for username, author_hits_raw in zip(candidate_usernames, author_hits_results):
        if isinstance(author_hits_raw, BaseException):
            continue
        author_hits = cast(List[Dict[str, Any]], author_hits_raw)
        if not author_hits:
            continue

        practitioner_total = 0.0
        for hit in author_hits:
            points = hit.get("points", 0)
            created_at = hit.get("created_at_i")
            comment_text = str(hit.get("comment_text") or "")
            pseudo_item = {
                "id": int(hit.get("objectID") or 0),
                "type": "comment",
                "by": username,
                "text": comment_text,
                "time": int(created_at) if isinstance(created_at, int) else now_ts,
                "score": points if isinstance(points, int) else 0,
                "depth": 1,
            }
            signals = calculate_signals(
                pseudo_item,
                {
                    "now": now_ts,
                    "experts": experts,
                    "trust_scores": trust_scores,
                    "comment_depth_map": {pseudo_item["id"]: 1},
                },
            )
            practitioner_total += float(signals["practitioner_depth"]["score"])
            signal_item: Dict[str, Any] = dict(pseudo_item)
            signal_item["signals"] = signals
            signal_items.append(signal_item)

        comment_count = len(author_hits)
        practitioner_score = practitioner_total / float(comment_count)
        trust_score = get_trust_score(username, trust_scores)
        rank_score = (comment_count * 0.2) + (trust_score * 2.0) + practitioner_score
        if username in experts:
            rank_score += 0.25

        expert_rows.append(
            {
                "username": username,
                "trust_score": trust_score,
                "comment_count": comment_count,
                "practitioner_score": practitioner_score,
                "ranking_score": rank_score,
            }
        )

    expert_rows.sort(key=lambda item: float(item.get("ranking_score", 0.0)), reverse=True)
    top_experts = []
    for row in expert_rows[: max(1, limit)]:
        top_experts.append(
            {
                "username": row["username"],
                "trust_score": row["trust_score"],
                "comment_count": row["comment_count"],
                "practitioner_score": row["practitioner_score"],
            }
        )

    return {
        "ok": True,
        "topic": topic,
        "signals": _aggregate_signals(signal_items),
        "experts": top_experts,
    }


@mcp.tool()
async def expert_brief(
    ctx: Context, username: str, topic: str = "", limit: int = 10
) -> Dict[str, Any]:
    runtime = await _get_runtime(ctx)
    client = runtime["client"]
    profile = runtime["profile"]
    trust_scores = runtime["trust_scores"]
    experts = list(getattr(profile, "experts", []))

    user_payload = await _safe_fetch_json(client, f"{FIREBASE_BASE_URL}/user/{username}.json")
    if _is_error_response(user_payload):
        return _error_payload(
            str(user_payload.get("error", "Failed to fetch expert profile")),
            user_payload.get("context"),
        )
    profile_data = user_payload if isinstance(user_payload, dict) else {}

    params = {
        "query": topic or username,
        "tags": f"comment,author_{username}",
        "hitsPerPage": max(1, min(limit, 100)),
    }
    comments_payload = await _safe_fetch_json(client, ALGOLIA_URL, params=params)
    if _is_error_response(comments_payload):
        return _error_payload(
            str(comments_payload.get("error", "Failed to fetch expert activity")),
            comments_payload.get("context"),
        )
    if not isinstance(comments_payload, dict):
        return _error_payload("Failed to fetch expert activity", {"source": "algolia"})

    hits = comments_payload.get("hits")
    if not isinstance(hits, list):
        return _error_payload(
            "Failed to fetch expert activity", {"source": "algolia", "reason": "missing hits"}
        )

    recent_comments: List[Dict[str, Any]] = []
    signal_items: List[Dict[str, Any]] = []
    now_ts = int(time.time())
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        if hit.get("author") != username:
            continue

        created_at = hit.get("created_at_i")
        points = hit.get("points", 0)
        comment_item = {
            "id": int(hit.get("objectID") or 0),
            "type": "comment",
            "by": username,
            "text": str(hit.get("comment_text") or ""),
            "time": int(created_at) if isinstance(created_at, int) else now_ts,
            "score": points if isinstance(points, int) else 0,
            "depth": 1,
        }
        signals = calculate_signals(
            comment_item,
            {
                "now": now_ts,
                "experts": experts,
                "trust_scores": trust_scores,
                "comment_depth_map": {comment_item["id"]: 1},
            },
        )

        comment_payload = {
            "id": comment_item["id"],
            "story_id": hit.get("story_id"),
            "title": str(hit.get("story_title") or ""),
            "text": comment_item["text"],
            "points": comment_item["score"],
            "created_at_i": comment_item["time"],
            "signals": signals,
        }
        recent_comments.append(comment_payload)

        signal_item: Dict[str, Any] = dict(comment_item)
        signal_item["signals"] = signals
        signal_items.append(signal_item)

    return {
        "ok": True,
        "username": username,
        "trust_score": get_trust_score(username, trust_scores),
        "signals": _aggregate_signals(signal_items),
        "profile": profile_data,
        "recent_comments": recent_comments,
    }


@mcp.tool()
async def story_brief(ctx: Context, story_id: int, top_n: int = 10) -> Dict[str, Any]:
    runtime = await _get_runtime(ctx)
    client = runtime["client"]
    cache = runtime["cache"]
    profile = runtime["profile"]
    trust_scores = runtime["trust_scores"]
    semaphore = runtime["semaphore"]
    experts = list(getattr(profile, "experts", []))

    async with semaphore:
        story_payload = await cache.get_or_fetch(
            f"item:{story_id}",
            lambda: _safe_fetch_json(client, f"{FIREBASE_BASE_URL}/item/{story_id}.json"),
            ITEM_TTL,
        )
    if _is_error_response(story_payload):
        return _error_payload(
            str(story_payload.get("error", "Failed to fetch story")), story_payload.get("context")
        )
    if not isinstance(story_payload, dict) or story_payload.get("type") != "story":
        return _error_payload("Story not found", {"story_id": story_id})

    comment_ids = _to_int_ids(story_payload.get("kids"))
    comment_lists = await asyncio.gather(
        *(_fetch_comment_subtree(client, cache, semaphore, item_id) for item_id in comment_ids),
        return_exceptions=True,
    )

    comments: List[Dict[str, Any]] = []
    for result in comment_lists:
        if isinstance(result, BaseException):
            continue
        comments.extend(cast(List[Dict[str, Any]], result))

    depth_map = _build_comment_depth_map(story_id, comments)
    now_ts = int(time.time())

    ranked_comments: List[Dict[str, Any]] = []
    signal_items: List[Dict[str, Any]] = []
    for comment in comments:
        comment_id = comment.get("id")
        if not isinstance(comment_id, int):
            continue
        signal_context = {
            "now": now_ts,
            "experts": experts,
            "trust_scores": trust_scores,
            "comment_depth_map": depth_map,
            "thread_depth_map": depth_map,
        }
        signals = calculate_signals(comment, signal_context)
        author = str(comment.get("by") or "")
        rank_score = calculate_quality_score(signals, getattr(profile, "weights", {}))
        if author in experts:
            rank_score += 0.25
        rank_score += min(0.3, get_trust_score(author, trust_scores))

        comment_payload = dict(comment)
        comment_payload["depth"] = depth_map.get(comment_id, 1)
        comment_payload["signals"] = signals
        comment_payload["ranking_score"] = rank_score
        ranked_comments.append(comment_payload)

        signal_item = dict(comment)
        signal_item["signals"] = signals
        signal_items.append(signal_item)

    ranked_comments.sort(key=lambda item: float(item.get("ranking_score", 0.0)), reverse=True)
    top_comments = ranked_comments[: max(1, top_n)]
    expert_highlights = [comment for comment in ranked_comments if comment.get("by") in experts]
    expert_highlights = expert_highlights[: max(1, min(top_n, 5))]

    story_with_signals = dict(story_payload)
    story_with_signals["signals"] = calculate_signals(
        story_payload,
        {
            "now": now_ts,
            "experts": experts,
            "trust_scores": trust_scores,
            "thread_depth_map": depth_map,
        },
    )

    all_signal_items = [story_with_signals] + signal_items
    return {
        "ok": True,
        "story": story_with_signals,
        "top_comments": top_comments,
        "expert_highlights": expert_highlights,
        "total_comments": len(ranked_comments),
        "signals": _aggregate_signals(all_signal_items),
    }


@mcp.tool()
async def thread_analysis(
    ctx: Context,
    story_id: int,
    expert_only: bool = False,
    max_depth: int = 3,
) -> Dict[str, Any]:
    runtime = await _get_runtime(ctx)
    client = runtime["client"]
    cache = runtime["cache"]
    profile = runtime["profile"]
    trust_scores = runtime["trust_scores"]
    semaphore = runtime["semaphore"]
    experts = list(getattr(profile, "experts", []))

    async with semaphore:
        story_payload = await cache.get_or_fetch(
            f"item:{story_id}",
            lambda: _safe_fetch_json(client, f"{FIREBASE_BASE_URL}/item/{story_id}.json"),
            ITEM_TTL,
        )
    if _is_error_response(story_payload):
        return _error_payload(
            str(story_payload.get("error", "Failed to fetch thread")), story_payload.get("context")
        )
    if not isinstance(story_payload, dict) or story_payload.get("type") != "story":
        return _error_payload("Story not found", {"story_id": story_id})

    root_ids = _to_int_ids(story_payload.get("kids"))
    comment_lists = await asyncio.gather(
        *(_fetch_comment_subtree(client, cache, semaphore, item_id) for item_id in root_ids),
        return_exceptions=True,
    )

    comments: List[Dict[str, Any]] = []
    for result in comment_lists:
        if isinstance(result, BaseException):
            continue
        comments.extend(cast(List[Dict[str, Any]], result))

    depth_map = _build_comment_depth_map(story_id, comments)
    now_ts = int(time.time())
    max_depth = max(1, max_depth)

    comment_nodes: Dict[int, Dict[str, Any]] = {}
    signal_items: List[Dict[str, Any]] = []
    for comment in comments:
        comment_id = comment.get("id")
        if not isinstance(comment_id, int):
            continue
        author = str(comment.get("by") or "")
        depth = int(depth_map.get(comment_id, 1))
        if depth > max_depth:
            continue
        if expert_only and author not in experts:
            continue

        signals = calculate_signals(
            comment,
            {
                "now": now_ts,
                "experts": experts,
                "trust_scores": trust_scores,
                "comment_depth_map": depth_map,
                "thread_depth_map": depth_map,
            },
        )
        quality_score = calculate_quality_score(signals, getattr(profile, "weights", {}))
        quality_score += min(0.3, get_trust_score(author, trust_scores))
        if author in experts:
            quality_score += 0.25

        node = {
            "id": comment_id,
            "parent": comment.get("parent"),
            "by": author,
            "text": str(comment.get("text") or ""),
            "time": comment.get("time"),
            "depth": depth,
            "quality_score": quality_score,
            "trust_score": get_trust_score(author, trust_scores),
            "signals": signals,
            "children": [],
        }
        comment_nodes[comment_id] = node

        signal_item = dict(comment)
        signal_item["signals"] = signals
        signal_items.append(signal_item)

    roots: List[Dict[str, Any]] = []
    for comment_id, node in comment_nodes.items():
        parent_id = node.get("parent")
        if isinstance(parent_id, int) and parent_id in comment_nodes:
            parent_node = comment_nodes[parent_id]
            parent_node["children"].append(node)
        else:
            roots.append(node)

    def sort_tree(nodes: List[Dict[str, Any]]) -> None:
        nodes.sort(key=lambda item: float(item.get("quality_score", 0.0)), reverse=True)
        for child in nodes:
            child_nodes = child.get("children")
            if isinstance(child_nodes, list):
                sort_tree(cast(List[Dict[str, Any]], child_nodes))

    sort_tree(roots)

    story_with_signals = dict(story_payload)
    story_with_signals["signals"] = calculate_signals(
        story_payload,
        {
            "now": now_ts,
            "experts": experts,
            "trust_scores": trust_scores,
            "thread_depth_map": depth_map,
        },
    )

    all_signal_items = [story_with_signals] + signal_items
    return {
        "ok": True,
        "story": story_with_signals,
        "expert_only": expert_only,
        "max_depth": max_depth,
        "comment_count": len(comment_nodes),
        "thread": roots,
        "signals": _aggregate_signals(all_signal_items),
    }


@mcp.resource("hn://config")
async def get_config(ctx: Context) -> str:
    runtime = await _get_runtime(ctx)
    profile = runtime["profile"]
    return json.dumps(
        {
            "keywords": list(getattr(profile, "keywords", [])),
            "experts": list(getattr(profile, "experts", [])),
            "min_score": int(getattr(profile, "min_score", 0)),
            "time_hours": int(getattr(profile, "time_hours", 24)),
            "weights": dict(getattr(profile, "weights", {})),
        }
    )


@mcp.resource("hn://trust")
async def get_trust(ctx: Context) -> str:
    runtime = await _get_runtime(ctx)
    trust_scores = runtime["trust_scores"]
    if not isinstance(trust_scores, dict):
        trust_scores = {}
    return json.dumps(trust_scores)


async def _reset_for_tests() -> None:
    async with _RUNTIME_LOCK:
        client = _RUNTIME_FALLBACK.get("client")
        if isinstance(client, httpx.AsyncClient):
            await client.aclose()
        _RUNTIME_FALLBACK.clear()


def main() -> None:
    mcp.run()
