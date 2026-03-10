from pathlib import Path
from typing import TypedDict

from _pytest.monkeypatch import MonkeyPatch

from hnmcp.trust import (
    MAX_ITERATIONS,
    MAX_TRUST_USERS,
    TRUST_ALPHA,
    build_reply_graph,
    compute_eigentrust,
    get_trust_score,
    is_trusted,
    load_trust_cache,
    save_trust_cache,
)


class SampleTrustGraph(TypedDict):
    users: list[str]
    seed_experts: list[str]
    edges: dict[str, list[str]]
    expected_trust_scores: dict[str, float]
    description: str


def _to_weighted_graph(edges: dict[str, list[str]]) -> dict[str, dict[str, int]]:
    return {user: {target: 1 for target in targets} for user, targets in edges.items()}


def test_eigentrust_basic(sample_trust_graph: SampleTrustGraph) -> None:
    reply_graph = _to_weighted_graph(sample_trust_graph["edges"])
    trust_scores = compute_eigentrust(reply_graph, sample_trust_graph["seed_experts"])

    expected = sample_trust_graph["expected_trust_scores"]
    assert trust_scores["A"] == trust_scores["B"]
    assert trust_scores["A"] > trust_scores["C"] > trust_scores["D"] > trust_scores["E"]
    assert abs(trust_scores["A"] - expected["A"]) < 0.06
    assert abs(trust_scores["B"] - expected["B"]) < 0.06
    assert abs(trust_scores["C"] - expected["C"]) < 0.06


def test_eigentrust_seed_highest(sample_trust_graph: SampleTrustGraph) -> None:
    reply_graph = _to_weighted_graph(sample_trust_graph["edges"])
    trust_scores = compute_eigentrust(reply_graph, sample_trust_graph["seed_experts"])

    top_seed_score = min(trust_scores[seed] for seed in sample_trust_graph["seed_experts"])
    non_seed_scores = [
        score
        for user, score in trust_scores.items()
        if user not in sample_trust_graph["seed_experts"]
    ]
    assert non_seed_scores
    assert top_seed_score > max(non_seed_scores)


def test_eigentrust_propagation() -> None:
    comments = [
        {"id": 1, "by": "seed", "parent": 0},
        {"id": 2, "by": "ally", "parent": 1},
        {"id": 3, "by": "ally", "parent": 1},
        {"id": 4, "by": "random", "parent": 0},
    ]
    reply_graph = build_reply_graph(comments)

    trust_scores = compute_eigentrust(reply_graph, ["seed"])
    assert trust_scores["ally"] > trust_scores["random"]


def test_eigentrust_single_seed() -> None:
    reply_graph: dict[str, dict[str, int]] = {
        "seed": {"user1": 2, "user2": 1},
        "user1": {"user3": 1},
        "user2": {},
        "user3": {},
    }

    trust_scores = compute_eigentrust(reply_graph, ["seed"])

    assert trust_scores["seed"] > trust_scores["user1"]
    assert trust_scores["user1"] > trust_scores["user3"]
    assert sum(trust_scores.values()) > 0.99


def test_eigentrust_no_interactions() -> None:
    reply_graph: dict[str, dict[str, int]] = {"A": {}, "B": {}, "C": {}}
    trust_scores = compute_eigentrust(reply_graph, ["A", "B"])

    assert trust_scores["A"] == 0.5
    assert trust_scores["B"] == 0.5
    assert trust_scores["C"] == 0.0


def test_eigentrust_convergence(sample_trust_graph: SampleTrustGraph) -> None:
    reply_graph = _to_weighted_graph(sample_trust_graph["edges"])

    score_50 = compute_eigentrust(
        reply_graph,
        sample_trust_graph["seed_experts"],
        alpha=TRUST_ALPHA,
        max_iter=MAX_ITERATIONS,
        epsilon=1e-8,
    )
    score_200 = compute_eigentrust(
        reply_graph,
        sample_trust_graph["seed_experts"],
        alpha=TRUST_ALPHA,
        max_iter=200,
        epsilon=1e-10,
    )

    for user in score_50:
        assert abs(score_50[user] - score_200[user]) < 1e-3


def test_eigentrust_max_users_cap() -> None:
    reply_graph: dict[str, dict[str, int]] = {}
    for idx in range(600):
        user = f"u{idx:03d}"
        target = f"u{idx + 1:03d}" if idx + 1 < 600 else None
        if target is None:
            reply_graph[user] = {}
        else:
            reply_graph[user] = {target: 1}

    trust_scores = compute_eigentrust(reply_graph, ["u000"])

    assert len(trust_scores) == MAX_TRUST_USERS
    assert "u000" in trust_scores


def test_trust_cache_persistence(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cache_path = "~/.hnmcp/trust_cache.json"
    trust_scores = {"seed": 0.8, "ally": 0.2}

    save_trust_cache(trust_scores, cache_path)

    expanded = Path(cache_path).expanduser()
    assert expanded.exists()
    assert load_trust_cache(cache_path) == trust_scores


def test_trust_cache_load(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cache_path = Path("~/.hnmcp/trust_cache.json").expanduser()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    _ = cache_path.write_text('{"seed": 0.7, "peer": 0.3}', encoding="utf-8")

    loaded = load_trust_cache(str(cache_path))
    assert loaded == {"seed": 0.7, "peer": 0.3}


def test_is_trusted_expert() -> None:
    trust_scores = {"seed": 0.9, "high": 0.35, "low": 0.05}

    assert is_trusted("seed", trust_scores)
    assert is_trusted("high", trust_scores)
    assert not is_trusted("low", trust_scores)
    assert get_trust_score("unknown", trust_scores) == 0.0


def test_build_reply_graph_edge_cases() -> None:
    comments = [
        {"id": 1, "by": "alice", "parent": 0},
        {"id": 2, "by": "", "parent": 1},
        {"id": 3, "by": 123, "parent": 1},
        {"id": 4, "by": "bob", "parent": "invalid"},
        {"id": 5, "by": "alice", "parent": 1},
        {"id": 6, "by": "charlie", "parent": 1},
    ]

    graph = build_reply_graph(comments)

    assert "alice" in graph
    assert "charlie" in graph
    assert "alice" not in graph["alice"]


def test_get_trust_score_invalid_types() -> None:
    trust_scores = {"user1": 0.5, "user2": "invalid", "user3": None}

    assert get_trust_score("user1", trust_scores) == 0.5
    assert get_trust_score("user2", trust_scores) == 0.0
    assert get_trust_score("user3", trust_scores) == 0.0


def test_load_trust_cache_missing_file(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nonexistent.json"
    assert load_trust_cache(str(nonexistent)) is None


def test_load_trust_cache_invalid_json(tmp_path: Path) -> None:
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("not valid json", encoding="utf-8")
    assert load_trust_cache(str(invalid_file)) is None


def test_load_trust_cache_invalid_structure(tmp_path: Path) -> None:
    invalid_structure = tmp_path / "invalid_structure.json"
    invalid_structure.write_text('["not", "a", "dict"]', encoding="utf-8")
    assert load_trust_cache(str(invalid_structure)) is None
