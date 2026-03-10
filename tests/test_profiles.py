import logging
from pathlib import Path

from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch
from hnmcp.profiles import Profile, load_profile


def test_load_from_json(tmp_profile_dir: Path, monkeypatch: MonkeyPatch) -> None:
    config_dir = tmp_profile_dir / ".hnmcp"
    config_dir.mkdir()
    profile_file = config_dir / "profile.json"
    profile_file.write_text(
        """
{
  "keywords": ["ai", "rust"],
  "experts": ["simonw", "tptacek"],
  "min_score": 42,
  "time_hours": 6,
  "weights": {
    "practitioner": 0.25,
    "velocity": 0.15,
    "reference": 0.15,
    "thread_depth": 0.25,
    "expert": 0.20
  }
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_profile_dir))

    profile = load_profile()

    assert profile.keywords == ["ai", "rust"]
    assert profile.experts == ["simonw", "tptacek"]
    assert profile.min_score == 42
    assert profile.time_hours == 6
    assert profile.weights["practitioner"] == 0.25


def test_load_fallback_env(tmp_profile_dir: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_profile_dir))
    monkeypatch.setenv("HN_KEYWORDS", "ai,security")
    monkeypatch.setenv("HN_MIN_SCORE", "15")
    monkeypatch.setenv("HN_EXPERTS", "pg,sw")
    monkeypatch.setenv("HN_TIME_HOURS", "12")

    profile = load_profile()

    assert profile.keywords == ["ai", "security"]
    assert profile.experts == ["pg", "sw"]
    assert profile.min_score == 15
    assert profile.time_hours == 12


def test_load_fallback_defaults(tmp_profile_dir: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_profile_dir))
    monkeypatch.delenv("HN_KEYWORDS", raising=False)
    monkeypatch.delenv("HN_MIN_SCORE", raising=False)
    monkeypatch.delenv("HN_EXPERTS", raising=False)
    monkeypatch.delenv("HN_TIME_HOURS", raising=False)

    profile = load_profile()

    assert profile == Profile()


def test_malformed_json(
    tmp_profile_dir: Path,
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    config_dir = tmp_profile_dir / ".hnmcp"
    config_dir.mkdir()
    (config_dir / "profile.json").write_text("{ not-json ", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_profile_dir))
    monkeypatch.setenv("HN_KEYWORDS", "ai,rust")
    monkeypatch.setenv("HN_MIN_SCORE", "9")

    with caplog.at_level(logging.WARNING):
        profile = load_profile()

    assert profile.keywords == ["ai", "rust"]
    assert profile.min_score == 9
    assert "malformed" in caplog.text.lower() or "invalid" in caplog.text.lower()


def test_env_overrides_defaults(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("HN_KEYWORDS", "ai,rust")

    profile = load_profile(path="/definitely/missing/profile.json")

    assert profile.keywords == ["ai", "rust"]


def test_empty_string_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("HN_KEYWORDS", "")

    profile = load_profile(path="/definitely/missing/profile.json")

    assert profile.keywords == []


def test_profile_schema_validation(tmp_profile_dir: Path) -> None:
    profile_file = tmp_profile_dir / "profile.json"
    profile_file.write_text(
        """
{
  "keywords": "not-a-list",
  "experts": ["alice", 42],
  "min_score": "bad",
  "unknown_field": "ignore-me"
}
""".strip(),
        encoding="utf-8",
    )

    profile = load_profile(path=str(profile_file))

    assert profile.keywords == []
    assert profile.experts == ["alice"]
    assert profile.min_score == 0
    assert profile.time_hours == 24


def test_profile_reload(tmp_profile_dir: Path) -> None:
    profile_file = tmp_profile_dir / "profile.json"
    profile_file.write_text('{"keywords": ["ai"], "min_score": 1}', encoding="utf-8")
    first = load_profile(path=str(profile_file))

    profile_file.write_text('{"keywords": ["rust"], "min_score": 99}', encoding="utf-8")
    second = load_profile(path=str(profile_file))

    assert first.keywords == ["ai"]
    assert second.keywords == ["rust"]
    assert second.min_score == 99
