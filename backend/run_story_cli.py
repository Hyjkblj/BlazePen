"""Unified CLI entrypoint for story backend operational commands.

Commands:
1. ``init-db``: run the explicit DB init / migration script
2. ``check-db``: inspect current DB readiness
3. ``smoke``: run deterministic story backend smoke tests
4. ``probe-llm``: run a minimal story flow and report whether LLM was invoked
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

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
            "  python backend/run_story_cli.py smoke -- backend/test_story_route_smoke.py -q\n"
            "  python backend/run_story_cli.py probe-llm --character-id 7\n"
            "  python backend/run_story_cli.py probe-llm --character-id 7 --scene-id school --user-input \"继续\""
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["init-db", "check-db", "smoke", "probe-llm"],
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


def _build_llm_probe_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python backend/run_story_cli.py probe-llm",
        description=(
            "Run a minimal story flow (init -> initialize -> one submit) and "
            "report whether the story agent actually invoked LLMService."
        ),
    )
    parser.add_argument(
        "--character-id",
        required=True,
        type=int,
        help="Existing character id used for probe flow",
    )
    parser.add_argument(
        "--user-id",
        default="story-cli-probe-user",
        help="Optional user id for this probe session",
    )
    parser.add_argument(
        "--scene-id",
        default="school",
        help="Opening major scene id, default: school",
    )
    parser.add_argument(
        "--opening-event-id",
        default=None,
        help="Optional opening event id inside scene",
    )
    parser.add_argument(
        "--user-input",
        default="继续",
        help="User input text for the probe turn",
    )
    parser.add_argument(
        "--option-id",
        default=None,
        type=int,
        help="Optional option index for the submit turn",
    )
    parser.add_argument(
        "--compact-json",
        action="store_true",
        help="Print compact JSON without indentation",
    )
    return parser


def _safe_llm_provider_context(llm_instance: object) -> Dict[str, Any]:
    provider = getattr(llm_instance, "provider_name", None)
    model = None
    try:
        get_model = getattr(llm_instance, "get_model", None)
        if callable(get_model):
            model = get_model()
    except Exception:
        model = None
    return {"provider": provider, "model": model}


def run_story_llm_probe(raw_probe_args: list[str]) -> int:
    """Probe story flow and print JSON report for real LLM invocation evidence."""

    probe_parser = _build_llm_probe_parser()
    probe_args = probe_parser.parse_args(_strip_smoke_passthrough_prefix(raw_probe_args))

    from api.dependencies import get_game_service
    from llm.base import LLMService

    counters = {"provider_call_count": 0, "retry_wrapper_count": 0}
    call_trace: list[Dict[str, Any]] = []
    retry_trace: list[Dict[str, Any]] = []
    original_call = LLMService.call
    original_call_with_retry = LLMService.call_with_retry

    def traced_call(
        self,
        messages,
        max_tokens=None,
        temperature=None,
        **kwargs,
    ):
        counters["provider_call_count"] += 1
        context = _safe_llm_provider_context(self)
        call_trace.append(
            {
                "provider": context["provider"],
                "model": context["model"],
                "message_count": len(messages or []),
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return original_call(
            self,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

    def traced_call_with_retry(
        self,
        messages,
        max_tokens=None,
        temperature=None,
        max_retries=3,
        retry_delay=1.0,
        **kwargs,
    ):
        counters["retry_wrapper_count"] += 1
        context = _safe_llm_provider_context(self)
        retry_trace.append(
            {
                "provider": context["provider"],
                "model": context["model"],
                "message_count": len(messages or []),
                "max_retries": max_retries,
                "retry_delay": retry_delay,
            }
        )
        return original_call_with_retry(
            self,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            max_retries=max_retries,
            retry_delay=retry_delay,
            **kwargs,
        )

    LLMService.call = traced_call
    LLMService.call_with_retry = traced_call_with_retry

    report: Dict[str, Any]
    exit_code = 1

    try:
        game_service = get_game_service()
        init_payload = game_service.init_game(
            user_id=probe_args.user_id,
            character_id=probe_args.character_id,
            game_mode="solo",
        )
        thread_id = str(init_payload["thread_id"])

        initialize_payload = game_service.initialize_story(
            thread_id=thread_id,
            character_id=probe_args.character_id,
            scene_id=probe_args.scene_id,
            opening_event_id=probe_args.opening_event_id,
        )
        submit_payload = game_service.submit_story_turn(
            thread_id=thread_id,
            user_input=probe_args.user_input,
            option_id=probe_args.option_id,
            user_id=probe_args.user_id,
            character_id=str(probe_args.character_id),
        )

        llm_called = counters["provider_call_count"] > 0
        provider_model_pairs = []
        for item in call_trace + retry_trace:
            pair = {
                "provider": item.get("provider"),
                "model": item.get("model"),
            }
            if pair not in provider_model_pairs:
                provider_model_pairs.append(pair)
        report = {
            "probe_success": True,
            "llm_called": llm_called,
            "llm_invocation_count": counters["provider_call_count"],
            "llm_retry_wrapper_count": counters["retry_wrapper_count"],
            "thread_id": thread_id,
            "provider_models_seen": provider_model_pairs,
            "llm_call_trace_sample": call_trace[:5],
            "llm_retry_trace_sample": retry_trace[:5],
            "initialize_has_options": bool(initialize_payload.get("player_options")),
            "submit_has_options": bool(submit_payload.get("player_options")),
            "fallback_suspected": not llm_called,
        }
        exit_code = 0 if llm_called else 3
    except Exception as exc:
        report = {
            "probe_success": False,
            "llm_called": counters["provider_call_count"] > 0,
            "llm_invocation_count": counters["provider_call_count"],
            "llm_retry_wrapper_count": counters["retry_wrapper_count"],
            "provider_models_seen": [
                {
                    "provider": item.get("provider"),
                    "model": item.get("model"),
                }
                for item in call_trace[:5]
            ],
            "llm_call_trace_sample": call_trace[:5],
            "llm_retry_trace_sample": retry_trace[:5],
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        exit_code = 1
    finally:
        LLMService.call = original_call
        LLMService.call_with_retry = original_call_with_retry

    if probe_args.compact_json:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


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

    if command == "probe-llm":
        return run_story_llm_probe(list(args.smoke_args))

    parser.error(f"unsupported command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
