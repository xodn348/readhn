from pathlib import Path

from hnmcp.setup import _get_config_paths, detect_installed_agents


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
