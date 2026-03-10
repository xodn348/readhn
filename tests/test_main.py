import subprocess
import sys


def test_main_entry_point() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "hnmcp", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "FastMCP" in output or "hnmcp" in output


def test_cli_routes_setup_command(monkeypatch) -> None:
    import hnmcp.cli as cli

    calls = {"setup": 0}

    def _fake_setup_main() -> None:
        calls["setup"] += 1

    monkeypatch.setattr("hnmcp.setup.main", _fake_setup_main)
    monkeypatch.setattr("sys.argv", ["readhn", "setup", "--list"])

    cli.main()

    assert calls["setup"] == 1
    assert sys.argv == ["readhn setup", "--list"]


def test_cli_routes_server_when_not_setup(monkeypatch) -> None:
    import hnmcp.cli as cli

    calls = {"server": 0}

    def _fake_server_main() -> None:
        calls["server"] += 1

    monkeypatch.setattr("hnmcp.server.main", _fake_server_main)
    monkeypatch.setattr("sys.argv", ["readhn", "--help"])

    cli.main()

    assert calls["server"] == 1


def test_cli_handles_setup_without_extra_flags(monkeypatch) -> None:
    import hnmcp.cli as cli

    calls = {"setup": 0}

    def _fake_setup_main() -> None:
        calls["setup"] += 1

    monkeypatch.setattr("hnmcp.setup.main", _fake_setup_main)
    monkeypatch.setattr("sys.argv", ["readhn", "setup"])

    cli.main()

    assert calls["setup"] == 1
    assert sys.argv == ["readhn setup"]


def test_module_entrypoint_routes_setup_subcommand() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "hnmcp", "setup", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "readhn setup" in output


def test_module_entrypoint_setup_list_subcommand() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "hnmcp", "setup", "--list"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "No supported AI agents detected" in output or "OpenCode" in output
