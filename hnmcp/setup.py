import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


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


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}
    return data


def deep_merge(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge(target[key], value)
        else:
            target[key] = value
    return target


def create_readhn_entry(fmt: str, experts: list[str], keywords: list[str]) -> dict[str, Any]:
    env = {
        "HN_EXPERTS": ",".join(experts),
        "HN_KEYWORDS": ",".join(keywords),
    }

    if fmt == "claude":
        return {
            "command": "python",
            "args": ["-m", "hnmcp"],
            "env": env,
        }

    if fmt == "opencode":
        return {
            "type": "local",
            "command": ["python", "-m", "hnmcp"],
            "environment": env,
        }

    raise ValueError(f"Unsupported format: {fmt}")


def backup_config(path: Path) -> Optional[Path]:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"{path.name}.backup-{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def atomic_write_config(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
