import sys


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        sys.argv = [sys.argv[0] + " setup"] + sys.argv[2:]
        from hnmcp.setup import main as setup_main

        setup_main()
        return

    from hnmcp.server import main as server_main

    server_main()
