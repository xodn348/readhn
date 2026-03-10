"""Embeddings-based semantic search and similarity detection."""

import asyncio
import importlib
import math
from typing import Coroutine, Optional, Protocol, TypeVar

from hnmcp.cache import ITEM_TTL, TTLCache

_INSTALL_HINT = "Install with: pip install hnmcp[embeddings]"
_MODEL_NAME = "all-MiniLM-L6-v2"

T = TypeVar("T")


class _EncoderModel(Protocol):
    def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]: ...


_model: Optional[_EncoderModel] = None
_TEXT_EMBED_CACHE = TTLCache()


def _run_sync(coro: Coroutine[object, object, T]) -> T:
    return asyncio.run(coro)


def _get_model() -> _EncoderModel:
    global _model
    if _model is not None:
        return _model

    try:
        module = importlib.import_module("sentence_transformers")
    except ImportError as exc:
        raise ImportError(_INSTALL_HINT) from exc

    model_cls = getattr(module, "SentenceTransformer")
    model = model_cls(_MODEL_NAME)
    _model = model
    return model


def embed_text(text: str) -> list[float]:
    cache_key = "embed:text:" + text
    cached = _run_sync(_TEXT_EMBED_CACHE.get(cache_key))
    if cached is not None:
        return cached

    model = _get_model()
    vector = model.encode([text], normalize_embeddings=True)[0]
    as_list = [float(v) for v in vector]
    _run_sync(_TEXT_EMBED_CACHE.set(cache_key, as_list, ITEM_TTL))
    return as_list


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(v * v for v in left))
    right_norm = math.sqrt(sum(v * v for v in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


class EmbeddingStore:
    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}
        self._store_cache = TTLCache()

    def add(self, item_id: str, text: str) -> None:
        vector = embed_text(text)
        self._vectors[item_id] = vector
        _run_sync(self._store_cache.set("item:" + item_id, vector, ITEM_TTL))

    def find_similar(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        if top_k <= 0 or not self._vectors:
            return []

        query_vector = embed_text(query)
        scored: list[tuple[str, float]] = []
        for item_id, vector in self._vectors.items():
            score = _cosine_similarity(query_vector, vector)
            scored.append((item_id, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        self._vectors.clear()
        self._store_cache.clear()
