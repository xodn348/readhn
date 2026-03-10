from datetime import timedelta

import asyncio
import pytest

from hnmcp.cache import ITEM_TTL, STORY_TTL, USER_TTL, TTLCache


@pytest.mark.asyncio
async def test_cache_set_get() -> None:
    cache = TTLCache()

    await cache.set("story:1", {"title": "hello"}, ttl=60)

    value = await cache.get("story:1")
    assert value == {"title": "hello"}


@pytest.mark.asyncio
async def test_cache_ttl_expiry(time_machine) -> None:
    cache = TTLCache()
    time_machine.move_to("2026-01-01 00:00:00")

    await cache.set("story:2", "value", ttl=300)
    assert await cache.get("story:2") == "value"

    time_machine.shift(timedelta(seconds=301))
    assert await cache.get("story:2") is None


@pytest.mark.asyncio
async def test_cache_different_ttls(time_machine) -> None:
    cache = TTLCache()
    time_machine.move_to("2026-01-01 00:00:00")

    await cache.set("story:3", "story", ttl=STORY_TTL)
    await cache.set("item:3", "item", ttl=ITEM_TTL)
    await cache.set("user:3", "user", ttl=USER_TTL)

    time_machine.shift(timedelta(seconds=301))
    assert await cache.get("story:3") is None
    assert await cache.get("item:3") == "item"
    assert await cache.get("user:3") == "user"

    time_machine.shift(timedelta(seconds=300))
    assert await cache.get("item:3") is None
    assert await cache.get("user:3") == "user"

    time_machine.shift(timedelta(seconds=1200))
    assert await cache.get("user:3") is None


@pytest.mark.asyncio
async def test_cache_async_safe() -> None:
    cache = TTLCache()

    async def writer(i: int) -> None:
        await cache.set(f"k:{i}", i, ttl=60)

    _ = await asyncio.gather(*(writer(i) for i in range(200)))

    values = await asyncio.gather(*(cache.get(f"k:{i}") for i in range(200)))
    assert values == list(range(200))


@pytest.mark.asyncio
async def test_cache_clear() -> None:
    cache = TTLCache()

    await cache.set("story:4", "a", ttl=60)
    await cache.set("story:5", "b", ttl=60)

    cache.clear()

    assert await cache.get("story:4") is None
    assert await cache.get("story:5") is None


@pytest.mark.asyncio
async def test_cache_stampede_protection() -> None:
    cache = TTLCache()
    calls = 0

    async def fetcher() -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return "payload"

    results = await asyncio.gather(
        *(cache.get_or_fetch("story:stampede", fetcher, ttl=60) for _ in range(5))
    )

    assert results == ["payload"] * 5
    assert calls == 1
