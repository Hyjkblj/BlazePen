"""Unified CLI entrypoint for story backend operational commands.

Commands:
1. ``init-db``: run the explicit DB init / migration script
2. ``check-db``: inspect current DB readiness
3. ``smoke``: run deterministic story backend smoke tests
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from backend_runner_bootstrap import (
    run_check_database_status_script,
    run_init_db_script,
)


PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STORY_SMOKE_TEST_ARGS = [
    "backend/test_story_standalone_app.py",
    "backend/test_story_route_smoke.py",
    "backend/test_story_restore_smoke.py",
    "-q",
]


def _build_root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Story backend unified CLI entrypoint",
        epilog=(
            "Examples:\n"
            "  python backend/run_story_cli.py init-db\n"
            "  python backend/run_story_cli.py check-db\n"
            "  python backend/run_story_cli.py smoke\n"
            "  python backend/run_story_cli.py smoke -- backend/test_story_route_smoke.py -q"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["init-db", "check-db", "smoke"],
        help="Story backend action to execute",
    )
    parser.add_argument(
        "smoke_args",
        nargs=argparse.REMAINDER,
        help="Optional pytest args for `smoke` (prefix with -- to pass through)",
    )
    return parser


def _strip_smoke_passthrough_prefix(smoke_args: list[str]) -> list[str]:
    if smoke_args and smoke_args[0] == "--":
        return smoke_args[1:]
    return smoke_args


def run_story_smoke_suite(pytest_args: list[str]) -> int:
    """Run story smoke tests via pytest from project root."""

    command = [sys.executable, "-m", "pytest", *pytest_args]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT_DIR,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = _build_root_parser()
    resolved_argv = list(sys.argv[1:] if argv is None else argv)
    if not resolved_argv or resolved_argv[0] in {"-h", "--help"}:
        parser.print_help()
        return 0

    args = parser.parse_args(resolved_argv)
    command = args.command

    if command == "init-db":
        if args.smoke_args:
            parser.error(f"command `{command}` does not accept extra arguments")
        run_init_db_script()
        return 0

    if command == "check-db":
        if args.smoke_args:
            parser.error(f"command `{command}` does not accept extra arguments")
        run_check_database_status_script()
        return 0

    if command == "smoke":
        smoke_args = _strip_smoke_passthrough_prefix(list(args.smoke_args))
        pytest_args = smoke_args or list(DEFAULT_STORY_SMOKE_TEST_ARGS)
        return run_story_smoke_suite(pytest_args)

    parser.error(f"unsupported command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
