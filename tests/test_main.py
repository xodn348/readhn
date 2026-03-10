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
