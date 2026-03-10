import json
import re
from pathlib import Path

from hnmcp.setup import (
    _get_config_paths,
    atomic_write_config,
    backup_config,
    create_readhn_entry,
    deep_merge,
    detect_installed_agents,
    load_config,
)


def test_get_config_paths_macos_claude_desktop(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/Users/test"))

    paths = _get_config_paths("Claude Desktop")

    assert paths == [
        Path("/Users/test/Library/Application Support/Claude/claude_desktop_config.json")
    ]


def test_get_config_paths_macos_cursor(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/Users/test"))

    paths = _get_config_paths("Cursor")

    assert paths == [Path("/Users/test/.cursor/mcp.json")]


def test_get_config_paths_macos_cline(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/Users/test"))

    paths = _get_config_paths("Cline")

    assert paths == [Path("/Users/test/.config/cline/mcp_settings.json")]


def test_get_config_paths_macos_windsurf(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/Users/test"))

    paths = _get_config_paths("Windsurf")

    assert paths == [Path("/Users/test/.codeium/windsurf/mcp_config.json")]


def test_get_config_paths_macos_opencode(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/Users/test"))

    paths = _get_config_paths("OpenCode")

    assert paths == [Path("/Users/test/.config/opencode/config.json")]


def test_get_config_paths_linux_uses_xdg(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/home/test"))

    paths = _get_config_paths("Cursor")

    assert paths == [Path("/home/test/.cursor/mcp.json")]

    paths = _get_config_paths("OpenCode")

    assert paths == [
        Path("/xdg/opencode/config.json"),
        Path("/home/test/.config/opencode/config.json"),
    ]


def test_get_config_paths_windows_uses_appdata(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\\Users\\test\\AppData\\Roaming")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("C:/Users/test"))

    paths = _get_config_paths("Claude Desktop")

    assert str(paths[0]).endswith("Claude/claude_desktop_config.json")
    assert "Roaming" in str(paths[0])


def test_detect_installed_agents_detects_existing_config(monkeypatch, tmp_path: Path) -> None:
    cursor_config = tmp_path / "cursor.json"
    cursor_config.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "hnmcp.setup._get_config_paths",
        lambda agent: [cursor_config]
        if agent == "Cursor"
        else [tmp_path / "missing" / agent / "config.json"],
    )

    detected = detect_installed_agents()

    assert detected == {"Cursor": cursor_config}


def test_detect_installed_agents_detects_existing_parent_dir(monkeypatch, tmp_path: Path) -> None:
    opencode_config = tmp_path / "opencode" / "config.json"
    opencode_config.parent.mkdir(parents=True)
    monkeypatch.setattr(
        "hnmcp.setup._get_config_paths",
        lambda agent: [opencode_config]
        if agent == "OpenCode"
        else [tmp_path / "missing" / agent / "config.json"],
    )

    detected = detect_installed_agents()

    assert detected == {"OpenCode": opencode_config}


def test_detect_installed_agents_picks_first_existing_path(monkeypatch, tmp_path: Path) -> None:
    first = tmp_path / "first" / "config.json"
    second = tmp_path / "second" / "config.json"
    second.parent.mkdir(parents=True)
    first.parent.mkdir(parents=True)
    first.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "hnmcp.setup._get_config_paths",
        lambda agent: [first, second]
        if agent == "OpenCode"
        else [tmp_path / "missing" / agent / "config.json"],
    )

    detected = detect_installed_agents()

    assert detected == {"OpenCode": first}


def test_detect_installed_agents_ignores_missing_paths(monkeypatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing" / "config.json"
    monkeypatch.setattr("hnmcp.setup._get_config_paths", lambda agent: [missing])

    detected = detect_installed_agents()

    assert detected == {}


def test_detect_installed_agents_empty_when_no_agents(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "hnmcp.setup._get_config_paths",
        lambda agent: [tmp_path / "none" / f"{agent}.json"],
    )

    detected = detect_installed_agents()

    assert detected == {}


def test_load_config_returns_empty_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    assert load_config(missing) == {}


def test_load_config_returns_empty_for_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")

    assert load_config(path) == {}


def test_load_config_returns_empty_for_non_dict_json(tmp_path: Path) -> None:
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")

    assert load_config(path) == {}


def test_load_config_reads_valid_json_dict(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"mcpServers": {"x": {}}}', encoding="utf-8")

    assert load_config(path) == {"mcpServers": {"x": {}}}


def test_deep_merge_recursively_merges_nested_dicts() -> None:
    target = {"a": {"x": 1, "y": 2}, "b": 1}
    source = {"a": {"y": 3, "z": 4}, "c": 2}

    merged = deep_merge(target, source)

    assert merged == {"a": {"x": 1, "y": 3, "z": 4}, "b": 1, "c": 2}


def test_deep_merge_source_wins_on_scalar_conflict() -> None:
    merged = deep_merge({"a": 1}, {"a": 2})

    assert merged == {"a": 2}


def test_deep_merge_replaces_dict_with_scalar() -> None:
    merged = deep_merge({"a": {"x": 1}}, {"a": 3})

    assert merged == {"a": 3}


def test_deep_merge_replaces_scalar_with_dict() -> None:
    merged = deep_merge({"a": 1}, {"a": {"x": 3}})

    assert merged == {"a": {"x": 3}}


def test_deep_merge_returns_target_instance() -> None:
    target = {"a": 1}

    merged = deep_merge(target, {"b": 2})

    assert merged is target
    assert target == {"a": 1, "b": 2}


def test_create_readhn_entry_claude_format_shape() -> None:
    entry = create_readhn_entry("claude", ["patio11"], ["ai", "python"])

    assert entry["command"] == "python"
    assert entry["args"] == ["-m", "hnmcp"]
    assert entry["env"] == {"HN_EXPERTS": "patio11", "HN_KEYWORDS": "ai,python"}


def test_create_readhn_entry_opencode_format_shape() -> None:
    entry = create_readhn_entry("opencode", ["tptacek"], ["startups"])

    assert entry["type"] == "local"
    assert entry["command"] == ["python", "-m", "hnmcp"]
    assert entry["environment"] == {"HN_EXPERTS": "tptacek", "HN_KEYWORDS": "startups"}


def test_create_readhn_entry_handles_empty_lists() -> None:
    entry = create_readhn_entry("claude", [], [])

    assert entry["env"] == {"HN_EXPERTS": "", "HN_KEYWORDS": ""}


def test_create_readhn_entry_raises_for_unknown_format() -> None:
    try:
        create_readhn_entry("unknown", ["a"], ["b"])
    except ValueError as exc:
        assert "Unsupported format" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown format")


def test_backup_config_returns_none_for_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"

    assert backup_config(path) is None


def test_backup_config_creates_timestamped_backup(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"a": 1}', encoding="utf-8")

    backup = backup_config(path)

    assert backup is not None
    assert backup.exists()
    assert re.search(r"config\.json\.backup-\d{8}-\d{6}$", str(backup))


def test_backup_config_preserves_file_contents(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"k": "v"}', encoding="utf-8")

    backup = backup_config(path)

    assert backup is not None
    assert backup.read_text(encoding="utf-8") == '{"k": "v"}'


def test_backup_config_keeps_original_file_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    original = '{"n": 10}'
    path.write_text(original, encoding="utf-8")

    _ = backup_config(path)

    assert path.read_text(encoding="utf-8") == original


def test_atomic_write_config_writes_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "config.json"

    atomic_write_config(path, {"x": 1})

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == {"x": 1}


def test_atomic_write_config_appends_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "config.json"

    atomic_write_config(path, {"x": 1})

    assert path.read_text(encoding="utf-8").endswith("\n")


def test_atomic_write_config_overwrites_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"old": true}', encoding="utf-8")

    atomic_write_config(path, {"new": True})

    assert json.loads(path.read_text(encoding="utf-8")) == {"new": True}


def test_atomic_write_config_keeps_parent_clean_of_temp_files(tmp_path: Path) -> None:
    path = tmp_path / "config.json"

    atomic_write_config(path, {"clean": True})

    leftovers = [p for p in path.parent.iterdir() if p.name.startswith("config.json") and p != path]
    assert leftovers == []


def test_atomic_write_config_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "config.json"

    atomic_write_config(path, {"ok": True})

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}
