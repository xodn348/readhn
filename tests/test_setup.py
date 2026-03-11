import json
import re
from pathlib import Path
from unittest.mock import patch

from hnmcp.setup import (
    DEFAULT_EXPERTS,
    DEFAULT_KEYWORDS,
    _get_config_paths,
    atomic_write_config,
    backup_config,
    create_readhn_entry,
    deep_merge,
    detect_installed_agents,
    load_config,
    main as setup_main,
    prompt_experts,
    prompt_keywords,
    setup_agent,
    setup_all,
)


def test_get_config_paths_macos_claude_desktop(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/Users/test"))

    paths = _get_config_paths("Claude Desktop")

    assert paths == [
        Path("/Users/test/Library/Application Support/Claude/claude_desktop_config.json")
    ]


def test_get_config_paths_macos_claude_code(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/Users/test"))

    paths = _get_config_paths("Claude Code")

    assert paths == [Path("/Users/test/.claude.json")]


def test_get_config_paths_macos_codex(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/Users/test"))

    paths = _get_config_paths("Codex")

    assert paths == [Path("/Users/test/.codex/config.toml")]


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


def test_get_config_paths_linux_claude_desktop_uses_xdg(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/home/test"))

    paths = _get_config_paths("Claude Desktop")

    assert paths == [
        Path("/xdg/Claude/claude_desktop_config.json"),
        Path("/home/test/.config/Claude/claude_desktop_config.json"),
    ]


def test_get_config_paths_windows_cline_uses_appdata(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\\Users\\test\\AppData\\Roaming")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("C:/Users/test"))

    paths = _get_config_paths("Cline")

    assert str(paths[0]).endswith("Cline/mcp_settings.json")
    assert "Roaming" in str(paths[0])


def test_get_config_paths_linux_cline_uses_xdg(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/home/test"))

    paths = _get_config_paths("Cline")

    assert paths == [
        Path("/xdg/cline/mcp_settings.json"),
        Path("/home/test/.config/cline/mcp_settings.json"),
    ]


def test_get_config_paths_windows_opencode_uses_appdata(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\\Users\\test\\AppData\\Roaming")
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("C:/Users/test"))

    paths = _get_config_paths("OpenCode")

    assert str(paths[0]).endswith("opencode/config.json")
    assert "Roaming" in str(paths[0])


def test_get_config_paths_unknown_agent_returns_empty(monkeypatch) -> None:
    monkeypatch.setattr("hnmcp.setup.Path.home", lambda: Path("/Users/test"))

    assert _get_config_paths("Unknown") == []


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


def test_read_toml_config_returns_empty_on_missing(tmp_path: Path) -> None:
    from hnmcp.setup import _read_toml_config

    assert _read_toml_config(tmp_path / "missing.toml") == ""


def test_read_toml_config_returns_empty_on_oserror(tmp_path: Path) -> None:
    from hnmcp.setup import _read_toml_config

    path = tmp_path / "config.toml"
    path.write_text("x=1\n", encoding="utf-8")
    with patch.object(Path, "read_text", side_effect=OSError("boom")):
        assert _read_toml_config(path) == ""


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


def test_create_readhn_entry_toml_format_shape() -> None:
    entry = create_readhn_entry("toml", ["tptacek"], ["rust", "databases"])

    assert entry["command"] == "python"
    assert entry["args"] == ["-m", "hnmcp"]
    assert entry["env"] == {"HN_EXPERTS": "tptacek", "HN_KEYWORDS": "rust,databases"}


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


def test_atomic_write_config_cleans_temp_on_replace_failure(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "config.json"

    def _boom(_src: str, _dst: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("hnmcp.setup.os.replace", _boom)

    try:
        atomic_write_config(path, {"x": 1})
    except OSError:
        pass
    else:
        raise AssertionError("Expected OSError")

    leftovers = [p for p in path.parent.iterdir() if p.name.startswith("config.json")]
    assert leftovers == []


def test_atomic_write_text_cleans_temp_on_replace_failure(monkeypatch, tmp_path: Path) -> None:
    from hnmcp.setup import _atomic_write_text

    path = tmp_path / "config.toml"

    def _boom(_src: str, _dst: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("hnmcp.setup.os.replace", _boom)

    try:
        _atomic_write_text(path, "x=1\n")
    except OSError:
        pass
    else:
        raise AssertionError("Expected OSError")

    leftovers = [p for p in path.parent.iterdir() if p.name.startswith("config.toml")]
    assert leftovers == []


def test_atomic_write_config_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "config.json"

    atomic_write_config(path, {"ok": True})

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}


def test_prompt_experts_returns_defaults_on_empty_input(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "")

    assert prompt_experts() == DEFAULT_EXPERTS


def test_prompt_experts_parses_comma_separated_values(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "alice, bob , carol")

    assert prompt_experts() == ["alice", "bob", "carol"]


def test_prompt_keywords_returns_defaults_on_empty_input(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "")

    assert prompt_keywords() == DEFAULT_KEYWORDS


def test_prompt_keywords_parses_comma_separated_values(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "ai, python, startups")

    assert prompt_keywords() == ["ai", "python", "startups"]


def test_setup_agent_skips_existing_without_force(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text('{"mcpServers": {"readhn": {"command": "python"}}}', encoding="utf-8")

    modified = setup_agent("Cursor", config, ["a"], ["b"], force=False, dry_run=False)

    assert modified is False


def test_setup_agent_force_overwrites_existing(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text('{"mcpServers": {"readhn": {"command": "old"}}}', encoding="utf-8")

    modified = setup_agent("Cursor", config, ["a"], ["b"], force=True, dry_run=False)

    data = json.loads(config.read_text(encoding="utf-8"))
    assert modified is True
    assert data["mcpServers"]["readhn"]["command"] == "python"


def test_setup_agent_dry_run_does_not_write(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")

    modified = setup_agent("Cursor", config, ["a"], ["b"], force=False, dry_run=True)

    assert modified is True
    assert json.loads(config.read_text(encoding="utf-8")) == {}


def test_setup_agent_creates_backup_when_writing(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")

    _ = setup_agent("Cursor", config, ["a"], ["b"], force=False, dry_run=False)

    backups = list(tmp_path.glob("config.json.backup-*"))
    assert len(backups) == 1


def test_setup_agent_writes_opencode_shape(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")

    modified = setup_agent("OpenCode", config, ["alice"], ["ai"], force=False, dry_run=False)

    data = json.loads(config.read_text(encoding="utf-8"))
    assert modified is True
    assert data["mcp"]["readhn"]["type"] == "local"


def test_setup_agent_handles_non_dict_existing_config_key(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text('{"mcpServers": []}', encoding="utf-8")

    modified = setup_agent("Cursor", config, ["alice"], ["ai"], force=False, dry_run=False)

    data = json.loads(config.read_text(encoding="utf-8"))
    assert modified is True
    assert isinstance(data["mcpServers"], dict)
    assert "readhn" in data["mcpServers"]


def test_setup_agent_is_idempotent_without_force(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")

    first = setup_agent("Cursor", config, ["alice"], ["ai"], force=False, dry_run=False)
    second = setup_agent("Cursor", config, ["alice"], ["ai"], force=False, dry_run=False)

    assert first is True
    assert second is False


def test_setup_agent_writes_codex_toml_shape(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('model = "gpt-5"\n', encoding="utf-8")

    modified = setup_agent("Codex", config, ["alice"], ["ai", "llm"], force=False, dry_run=False)

    data = config.read_text(encoding="utf-8")
    assert modified is True
    assert "[mcp_servers.readhn]" in data
    assert 'command = "python"' in data
    assert 'args = ["-m", "hnmcp"]' in data
    assert "[mcp_servers.readhn.env]" in data
    assert 'HN_EXPERTS = "alice"' in data
    assert 'HN_KEYWORDS = "ai,llm"' in data


def test_setup_agent_codex_force_replaces_existing_block(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        "\n".join(
            [
                'model = "gpt-5"',
                "",
                "[mcp_servers.readhn]",
                'command = "old"',
                'args = ["-m", "old"]',
                "",
                "[mcp_servers.readhn.env]",
                'HN_EXPERTS = "old"',
                'HN_KEYWORDS = "old"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    modified = setup_agent("Codex", config, ["bob"], ["rust"], force=True, dry_run=False)

    data = config.read_text(encoding="utf-8")
    assert modified is True
    assert data.count("[mcp_servers.readhn]") == 1
    assert 'command = "python"' in data
    assert 'HN_EXPERTS = "bob"' in data
    assert 'HN_KEYWORDS = "rust"' in data


def test_setup_agent_codex_skip_when_exists_without_force(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('[mcp_servers.readhn]\ncommand = "python"\n', encoding="utf-8")

    modified = setup_agent("Codex", config, ["bob"], ["rust"], force=False, dry_run=False)

    assert modified is False


def test_setup_agent_codex_dry_run(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('model = "gpt-5"\n', encoding="utf-8")

    modified = setup_agent("Codex", config, ["alice"], ["ai"], force=False, dry_run=True)

    assert modified is True
    assert config.read_text(encoding="utf-8") == 'model = "gpt-5"\n'


def test_setup_agent_codex_write_failure(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('model = "gpt-5"\n', encoding="utf-8")

    def _boom(_path: Path, _content: str) -> None:
        raise OSError("write failed")

    monkeypatch.setattr("hnmcp.setup._atomic_write_text", _boom)

    modified = setup_agent("Codex", config, ["alice"], ["ai"], force=False, dry_run=False)

    assert modified is False


def test_setup_agent_codex_validation_failure(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('model = "gpt-5"\n', encoding="utf-8")

    monkeypatch.setattr("hnmcp.setup._read_toml_config", lambda _p: "")

    modified = setup_agent("Codex", config, ["alice"], ["ai"], force=False, dry_run=False)

    assert modified is False


def test_setup_agent_json_write_failure(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")

    def _boom(_path: Path, _data: dict[str, object]) -> None:
        raise OSError("write failed")

    monkeypatch.setattr("hnmcp.setup.atomic_write_config", _boom)

    modified = setup_agent("Cursor", config, ["alice"], ["ai"], force=False, dry_run=False)

    assert modified is False


def test_setup_agent_json_validation_failure(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("hnmcp.setup.load_config", lambda _p: {})

    modified = setup_agent("Cursor", config, ["alice"], ["ai"], force=False, dry_run=False)

    assert modified is False


def test_setup_all_returns_one_when_no_agents(monkeypatch) -> None:
    monkeypatch.setattr("hnmcp.setup.detect_installed_agents", lambda: {})

    code = setup_all(None, ["a"], ["b"], force=False, dry_run=False)

    assert code == 1


def test_setup_all_filters_requested_agents(monkeypatch, tmp_path: Path) -> None:
    cursor = tmp_path / "cursor.json"
    open_code = tmp_path / "opencode.json"
    monkeypatch.setattr(
        "hnmcp.setup.detect_installed_agents", lambda: {"Cursor": cursor, "OpenCode": open_code}
    )

    calls: list[str] = []

    def _fake_setup(name, *_args, **_kwargs):
        calls.append(name)
        return True

    monkeypatch.setattr("hnmcp.setup.setup_agent", _fake_setup)

    code = setup_all(["Cursor"], ["a"], ["b"], force=False, dry_run=False)

    assert code == 0
    assert calls == ["Cursor"]


def test_setup_all_returns_one_when_filter_matches_nothing(monkeypatch, tmp_path: Path) -> None:
    cursor = tmp_path / "cursor.json"
    monkeypatch.setattr("hnmcp.setup.detect_installed_agents", lambda: {"Cursor": cursor})

    code = setup_all(["OpenCode"], ["a"], ["b"], force=False, dry_run=False)

    assert code == 1


def test_setup_all_prompts_when_values_missing(monkeypatch, tmp_path: Path) -> None:
    cursor = tmp_path / "cursor.json"
    monkeypatch.setattr("hnmcp.setup.detect_installed_agents", lambda: {"Cursor": cursor})
    monkeypatch.setattr("hnmcp.setup.prompt_experts", lambda: ["e1"])
    monkeypatch.setattr("hnmcp.setup.prompt_keywords", lambda: ["k1"])

    captured: dict[str, list[str]] = {}

    def _fake_setup(_name, _path, experts, keywords, _force, _dry_run):
        captured["experts"] = experts
        captured["keywords"] = keywords
        return True

    monkeypatch.setattr("hnmcp.setup.setup_agent", _fake_setup)

    code = setup_all(None, None, None, force=False, dry_run=False)

    assert code == 0
    assert captured == {"experts": ["e1"], "keywords": ["k1"]}


def test_setup_all_uses_provided_values_without_prompt(monkeypatch, tmp_path: Path) -> None:
    cursor = tmp_path / "cursor.json"
    monkeypatch.setattr("hnmcp.setup.detect_installed_agents", lambda: {"Cursor": cursor})

    def _fail_prompt() -> list[str]:
        raise AssertionError("prompt should not be called")

    monkeypatch.setattr("hnmcp.setup.prompt_experts", _fail_prompt)
    monkeypatch.setattr("hnmcp.setup.prompt_keywords", _fail_prompt)
    monkeypatch.setattr("hnmcp.setup.setup_agent", lambda *_args, **_kwargs: True)

    code = setup_all(None, ["e"], ["k"], force=False, dry_run=False)

    assert code == 0


def test_main_list_flag_prints_agents_and_exits(monkeypatch, tmp_path: Path, capsys) -> None:
    cursor = tmp_path / "cursor.json"
    monkeypatch.setattr("hnmcp.setup.detect_installed_agents", lambda: {"Cursor": cursor})
    monkeypatch.setattr("sys.argv", ["readhn setup", "--list"])

    setup_main()
    output = capsys.readouterr().out
    assert "Cursor" in output


def test_main_list_flag_prints_none_when_empty(monkeypatch, capsys) -> None:
    monkeypatch.setattr("hnmcp.setup.detect_installed_agents", lambda: {})
    monkeypatch.setattr("sys.argv", ["readhn setup", "--list"])

    setup_main()
    output = capsys.readouterr().out
    assert "No supported AI agents detected." in output


def test_main_parses_agents_experts_keywords(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "readhn setup",
            "--agents",
            "Cursor,OpenCode",
            "--experts",
            "a,b",
            "--keywords",
            "k1,k2",
            "--force",
            "--dry-run",
        ],
    )

    captured = {}

    def _fake_setup_all(agent_filter, experts, keywords, force, dry_run):
        captured["agent_filter"] = agent_filter
        captured["experts"] = experts
        captured["keywords"] = keywords
        captured["force"] = force
        captured["dry_run"] = dry_run
        return 0

    monkeypatch.setattr("hnmcp.setup.setup_all", _fake_setup_all)

    setup_main()

    assert captured == {
        "agent_filter": ["Cursor", "OpenCode"],
        "experts": ["a", "b"],
        "keywords": ["k1", "k2"],
        "force": True,
        "dry_run": True,
    }
