import os
import sys
from pathlib import Path


AGENTS = {
    "Claude Desktop": {"config_key": "mcpServers", "format": "claude"},
    "Cursor": {"config_key": "mcpServers", "format": "claude"},
    "Cline": {"config_key": "mcpServers", "format": "claude"},
    "Windsurf": {"config_key": "mcpServers", "format": "claude"},
    "OpenCode": {"config_key": "mcp", "format": "opencode"},
}


def _get_config_paths(agent: str) -> list[Path]:
    home = Path.home()
    is_macos = sys.platform == "darwin"
    is_windows = sys.platform == "win32"

    if agent == "Claude Desktop":
        if is_macos:
            return [home / "Library/Application Support/Claude/claude_desktop_config.json"]
        if is_windows:
            appdata = Path(os.environ.get("APPDATA", str(home / "AppData/Roaming")))
            return [appdata / "Claude/claude_desktop_config.json"]
        xdg = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config")))
        return [
            xdg / "Claude/claude_desktop_config.json",
            home / ".config/Claude/claude_desktop_config.json",
        ]

    if agent == "Cursor":
        return [home / ".cursor/mcp.json"]

    if agent == "Cline":
        if is_windows:
            appdata = Path(os.environ.get("APPDATA", str(home / "AppData/Roaming")))
            return [appdata / "Cline/mcp_settings.json"]
        if is_macos:
            return [home / ".config/cline/mcp_settings.json"]
        xdg = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config")))
        return [xdg / "cline/mcp_settings.json", home / ".config/cline/mcp_settings.json"]

    if agent == "Windsurf":
        return [home / ".codeium/windsurf/mcp_config.json"]

    if agent == "OpenCode":
        if is_windows:
            appdata = Path(os.environ.get("APPDATA", str(home / "AppData/Roaming")))
            return [appdata / "opencode/config.json"]
        if is_macos:
            return [home / ".config/opencode/config.json"]
        xdg = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config")))
        return [xdg / "opencode/config.json", home / ".config/opencode/config.json"]

    return []


def detect_installed_agents() -> dict[str, Path]:
    detected: dict[str, Path] = {}

    for agent_name in AGENTS:
        for path in _get_config_paths(agent_name):
            if path.exists() or path.parent.exists():
                detected[agent_name] = path
                break

    return detected
