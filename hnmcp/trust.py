import json

from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
from typing import cast


MAX_TRUST_USERS = 500
TRUST_ALPHA = 0.15
MAX_ITERATIONS = 50
_SEED_SELF_WEIGHT = 4.0

_TRUST_CACHE: dict[str, float] = {}


def build_reply_graph(comments: Sequence[Mapping[str, object]]) -> dict[str, dict[str, int]]:
    id_to_author: dict[int, str] = {}
    graph: dict[str, dict[str, int]] = {}

    for comment in comments:
        comment_id = comment.get("id")
        author = comment.get("by")
        if isinstance(comment_id, int) and isinstance(author, str) and author:
            id_to_author[comment_id] = author
            if author not in graph:
                graph[author] = {}

    for comment in comments:
        author = comment.get("by")
        parent_id = comment.get("parent")
        if not isinstance(author, str) or not author:
            continue
        if not isinstance(parent_id, int):
            continue

        parent_author = id_to_author.get(parent_id)
        if parent_author is None or parent_author == author:
            continue

        if author not in graph:
            graph[author] = {}
        graph[parent_author][author] = graph[parent_author].get(author, 0) + 1

    return graph


def _normalize_graph(
    reply_graph: dict[str, dict[str, int]], seed_experts: list[str]
) -> tuple[list[str], dict[str, dict[str, float]], dict[str, float]]:
    users: set[str] = set(seed_experts)
    for source, targets in reply_graph.items():
        users.add(source)
        for target in targets:
            users.add(target)

    ordered_users = sorted(users)
    if len(ordered_users) > MAX_TRUST_USERS:
        seed_set = set(seed_experts)
        seeded = [user for user in ordered_users if user in seed_set]
        others = [user for user in ordered_users if user not in seed_set]
        ordered_users = (seeded + others)[:MAX_TRUST_USERS]

    allowed = set(ordered_users)
    seed_set = set(seed_experts)
    normalized: dict[str, dict[str, float]] = {}
    for source in ordered_users:
        raw_targets = reply_graph.get(source, {})
        filtered = {
            target: float(weight)
            for target, weight in raw_targets.items()
            if target in allowed and weight > 0
        }
        if source in seed_set:
            filtered[source] = filtered.get(source, 0.0) + _SEED_SELF_WEIGHT

        total = sum(filtered.values())
        if total <= 0:
            normalized[source] = {}
            continue

        normalized[source] = {target: weight / total for target, weight in filtered.items()}

    valid_seeds = [seed for seed in seed_experts if seed in allowed]
    if valid_seeds:
        pretrust = {user: 0.0 for user in ordered_users}
        seed_weight = 1.0 / float(len(valid_seeds))
        for seed in valid_seeds:
            pretrust[seed] = seed_weight
    else:
        uniform_weight = 1.0 / float(len(ordered_users)) if ordered_users else 0.0
        pretrust = {user: uniform_weight for user in ordered_users}

    return ordered_users, normalized, pretrust


def compute_eigentrust(
    reply_graph: dict[str, dict[str, int]],
    seed_experts: list[str],
    alpha: float = TRUST_ALPHA,
    max_iter: int = MAX_ITERATIONS,
    epsilon: float = 1e-4,
) -> dict[str, float]:
    users, normalized_graph, pretrust = _normalize_graph(reply_graph, seed_experts)
    if not users:
        return {}

    trust_scores = dict(pretrust)
    for _ in range(max_iter):
        propagated: dict[str, float] = {user: 0.0 for user in users}
        for source in users:
            source_score = trust_scores[source]
            source_edges = normalized_graph[source]
            if not source_edges:
                for target in users:
                    propagated[target] += source_score * pretrust[target]
                continue

            for target, edge_weight in source_edges.items():
                propagated[target] += source_score * edge_weight

        updated: dict[str, float] = {}
        for user in users:
            updated[user] = (1.0 - alpha) * propagated[user] + alpha * pretrust[user]

        delta = sum(abs(updated[user] - trust_scores[user]) for user in users)
        trust_scores = updated
        if delta < epsilon:
            break

    total = sum(trust_scores.values())
    if total > 0:
        trust_scores = {user: score / total for user, score in trust_scores.items()}

    _TRUST_CACHE.clear()
    _TRUST_CACHE.update(trust_scores)
    return trust_scores


def is_trusted(username: str, trust_scores: dict[str, float], threshold: float = 0.3) -> bool:
    return get_trust_score(username, trust_scores) >= threshold


def get_trust_score(username: str, trust_scores: dict[str, float]) -> float:
    value = trust_scores.get(username, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def save_trust_cache(trust_scores: dict[str, float], path: str) -> None:
    cache_path = Path(path).expanduser()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {user: float(score) for user, score in trust_scores.items()}
    _ = cache_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def load_trust_cache(path: str):
    cache_path = Path(path).expanduser()
    if not cache_path.exists():
        return None

    try:
        raw_obj = cast(object, json.loads(cache_path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(raw_obj, dict):
        return None

    raw_dict = cast(dict[object, object], raw_obj)
    loaded: dict[str, float] = {}
    for user, score in raw_dict.items():
        if isinstance(user, str) and isinstance(score, (int, float, str)):
            try:
                loaded[user] = float(score)
            except (TypeError, ValueError):
                continue

    _TRUST_CACHE.clear()
    _TRUST_CACHE.update(loaded)
    return loaded
