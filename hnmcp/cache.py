import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

STORY_TTL = 300
ITEM_TTL = 600
USER_TTL = 1800


class TTLCache:
    def __init__(self) -> None:
        self._data: Dict[str, Tuple[Any, float]] = {}
        self._data_lock = asyncio.Lock()
        self._locks: Dict[str, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        now = time.time()
        async with self._data_lock:
            entry = self._data.get(key)
            if entry is None:
                return None

            value, expires_at = entry
            if expires_at <= now:
                del self._data[key]
                return None

            return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        expires_at = time.time() + ttl
        async with self._data_lock:
            self._data[key] = (value, expires_at)

    async def get_or_fetch(self, key: str, fetcher: Callable[[], Awaitable[Any]], ttl: int) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached

        key_lock = await self._get_key_lock(key)
        async with key_lock:
            cached = await self.get(key)
            if cached is not None:
                return cached

            value = await fetcher()
            await self.set(key, value, ttl)
            return value

    def clear(self) -> None:
        self._data.clear()
        self._locks.clear()

    async def _get_key_lock(self, key: str) -> asyncio.Lock:
        async with self._locks_guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock
