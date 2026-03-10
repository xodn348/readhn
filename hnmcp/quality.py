import math
import re
from collections.abc import Mapping
from typing import Optional, TypedDict


class PractitionerDepthSignal(TypedDict):
    score: float
    markers: list[str]


class VelocitySignal(TypedDict):
    score: float
    points_per_hour: float


class ReferenceDensitySignal(TypedDict):
    score: float
    link_count: int


class ThreadDepthSignal(TypedDict):
    score: float
    max_depth: int


class ExpertInvolvementSignal(TypedDict):
    score: float
    experts: list[str]
    trust_scores: dict[str, float]


class Signals(TypedDict):
    practitioner_depth: PractitionerDepthSignal
    velocity: VelocitySignal
    reference_density: ReferenceDensitySignal
    thread_depth: ThreadDepthSignal
    expert_involvement: ExpertInvolvementSignal


PRACTITIONER_MARKERS = [
    "i built",
    "we used",
    "in production",
    "our team",
    "i tried",
    "we deployed",
    "at scale",
    "my experience",
]

HEDGING_MARKERS = ["fwiw", "ymmv", "imho", "in my opinion", "depends on"]

DEFAULT_WEIGHTS = {
    "practitioner_depth": 0.30,
    "velocity": 0.15,
    "reference_density": 0.15,
    "thread_depth": 0.20,
    "expert_involvement": 0.20,
}

URL_PATTERN = re.compile(r"https?://[^\s<>()\[\]{}\"']+")
CODE_BLOCK_PATTERN = re.compile(r"<pre>|```", re.IGNORECASE)
METRIC_PATTERN = re.compile(r"\d+%|\d+x|\$\d+|v\d+\.\d+", re.IGNORECASE)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _as_int(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) else 0


def detect_practitioner_markers(text: str) -> list[str]:
    normalized = text.lower()
    return [marker for marker in PRACTITIONER_MARKERS if marker in normalized]


def count_references(text: str) -> int:
    return len(URL_PATTERN.findall(text))


def calculate_velocity(score: int, age_seconds: int) -> float:
    effective_age = max(60, age_seconds)
    return float(max(0, score)) / (effective_age / 3600.0)


def _extract_thread_depth(item: Mapping[str, object], context: Mapping[str, object]) -> int:
    item_id = item.get("id")
    raw_depth_map = context.get("thread_depth_map") or context.get("comment_depth_map")
    if isinstance(raw_depth_map, Mapping) and item_id in raw_depth_map:
        return _as_int(raw_depth_map[item_id])
    return _as_int(item.get("depth"))


def _extract_experts(context: Mapping[str, object]) -> list[str]:
    raw_experts = context.get("experts")
    if not isinstance(raw_experts, list):
        return []
    return [name for name in raw_experts if isinstance(name, str)]


def _extract_trust_scores(context: Mapping[str, object]) -> dict[str, float]:
    raw_trust_scores = context.get("trust_scores")
    if not isinstance(raw_trust_scores, Mapping):
        return {}
    extracted: dict[str, float] = {}
    for name, score in raw_trust_scores.items():
        if isinstance(name, str) and isinstance(score, (int, float)):
            extracted[name] = _clamp(float(score))
    return extracted


def _expert_signal(
    author: str, experts: list[str], trust_scores: dict[str, float]
) -> ExpertInvolvementSignal:
    matched_experts: list[str] = []
    if author in experts:
        matched_experts.append(author)

    trust_value = _clamp(float(trust_scores.get(author, 0.0)))
    score = max(0.2, trust_value) if matched_experts else 0.0
    selected_trust = {name: _clamp(float(trust_scores.get(name, 0.0))) for name in matched_experts}

    return {
        "score": _clamp(score),
        "experts": matched_experts,
        "trust_scores": selected_trust,
    }


def calculate_signals(item: Mapping[str, object], context: Mapping[str, object]) -> Signals:
    text_raw = item.get("text")
    text = text_raw if isinstance(text_raw, str) else ""
    item_type_raw = item.get("type")
    item_type = item_type_raw if isinstance(item_type_raw, str) else "comment"
    author_raw = item.get("by")
    author = author_raw if isinstance(author_raw, str) else ""
    experts = _extract_experts(context)
    trust_scores = _extract_trust_scores(context)

    link_count = count_references(text)
    reference_score = _clamp(link_count / 3.0)

    depth = _extract_thread_depth(item, context)
    thread_depth_score = _clamp(depth / 4.0)

    practitioner_markers = detect_practitioner_markers(text)
    has_code_block = bool(CODE_BLOCK_PATTERN.search(text))
    has_metric = bool(METRIC_PATTERN.search(text))
    lower_text = text.lower()
    hedging_hits = [marker for marker in HEDGING_MARKERS if marker in lower_text]

    practitioner_score = 0.0
    velocity_points_per_hour = 0.0
    velocity_score = 0.0

    if item_type == "story":
        raw_score = _as_int(item.get("score"))
        story_points = math.log1p(max(0, raw_score)) / math.log1p(500.0)
        now = _as_int(context.get("now"))
        item_time = _as_int(item.get("time"))
        age_seconds = max(0, now - item_time)
        velocity_points_per_hour = calculate_velocity(raw_score, age_seconds)
        velocity_score = _clamp(velocity_points_per_hour / 50.0)
        practitioner_score = _clamp(story_points)
    else:
        components = len(practitioner_markers)
        if has_code_block:
            components += 1
            practitioner_markers = practitioner_markers + ["code_block"]
        if has_metric:
            components += 1
            practitioner_markers = practitioner_markers + ["concrete_metric"]
        practitioner_score = _clamp(components / 4.0)
        if hedging_hits:
            practitioner_score = _clamp(practitioner_score + min(0.2, len(hedging_hits) * 0.05))

    return {
        "practitioner_depth": {
            "score": _clamp(practitioner_score),
            "markers": practitioner_markers,
        },
        "velocity": {
            "score": _clamp(velocity_score),
            "points_per_hour": float(velocity_points_per_hour),
        },
        "reference_density": {
            "score": _clamp(reference_score),
            "link_count": int(link_count),
        },
        "thread_depth": {
            "score": _clamp(thread_depth_score),
            "max_depth": int(depth),
        },
        "expert_involvement": _expert_signal(author, experts, trust_scores),
    }


def calculate_quality_score(signals: Signals, weights: Optional[dict[str, float]] = None) -> float:
    applied_weights = dict(DEFAULT_WEIGHTS)
    if weights:
        applied_weights.update(weights)

    weighted_sum = 0.0
    total_weight = 0.0
    for signal_name, signal_weight in applied_weights.items():
        score = _clamp(float(signals.get(signal_name, {"score": 0.0})["score"]))
        weight_value = max(0.0, float(signal_weight))
        weighted_sum += score * weight_value
        total_weight += weight_value

    if total_weight == 0.0:
        return 0.0
    return _clamp(weighted_sum / total_weight)
