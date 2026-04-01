"""Standalone runner for the training story script agent.

Usage:
  # 1) Create a new training session (init may write fallback script)
  python run_training_story_script_agent.py init --user-id "debug-user" --training-mode guided --character-id 42

  # 2) Ensure & print story script for an existing session (async ensure)
  python run_training_story_script_agent.py get --session-id "<session-id>" --ensure
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from api.dependencies import get_training_story_script_service, get_training_service


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run training story script agent standalone.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create a training session.")
    init_cmd.add_argument("--user-id", required=True)
    init_cmd.add_argument("--training-mode", default="guided")
    init_cmd.add_argument("--character-id", type=int, default=None)
    init_cmd.add_argument("--out", default="", help="Optional JSON output path.")

    get_cmd = sub.add_parser("get", help="Fetch story script by session_id.")
    get_cmd.add_argument("--session-id", required=True)
    get_cmd.add_argument("--ensure", action="store_true", help="Trigger ensure (async) before reading.")
    get_cmd.add_argument("--out", default="", help="Optional JSON output path.")

    return parser


def main() -> int:
    args = _build_parser().parse_args()

    training_service = get_training_service()
    story_service = get_training_story_script_service()

    if args.command == "init":
        init_result = training_service.init_training(
            user_id=str(args.user_id),
            character_id=args.character_id,
            training_mode=str(args.training_mode),
            player_profile=None,
        )
        if args.out:
            _write_json(Path(args.out), dict(init_result))
        else:
            print(json.dumps(init_result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "get":
        session_id = str(args.session_id)
        if args.ensure:
            ensure_result = story_service.ensure_story_script(session_id)
            if args.out:
                _write_json(Path(args.out), dict(ensure_result))
            else:
                print(json.dumps(ensure_result, ensure_ascii=False, indent=2))
            return 0

        get_result = story_service.get_story_script(session_id)
        if args.out:
            _write_json(Path(args.out), dict(get_result))
        else:
            print(json.dumps(get_result, ensure_ascii=False, indent=2))
        return 0

    raise SystemExit("unknown command")


if __name__ == "__main__":
    raise SystemExit(main())

