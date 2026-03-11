import builtins
import importlib
import math
import sys
from pathlib import Path
from types import ModuleType
from typing import Mapping, Optional, Sequence, cast

import pytest


def _reload_embeddings_module() -> ModuleType:
    sys.modules.pop("hnmcp.embeddings", None)
    module = importlib.import_module("hnmcp.embeddings")
    return cast(ModuleType, module)


def test_import_without_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals_: Optional[Mapping[str, object]] = None,
        locals_: Optional[Mapping[str, object]] = None,
        fromlist: Optional[Sequence[str]] = None,
        level: int = 0,
    ) -> object:
        if name == "sentence_transformers":
            raise AssertionError("sentence_transformers imported at module import time")
        return real_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    module = _reload_embeddings_module()
    assert hasattr(module, "EmbeddingStore")


def test_embed_text(monkeypatch: pytest.MonkeyPatch) -> None:
    embeddings = _reload_embeddings_module()

    class FakeModel:
        def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
            assert texts == ["hello world"]
            assert normalize_embeddings is True
            return [[0.25, 0.75]]

    monkeypatch.setattr(embeddings, "_get_model", lambda: FakeModel())

    assert embeddings.embed_text("hello world") == [0.25, 0.75]


def test_find_similar(monkeypatch: pytest.MonkeyPatch) -> None:
    embeddings = _reload_embeddings_module()

    vectors: dict[str, list[float]] = {
        "rust async io": [1.0, 0.0],
        "python data science": [0.0, 1.0],
        "rust tokio tutorial": [0.95, 0.05],
        "rust concurrency": [0.9, 0.1],
    }

    monkeypatch.setattr(embeddings, "embed_text", lambda text: vectors[text])

    store = embeddings.EmbeddingStore()
    store.add("a", "rust async io")
    store.add("b", "python data science")
    store.add("c", "rust tokio tutorial")

    results = store.find_similar("rust concurrency", top_k=2)

    assert len(results) == 2
    assert results[0][0] == "c"
    assert results[1][0] == "a"
    assert math.isclose(results[0][1], 0.9983141698791174)


def test_session_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    embeddings = _reload_embeddings_module()
    monkeypatch.setattr(
        embeddings, "embed_text", lambda text: [1.0, 0.0] if text == "a" else [0.0, 1.0]
    )

    before = {p.name for p in tmp_path.iterdir()}

    first_store = embeddings.EmbeddingStore()
    first_store.add("x", "a")
    assert first_store.find_similar("a") == [("x", 1.0)]

    second_store = embeddings.EmbeddingStore()
    assert second_store.find_similar("a") == []

    after = {p.name for p in tmp_path.iterdir()}
    assert before == after


def test_graceful_degradation(monkeypatch: pytest.MonkeyPatch) -> None:
    embeddings = _reload_embeddings_module()

    original_import_module = importlib.import_module

    def fail_sentence_transformers(name: str, package: Optional[str] = None) -> object:
        if name == "sentence_transformers":
            raise ImportError("missing optional dependency")
        return original_import_module(name, package)

    monkeypatch.setattr(embeddings.importlib, "import_module", fail_sentence_transformers)
    monkeypatch.setattr(embeddings, "_model", None)

    with pytest.raises(ImportError, match="Install with: pip install hnmcp\\[embeddings\\]"):
        embeddings.embed_text("hello")

    store = embeddings.EmbeddingStore()
    with pytest.raises(ImportError, match="Install with: pip install hnmcp\\[embeddings\\]"):
        store.add("x", "hello")


def test_cosine_similarity_edge_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    embeddings = _reload_embeddings_module()

    # Empty vectors
    assert embeddings._cosine_similarity([], [1.0]) == 0.0
    assert embeddings._cosine_similarity([1.0], []) == 0.0

    # Different lengths
    assert embeddings._cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    # Zero norm vectors
    assert embeddings._cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
    assert embeddings._cosine_similarity([1.0, 2.0], [0.0, 0.0]) == 0.0


def test_embedding_store_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    embeddings = _reload_embeddings_module()
    monkeypatch.setattr(embeddings, "embed_text", lambda text: [1.0, 0.0])

    store = embeddings.EmbeddingStore()
    store.add("x", "test")
    assert len(store.find_similar("test")) == 1

    store.clear()
    assert len(store.find_similar("test")) == 0


def test_embed_text_caching(monkeypatch: pytest.MonkeyPatch) -> None:
    embeddings = _reload_embeddings_module()

    call_count = 0

    class FakeModel:
        def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            return [[0.5, 0.5]]

    monkeypatch.setattr(embeddings, "_get_model", lambda: FakeModel())

    result1 = embeddings.embed_text("same text")
    result2 = embeddings.embed_text("same text")

    assert result1 == result2
    assert call_count == 1


def test_get_model_uses_cached_model() -> None:
    embeddings = _reload_embeddings_module()

    class FakeModel:
        def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
            return [[1.0]]

    embeddings._model = FakeModel()
    assert embeddings._get_model() is embeddings._model


def test_get_model_loads_sentence_transformer(monkeypatch: pytest.MonkeyPatch) -> None:
    embeddings = _reload_embeddings_module()

    class FakeModel:
        def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
            return [[1.0]]

    class FakeModule:
        def __init__(self) -> None:
            self.SentenceTransformer = lambda _name: FakeModel()

    monkeypatch.setattr(embeddings.importlib, "import_module", lambda _name: FakeModule())
    embeddings._model = None

    loaded = embeddings._get_model()

    assert isinstance(loaded, FakeModel)
