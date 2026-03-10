import argparse
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

DEFAULT_EXPERTS = ["patio11", "tptacek", "simonw"]
DEFAULT_KEYWORDS = ["ai", "python", "startups"]


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


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def prompt_experts() -> list[str]:
    raw = input(
        f"Seed experts (comma-separated, Enter for defaults: {', '.join(DEFAULT_EXPERTS)}): "
    ).strip()
    return _parse_csv(raw) if raw else DEFAULT_EXPERTS


def prompt_keywords() -> list[str]:
    raw = input(
        f"Default keywords (comma-separated, Enter for defaults: {', '.join(DEFAULT_KEYWORDS)}): "
    ).strip()
    return _parse_csv(raw) if raw else DEFAULT_KEYWORDS


def setup_agent(
    agent_name: str,
    config_path: Path,
    experts: list[str],
    keywords: list[str],
    force: bool,
    dry_run: bool,
) -> bool:
    agent_meta = AGENTS[agent_name]
    config_key = str(agent_meta["config_key"])
    fmt = str(agent_meta["format"])

    config = load_config(config_path)
    existing = config.get(config_key, {})
    if not isinstance(existing, dict):
        existing = {}

    if "readhn" in existing and not force:
        print(f"- {agent_name}: readhn already configured, skipping (use --force to overwrite)")
        return False

    update = {config_key: {"readhn": create_readhn_entry(fmt, experts, keywords)}}
    merged = deep_merge(config, update)

    if dry_run:
        print(f"- {agent_name}: would update {config_path}")
        print(json.dumps(merged, indent=2))
        return True

    backup = backup_config(config_path)
    if backup is not None:
        print(f"- {agent_name}: backup created at {backup}")

    try:
        atomic_write_config(config_path, merged)
    except OSError as exc:
        print(f"- {agent_name}: failed to write config: {exc}")
        return False

    validated = load_config(config_path)
    if not validated:
        print(f"- {agent_name}: write failed validation")
        return False

    print(f"- {agent_name}: configured at {config_path}")
    return True


def setup_all(
    agent_filter: Optional[list[str]],
    experts: Optional[list[str]],
    keywords: Optional[list[str]],
    force: bool,
    dry_run: bool,
) -> int:
    detected = detect_installed_agents()
    if not detected:
        print(
            "No supported AI agents detected. Install one of: Claude Desktop, Cursor, Cline, Windsurf, OpenCode."
        )
        return 1

    selected = detected
    if agent_filter:
        selected = {name: path for name, path in detected.items() if name in set(agent_filter)}
        if not selected:
            print("No matching agents found for --agents filter.")
            return 1

    final_experts = experts if experts is not None else prompt_experts()
    final_keywords = keywords if keywords is not None else prompt_keywords()

    updated = 0
    for agent_name, config_path in selected.items():
        if setup_agent(agent_name, config_path, final_experts, final_keywords, force, dry_run):
            updated += 1

    print(f"Setup complete: updated {updated}/{len(selected)} agent configs.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="readhn setup", description="Configure readhn MCP for supported AI agents"
    )
    parser.add_argument("--agents", help="Comma-separated agent names to configure")
    parser.add_argument("--experts", help="Comma-separated expert seed usernames")
    parser.add_argument("--keywords", help="Comma-separated default keywords")
    parser.add_argument("--force", action="store_true", help="Overwrite existing readhn config")
    parser.add_argument("--list", action="store_true", help="List detected agents and config paths")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview config updates without writing"
    )

    args = parser.parse_args()

    if args.list:
        detected = detect_installed_agents()
        if not detected:
            print("No supported AI agents detected.")
            return
        for name, path in detected.items():
            print(f"{name}: {path}")
        return

    agent_filter = _parse_csv(args.agents) if args.agents else None
    experts = _parse_csv(args.experts) if args.experts else None
    keywords = _parse_csv(args.keywords) if args.keywords else None

    setup_all(agent_filter, experts, keywords, force=args.force, dry_run=args.dry_run)
