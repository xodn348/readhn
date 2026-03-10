from collections.abc import Mapping
from tests.conftest import SIGNALS_SCHEMA

from hnmcp.quality import (
    calculate_quality_score,
    calculate_signals,
    calculate_velocity,
    count_references,
    detect_practitioner_markers,
)


def _assert_signals_schema(signals: Mapping[str, object], schema: Mapping[str, object]) -> None:
    assert set(signals.keys()) == set(schema.keys())
    for key, sub_schema in schema.items():
        signal_value = signals[key]
        assert isinstance(signal_value, Mapping)
        assert isinstance(sub_schema, Mapping)
        assert set(signal_value.keys()) == set(sub_schema.keys())


def test_practitioner_markers_detected() -> None:
    text = "I built this at our team and we deployed it in production."
    matched = detect_practitioner_markers(text)

    assert "i built" in matched
    assert "our team" in matched

    signals = calculate_signals({"type": "comment", "text": text, "by": "alice"}, {})
    assert signals["practitioner_depth"]["score"] > 0.0


def test_practitioner_markers_with_code_block() -> None:
    text = "<pre>SELECT * FROM events;</pre>"
    signals = calculate_signals({"type": "comment", "text": text, "by": "alice"}, {})

    assert signals["practitioner_depth"]["score"] > 0.0
    assert "code_block" in signals["practitioner_depth"]["markers"]


def test_velocity_scoring() -> None:
    per_hour = calculate_velocity(score=50, age_seconds=3600)
    signals = calculate_signals(
        {"type": "story", "score": 50, "time": 0, "by": "alice"}, {"now": 3600}
    )

    assert per_hour >= 49.0
    assert signals["velocity"]["score"] > 0.7


def test_velocity_old_story() -> None:
    five_years_seconds = 5 * 365 * 24 * 3600
    per_hour = calculate_velocity(score=50, age_seconds=five_years_seconds)
    signals = calculate_signals(
        {"type": "story", "score": 50, "time": 0, "by": "alice"}, {"now": five_years_seconds}
    )

    assert per_hour > 0.0
    assert per_hour < 0.01
    assert 0.0 <= signals["velocity"]["score"] <= 0.05


def test_reference_density() -> None:
    text = "Refs: https://a.com, http://b.dev, https://c.org/docs"
    assert count_references(text) == 3

    signals = calculate_signals({"type": "comment", "text": text, "by": "alice"}, {})
    assert signals["reference_density"]["link_count"] == 3
    assert signals["reference_density"]["score"] > 0.0


def test_thread_depth() -> None:
    item = {"type": "story", "id": 42, "score": 10, "time": 0, "by": "alice"}
    context = {"now": 3600, "thread_depth_map": {42: 4}}
    signals = calculate_signals(item, context)

    assert signals["thread_depth"]["max_depth"] == 4
    assert signals["thread_depth"]["score"] >= 0.75


def test_expert_involvement() -> None:
    item = {"type": "comment", "text": "fwiw we used this", "by": "seed_expert"}
    context = {"experts": ["seed_expert"], "trust_scores": {"seed_expert": 0.92}}
    signals = calculate_signals(item, context)

    assert signals["expert_involvement"]["score"] > 0.0
    assert "seed_expert" in signals["expert_involvement"]["experts"]


def test_full_signals_schema() -> None:
    signals = calculate_signals(
        {"type": "story", "id": 7, "score": 20, "time": 0, "by": "alice"}, {"now": 7200}
    )
    _assert_signals_schema(signals, SIGNALS_SCHEMA)


def test_story_quality_score() -> None:
    item = {
        "type": "story",
        "id": 11,
        "score": 200,
        "time": 0,
        "text": "I built this in production https://example.com",
        "by": "expert_1",
    }
    context = {
        "now": 7200,
        "thread_depth_map": {11: 3},
        "experts": ["expert_1"],
        "trust_scores": {"expert_1": 0.8},
    }
    signals = calculate_signals(item, context)
    quality = calculate_quality_score(signals, {})

    assert 0.0 <= quality <= 1.0
    assert quality > 0.3


def test_comment_quality_score() -> None:
    context = {"experts": ["alice"], "trust_scores": {"alice": 0.7}}
    low_points_comment = {
        "type": "comment",
        "score": 1,
        "text": "I built this at scale. fwiw details: https://example.com",
        "by": "alice",
    }
    high_points_comment = {
        "type": "comment",
        "score": 999,
        "text": "I built this at scale. fwiw details: https://example.com",
        "by": "alice",
    }

    low_signals = calculate_signals(low_points_comment, context)
    high_signals = calculate_signals(high_points_comment, context)
    low_quality = calculate_quality_score(low_signals, {})
    high_quality = calculate_quality_score(high_signals, {})

    assert low_quality > 0.0
    assert low_quality == high_quality


def test_negative_sentiment_not_penalized() -> None:
    context = {"experts": ["alice"], "trust_scores": {"alice": 0.7}}
    negative_text = (
        "This is terrible, broken, and bad. I built this in production: https://example.com"
    )
    neutral_text = "I built this in production: https://example.com"

    negative_quality = calculate_quality_score(
        calculate_signals({"type": "comment", "text": negative_text, "by": "alice"}, context), {}
    )
    neutral_quality = calculate_quality_score(
        calculate_signals({"type": "comment", "text": neutral_text, "by": "alice"}, context), {}
    )

    assert negative_quality == neutral_quality


def test_score_range() -> None:
    item = {
        "type": "story",
        "id": 99,
        "score": 5000,
        "time": 0,
        "text": "I built this in production https://a.com https://b.com",
        "by": "seed",
    }
    context = {
        "now": 3600,
        "thread_depth_map": {99: 8},
        "experts": ["seed"],
        "trust_scores": {"seed": 1.0},
    }
    signals = calculate_signals(item, context)
    quality = calculate_quality_score(signals, {})

    for key in signals:
        assert 0.0 <= signals[key]["score"] <= 1.0
    assert 0.0 <= quality <= 1.0


def test_practitioner_with_metrics() -> None:
    text = "We saw 35% improvement after deploying this change."
    signals = calculate_signals({"type": "comment", "text": text, "by": "alice"}, {})
    assert signals["practitioner_depth"]["score"] > 0.0
    assert "concrete_metric" in signals["practitioner_depth"]["markers"]


def test_quality_score_zero_weights() -> None:
    signals = {
        "practitioner_depth": {"score": 0.5},
        "score_velocity": {"score": 0.5},
        "reference_density": {"score": 0.5},
        "thread_depth": {"score": 0.5},
        "expert_involvement": {"score": 0.5},
    }

    quality = calculate_quality_score(
        signals,
        {
            "practitioner_depth": 0.0,
            "score_velocity": 0.0,
            "reference_density": 0.0,
            "thread_depth": 0.0,
            "expert_involvement": 0.0,
        },
    )

    assert quality == 0.0
