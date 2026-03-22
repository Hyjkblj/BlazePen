"""Unified CLI entrypoint for the training backend.

Commands:
1. ``init-db``: run the explicit DB init / migration script
2. ``check-db``: inspect current DB readiness
3. ``smoke``: run the non-interactive local training smoke flow
4. ``play``: run the interactive training CLI
5. ``experience``: one-click full backend training experience
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import run_training_service_cli
import run_training_service_local
from backend_runner_bootstrap import (
    run_check_database_status_script,
    run_init_db_script,
)


PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent


def _build_root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="训练后端统一 CLI 入口",
        epilog=(
            "示例:\n"
            "  python backend/run_training_cli.py init-db\n"
            "  python backend/run_training_cli.py check-db\n"
            "  python backend/run_training_cli.py smoke --check-db-status\n"
            "  python backend/run_training_cli.py play --check-db-status\n"
            "  python backend/run_training_cli.py experience"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["init-db", "check-db", "smoke", "play", "experience"],
        help="要执行的训练后端动作",
    )
    return parser


def _print_simple_command_help(command: str) -> None:
    if command == "init-db":
        print("usage: python backend/run_training_cli.py init-db")
        print()
        print("Run the explicit training DB init / migration script.")
        return

    if command == "check-db":
        print("usage: python backend/run_training_cli.py check-db")
        print()
        print("Run the explicit training DB status check script.")
        return

    if command == "experience":
        print("usage: python backend/run_training_cli.py experience [smoke args]")
        print()
        print("One-click full backend training experience:")
        print("1. initialize / migrate DB unless --skip-init-db is passed")
        print("2. run explicit DB status check")
        print("3. execute the full non-interactive training smoke flow by default")
        print("4. when --interactive is provided, switch to the interactive training CLI")
        print("5. save JSON replay artifacts to a timestamped directory by default")
        print()
        print("Example:")
        print("  python backend/run_training_cli.py experience")
        print("  python backend/run_training_cli.py experience --round-limit 3")
        print("  python backend/run_training_cli.py experience --interactive")
        print("  python backend/run_training_cli.py experience --skip-init-db --training-mode guided")
        return

    raise ValueError(f"unsupported command help: {command}")


def _build_default_experience_artifact_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return PROJECT_ROOT_DIR / "tmp" / "training-experience" / timestamp


def _build_experience_args(remaining_args: list[str]) -> list[str]:
    resolved_args = list(remaining_args)

    if "--check-db-status" not in resolved_args:
        resolved_args.append("--check-db-status")

    if "--save-json-dir" not in resolved_args:
        artifact_dir = _build_default_experience_artifact_dir()
        resolved_args.extend(["--save-json-dir", str(artifact_dir)])

    return resolved_args


def _extract_experience_mode(remaining_args: list[str]) -> tuple[bool, list[str]]:
    interactive = False
    forwarded_args: list[str] = []
    for arg in remaining_args:
        if arg == "--interactive":
            interactive = True
            continue
        forwarded_args.append(arg)
    return interactive, forwarded_args


def main(argv: list[str] | None = None) -> int:
    parser = _build_root_parser()
    resolved_argv = list(sys.argv[1:] if argv is None else argv)
    if not resolved_argv or resolved_argv[0] in {"-h", "--help"}:
        parser.print_help()
        return 0

    command = resolved_argv[0]
    remaining_args = resolved_argv[1:]
    if command not in {"init-db", "check-db", "smoke", "play", "experience"}:
        parser.error(
            f"invalid choice: {command!r} "
            "(choose from 'init-db', 'check-db', 'smoke', 'play', 'experience')"
        )

    if command == "init-db":
        if remaining_args in (["-h"], ["--help"]):
            _print_simple_command_help(command)
            return 0
        if remaining_args:
            parser.error(f"command `{command}` does not accept extra arguments: {' '.join(remaining_args)}")
        run_init_db_script()
        return 0

    if command == "check-db":
        if remaining_args in (["-h"], ["--help"]):
            _print_simple_command_help(command)
            return 0
        if remaining_args:
            parser.error(f"command `{command}` does not accept extra arguments: {' '.join(remaining_args)}")
        run_check_database_status_script()
        return 0

    if command == "smoke":
        return run_training_service_local.main(remaining_args)

    if command == "play":
        return run_training_service_cli.main(remaining_args)

    if command == "experience":
        if remaining_args in (["-h"], ["--help"]):
            _print_simple_command_help(command)
            return 0
        interactive_mode, forwarded_args = _extract_experience_mode(remaining_args)
        experience_args = _build_experience_args(forwarded_args)
        print("=== Training Backend Full Experience ===")
        if interactive_mode:
            print("Flow: init-db/check-db/interactive-training/report/diagnostics")
        else:
            print("Flow: init-db/check-db/full-smoke/report/diagnostics")
        if "--save-json-dir" in experience_args:
            artifact_dir = experience_args[experience_args.index("--save-json-dir") + 1]
            print(f"Artifacts: {artifact_dir}")
        print()
        if interactive_mode:
            return run_training_service_cli.main(experience_args)
        return run_training_service_local.main(experience_args)

    parser.error(f"unsupported command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
