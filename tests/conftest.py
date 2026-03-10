"""
Shared test fixtures for hnmcp test suite.

Provides realistic mock data structures for HN API responses, Firebase user profiles,
Algolia search results, and trust graph test cases.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional


# ============================================================================
# SIGNALS_SCHEMA: Defines the structure of quality signals
# ============================================================================

SIGNALS_SCHEMA = {
    "practitioner_depth": {"score": float, "markers": list},
    "velocity": {"score": float, "points_per_hour": float},
    "reference_density": {"score": float, "link_count": int},
    "thread_depth": {"score": float, "max_depth": int},
    "expert_involvement": {"score": float, "experts": list, "trust_scores": dict},
}


# ============================================================================
# FIXTURE 1: mock_story
# ============================================================================


@pytest.fixture
def mock_story() -> Dict[str, Any]:
    """
    Sample HN story dict matching Firebase API response shape.

    Includes: id, title, score, by, descendants, time, kids, url, text, type
    """
    return {
        "id": 12345,
        "title": "Building a Hacker News Quality Filter",
        "score": 250,
        "by": "alice_dev",
        "descendants": 45,
        "time": 1234567890,
        "kids": [12346, 12347, 12348],
        "url": "https://example.com/article",
        "text": None,
        "type": "story",
    }


# ============================================================================
# FIXTURE 2: mock_comment
# ============================================================================


@pytest.fixture
def mock_comment() -> Dict[str, Any]:
    """
    Sample HN comment dict matching Firebase API response shape.

    Includes: id, by, text, time, kids, parent, type, deleted, dead
    """
    return {
        "id": 12346,
        "by": "bob_engineer",
        "text": "This is a great approach to filtering low-quality comments.",
        "time": 1234567900,
        "kids": [12349, 12350],
        "parent": 12345,
        "type": "comment",
        "deleted": False,
        "dead": False,
    }


# ============================================================================
# FIXTURE 3: mock_expert_comment
# ============================================================================


@pytest.fixture
def mock_expert_comment() -> Dict[str, Any]:
    """
    Sample HN comment with practitioner markers (expertise signals).

    Includes code blocks and "I built" / "I work on" markers.
    """
    return {
        "id": 12351,
        "by": "carol_expert",
        "text": """I built a similar system at my company. Here's what we learned:

```python
def filter_quality(comments):
    return [c for c in comments if c.score > threshold]
```

The key insight is that velocity matters more than raw score. We saw a 40% improvement in signal-to-noise ratio.""",
        "time": 1234567950,
        "kids": [12352],
        "parent": 12345,
        "type": "comment",
        "deleted": False,
        "dead": False,
    }


# ============================================================================
# FIXTURE 4: mock_user_profile
# ============================================================================


@pytest.fixture
def mock_user_profile() -> Dict[str, Any]:
    """
    Sample Firebase user profile dict.

    Includes: id, karma, created, about, submitted
    """
    return {
        "id": "alice_dev",
        "karma": 5000,
        "created": 1200000000,
        "about": "Software engineer interested in NLP and information quality.",
        "submitted": [12345, 12346, 12347, 12348, 12349],
    }


# ============================================================================
# FIXTURE 5: mock_algolia_response
# ============================================================================


@pytest.fixture
def mock_algolia_response() -> Dict[str, Any]:
    """
    Sample Algolia search API response.

    Includes: hits array with author, comment_text, created_at_i, objectID, etc.
    """
    return {
        "hits": [
            {
                "author": "bob_engineer",
                "comment_text": "This is a great approach to filtering low-quality comments.",
                "created_at_i": 1234567900,
                "objectID": "12346",
                "parent_id": "12345",
                "story_id": "12345",
                "story_title": "Building a Hacker News Quality Filter",
                "points": 15,
                "children": [{"id": "12349"}, {"id": "12350"}],
            },
            {
                "author": "carol_expert",
                "comment_text": "I built a similar system at my company.",
                "created_at_i": 1234567950,
                "objectID": "12351",
                "parent_id": "12345",
                "story_id": "12345",
                "story_title": "Building a Hacker News Quality Filter",
                "points": 42,
                "children": [{"id": "12352"}],
            },
        ],
        "nbHits": 2,
        "nbPages": 1,
        "page": 0,
        "processingTimeMs": 5,
    }


# ============================================================================
# FIXTURE 6: sample_profile_json
# ============================================================================


@pytest.fixture
def sample_profile_json() -> str:
    """
    Valid profile.json content as JSON string.

    Contains: keywords, experts, min_score, weights
    """
    profile = {
        "keywords": ["machine learning", "distributed systems", "rust"],
        "experts": ["alice_dev", "bob_engineer", "carol_expert"],
        "min_score": 10,
        "weights": {
            "practitioner_depth": 0.3,
            "velocity": 0.2,
            "reference_density": 0.2,
            "thread_depth": 0.15,
            "expert_involvement": 0.15,
        },
    }
    return json.dumps(profile, indent=2)


# ============================================================================
# FIXTURE 7: sample_trust_graph
# ============================================================================


@pytest.fixture
def sample_trust_graph() -> Dict[str, Any]:
    """
    5-user trust matrix with hand-calculated EigenTrust scores.

    Users: A, B, C, D, E
    Seed experts: [A, B]
    Reply edges: A→C, B→C, C→D, D→E

    Expected trust order: A=B (highest, seed) > C (replied to by seeds) > D > E
    """
    return {
        "users": ["A", "B", "C", "D", "E"],
        "seed_experts": ["A", "B"],
        "edges": {"A": ["C"], "B": ["C"], "C": ["D"], "D": ["E"], "E": []},
        "expected_trust_scores": {"A": 0.4, "B": 0.4, "C": 0.15, "D": 0.04, "E": 0.01},
        "description": "A and B are seed experts. C replies to both. D replies to C. E replies to D.",
    }


# ============================================================================
# FIXTURE 8: tmp_profile_dir
# ============================================================================


@pytest.fixture
def tmp_profile_dir(tmp_path: Path) -> Path:
    """
    Temporary directory fixture for profile.json testing.

    Uses pytest's tmp_path fixture to provide a clean, isolated directory.
    """
    return tmp_path


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "SIGNALS_SCHEMA",
    "mock_story",
    "mock_comment",
    "mock_expert_comment",
    "mock_user_profile",
    "mock_algolia_response",
    "sample_profile_json",
    "sample_trust_graph",
    "tmp_profile_dir",
]
