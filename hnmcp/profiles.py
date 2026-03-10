"""User preference profiles and configuration management."""

import json
import logging
import os

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


LOGGER = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "practitioner": 0.30,
    "velocity": 0.15,
    "reference": 0.15,
    "thread_depth": 0.20,
    "expert": 0.20,
}


@dataclass
class Profile:
    keywords: list[str] = field(default_factory=list)
    experts: list[str] = field(default_factory=list)
    min_score: int = 0
    time_hours: int = 24
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


def _parse_csv(value: Optional[str]) -> list[str]:
    if value is None or value == "":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_int(value: object, default: int) -> int:
    if value is None or value == "":
        return default
    if not isinstance(value, (int, float, str)):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                cleaned.append(stripped)
    return cleaned


def _load_from_json(profile_path: Path) -> Optional[Profile]:
    try:
        raw_data = json.loads(profile_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        LOGGER.warning("Malformed profile JSON at %s; falling back to environment", profile_path)
        return None

    if not isinstance(raw_data, dict):
        return Profile()

    profile = Profile()
    profile.keywords = _clean_list(raw_data.get("keywords"))
    profile.experts = _clean_list(raw_data.get("experts"))
    profile.min_score = _parse_int(raw_data.get("min_score"), profile.min_score)
    profile.time_hours = _parse_int(raw_data.get("time_hours"), profile.time_hours)

    weights = raw_data.get("weights")
    if isinstance(weights, dict):
        merged_weights = dict(DEFAULT_WEIGHTS)
        for key in DEFAULT_WEIGHTS:
            value = weights.get(key)
            if isinstance(value, (int, float)):
                merged_weights[key] = float(value)
        profile.weights = merged_weights

    return profile


def _load_from_env() -> Profile:
    profile = Profile()
    profile.keywords = _parse_csv(os.getenv("HN_KEYWORDS"))
    profile.experts = _parse_csv(os.getenv("HN_EXPERTS"))
    profile.min_score = _parse_int(os.getenv("HN_MIN_SCORE"), profile.min_score)
    profile.time_hours = _parse_int(os.getenv("HN_TIME_HOURS"), profile.time_hours)
    return profile


def load_profile(path: Optional[str] = None) -> Profile:
    profile_path = Path(path).expanduser() if path else Path("~/.hnmcp/profile.json").expanduser()

    if profile_path.exists():
        loaded = _load_from_json(profile_path)
        if loaded is not None:
            return loaded

    return _load_from_env()
