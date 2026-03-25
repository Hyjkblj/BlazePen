"""本地直连服务层的交互式训练 CLI。

用途：
1. 不经过 FastAPI 路由，直接实例化 TrainingService。
2. 在终端中按回合手动选择题目、选项并输入作答内容。
3. 适合后端先独立验证训练引擎，再逐步接入前端交互层。
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

from api.services.training_service import TrainingService
from run_training_service_local import (
    DEFAULT_ACTION_TEMPLATES,
    _build_player_profile,
    _configure_stdout_encoding,
    _save_json_artifact,
    _summarize_states,
)
from backend_runner_bootstrap import bootstrap_database
from training.cli_story_script import (
    build_round_feedback_story_block,
    build_scene_story_block,
    build_story_epilogue_block,
    build_story_prologue_block,
    build_transition_story_block,
)


QUIT_COMMANDS = {"q", "quit", "exit"}


def _build_arg_parser() -> argparse.ArgumentParser:
    """构建交互式 CLI 的命令行参数。"""
    parser = argparse.ArgumentParser(description="本地直连 TrainingService 的交互式训练 CLI")
    parser.add_argument("--user-id", default="", help="用户 ID，不传则自动生成")
    parser.add_argument("--training-mode", default="self-paced", help="训练模式：guided / self-paced / adaptive")
    parser.add_argument("--name", default="李敏", help="玩家姓名")
    parser.add_argument("--gender", default="女", help="玩家性别")
    parser.add_argument("--identity", default="战地记者", help="玩家身份")
    parser.add_argument("--age", type=int, default=24, help="玩家年龄")
    parser.add_argument(
        "--skip-init-db",
        action="store_true",
        help="跳过 scripts/init_db.py，仅做连接与服务层调用",
    )
    parser.add_argument(
        "--check-db-status",
        action="store_true",
        help="在 CLI 启动前显式执行 scripts/check_database_status.py",
    )
    parser.add_argument(
        "--save-json-dir",
        default="",
        help="可选：把每一步结果落盘到指定目录，便于 review",
    )
    parser.add_argument(
        "--plain-mode",
        action="store_true",
        help="关闭剧本化叙事包装，仅保留原始 CLI 输出",
    )
    return parser


def _print_section(title: str) -> None:
    """打印分节标题。"""
    print(f"\n=== {title} ===")


def _print_compact_json(payload: Dict[str, Any]) -> None:
    """打印简洁 JSON，便于查看关键输出。"""
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _print_story_block(story_block: Dict[str, Any] | None) -> None:
    """打印剧本层返回的叙事块。

    这里把叙事渲染统一收口，避免主流程里散落格式细节，
    让 CLI 继续只负责“调度”和“展示”两件事。
    """
    if not isinstance(story_block, dict) or not story_block:
        return

    title = str(story_block.get("title") or "").strip()
    paragraphs = list(story_block.get("paragraphs") or [])
    dialogues = list(story_block.get("dialogues") or [])

    if title:
        _print_section(title)

    for paragraph in paragraphs:
        paragraph_text = str(paragraph).strip()
        if paragraph_text:
            print(paragraph_text)

    for dialogue in dialogues:
        speaker = str(dialogue.get("speaker") or "").strip()
        text = str(dialogue.get("text") or "").strip()
        if speaker and text:
            print(f"{speaker}：{text}")


def _prompt_input(prompt_text: str, allow_empty: bool = True) -> str:
    """统一处理用户输入，并兼容退出命令。"""
    while True:
        user_text = input(prompt_text).strip()
        if user_text.lower() in QUIT_COMMANDS:
            raise KeyboardInterrupt("用户主动结束训练")
        if user_text or allow_empty:
            return user_text
        print("输入不能为空，请重试。")


def _pick_scenario_from_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """在当前回合中让用户选择场景。"""
    scenario = bundle.get("scenario")
    scenario_candidates = list(bundle.get("scenario_candidates") or [])

    # 非自选模式通常只有一个系统给定场景，这里直接返回。
    if scenario and not scenario_candidates:
        return dict(scenario)

    if scenario_candidates:
        _print_section("候选题目")
        recommended_id = str((scenario or {}).get("id") or "")
        for index, candidate in enumerate(scenario_candidates, start=1):
            candidate_id = str(candidate.get("id") or "")
            recommendation = dict(candidate.get("recommendation") or {})
            rank = recommendation.get("rank")
            is_recommended = candidate_id == recommended_id or bool(recommendation)
            recommended_flag = " [推荐]" if is_recommended else ""
            rank_text = f" rank={rank}" if rank is not None else ""
            print(f"{index}. {candidate_id} - {candidate.get('title', '')}{recommended_flag}{rank_text}")
            if recommendation:
                reasons = "；".join(recommendation.get("reasons") or [])
                if reasons:
                    print(f"   推荐理由: {reasons}")

        default_index = 1
        selected_text = _prompt_input(f"请选择题目编号，直接回车默认 {default_index}: ")
        if not selected_text:
            return dict(scenario_candidates[default_index - 1])

        try:
            selected_index = int(selected_text)
        except ValueError:
            print("输入不是有效编号，默认选择推荐题。")
            return dict(scenario_candidates[default_index - 1])

        if 1 <= selected_index <= len(scenario_candidates):
            return dict(scenario_candidates[selected_index - 1])

        print("编号超出范围，默认选择推荐题。")
        return dict(scenario_candidates[default_index - 1])

    if scenario:
        return dict(scenario)
    raise ValueError("当前没有可用场景")


def _pick_option_and_text(scenario: Dict[str, Any]) -> tuple[str | None, str]:
    """为当前场景选择选项并收集用户输入。"""
    scenario_id = str(scenario.get("id") or "").strip()
    default_template = DEFAULT_ACTION_TEMPLATES.get(scenario_id, {})
    default_option = str(default_template.get("selected_option") or "").strip() or None
    default_text = str(default_template.get("user_input") or "").strip()

    _print_section("当前场景")
    print(f"场景ID: {scenario_id}")
    print(f"标题: {scenario.get('title', '')}")
    print(f"时间: {scenario.get('era_date', '')}")
    print(f"地点: {scenario.get('location', '')}")
    print(f"任务: {scenario.get('mission', '')}")
    print(f"核心焦点: {scenario.get('decision_focus', '')}")
    print(f"背景: {scenario.get('brief', '')}")

    options = list(scenario.get("options") or [])
    if options:
        _print_section("可选操作")
        for option in options:
            option_id = str(option.get("id") or "")
            default_flag = " [默认]" if option_id == default_option else ""
            print(f"{option_id}. {option.get('label', '')}{default_flag}")
            if option.get("impact_hint"):
                print(f"   提示: {option['impact_hint']}")

        option_prompt = "请输入选项 ID"
        if default_option:
            option_prompt += f"，直接回车默认 {default_option}"
        option_prompt += ": "
        selected_option = _prompt_input(option_prompt)
        if not selected_option:
            selected_option = default_option
    else:
        selected_option = None

    _print_section("请输入你的作答")
    if default_text:
        print(f"默认参考作答: {default_text}")
    user_input = _prompt_input("直接回车使用默认作答，或输入你自己的作答: ")
    if not user_input:
        user_input = default_text or f"针对{scenario.get('title', scenario_id)}，我会先核验事实，再稳妥发布。"

    return selected_option, user_input


def _print_round_feedback(submit_result: Dict[str, Any]) -> None:
    """打印单回合提交后的结果摘要。"""
    _print_section("回合结果")
    evaluation = dict(submit_result.get("evaluation") or {})
    decision_context = dict(submit_result.get("decision_context") or {})
    summary = _summarize_states(submit_result)

    print(f"round_no: {submit_result.get('round_no')}")
    print(f"is_completed: {submit_result.get('is_completed')}")
    print(f"risk_flags: {evaluation.get('risk_flags', [])}")
    print(f"evidence: {evaluation.get('evidence', [])}")
    print(f"selection_source: {decision_context.get('selection_source')}")
    print(f"top_k: {summary['top_k']}")
    print(f"top_s: {summary['top_s']}")


def _print_final_summary(
    player_profile: Dict[str, Any],
    training_mode: str,
    progress_result: Dict[str, Any],
    report_result: Dict[str, Any],
    diagnostics_result: Dict[str, Any],
) -> None:
    """打印最终训练摘要。"""
    ending_payload = dict(report_result.get("ending") or {})
    _print_section("训练完成")
    _print_compact_json(
        {
            "player_profile": player_profile,
            "training_mode": training_mode,
            "round_no": progress_result.get("round_no"),
            "status": progress_result.get("status"),
            "ending_type": ending_payload.get("ending_type") or ending_payload.get("type"),
            "improvement": report_result.get("improvement"),
            "summary": report_result.get("summary"),
            "diagnostics_summary": diagnostics_result.get("summary"),
        }
    )


def run_interactive_cli(args: argparse.Namespace) -> int:
    """执行本地交互式训练流程。"""
    _configure_stdout_encoding()

    if not args.skip_init_db:
        _print_section("数据库初始化")
        print("执行 scripts/init_db.py，统一走显式迁移入口。")

    if getattr(args, "check_db_status", False):
        _print_section("数据库自检")
        print("执行 scripts/check_database_status.py，确认当前数据库状态。")

    db_manager = bootstrap_database(
        skip_init_db=bool(args.skip_init_db),
        check_db_status=bool(getattr(args, "check_db_status", False)),
    )

    training_service = TrainingService(db_manager=db_manager)
    user_id = args.user_id or f"local-cli-{uuid.uuid4().hex[:8]}"
    player_profile = _build_player_profile(args)
    save_dir = Path(args.save_json_dir).resolve() if args.save_json_dir else None
    story_mode_enabled = not bool(args.plain_mode)

    _print_section("玩家建档")
    _print_compact_json(player_profile)

    init_result = training_service.init_training(
        user_id=user_id,
        training_mode=args.training_mode,
        player_profile=player_profile,
    )
    _save_json_artifact(save_dir, "01_init_result", init_result)

    session_id = init_result["session_id"]
    current_bundle: Dict[str, Any] = {
        "scenario": init_result.get("next_scenario"),
        "scenario_candidates": init_result.get("scenario_candidates"),
    }
    current_round_no = 1

    if story_mode_enabled:
        _print_story_block(build_story_prologue_block(player_profile, args.training_mode))

    try:
        while True:
            scenario = _pick_scenario_from_bundle(current_bundle)
            if story_mode_enabled:
                _print_story_block(
                    build_scene_story_block(
                        scenario=scenario,
                        player_profile=player_profile,
                        round_no=current_round_no,
                    )
                )
            selected_option, user_input = _pick_option_and_text(scenario)

            submit_result = training_service.submit_round(
                session_id=session_id,
                scenario_id=str(scenario.get("id")),
                user_input=user_input,
                selected_option=selected_option,
            )
            round_no = int(submit_result.get("round_no") or 0)
            _save_json_artifact(save_dir, f"02_round_{round_no}_submit_result", submit_result)
            if story_mode_enabled:
                _print_story_block(
                    build_round_feedback_story_block(
                        scenario=scenario,
                        submit_result=submit_result,
                        selected_option=selected_option,
                        user_input=user_input,
                    )
                )
            _print_round_feedback(submit_result)

            if submit_result.get("is_completed"):
                break

            next_result = training_service.get_next_scenario(session_id)
            _save_json_artifact(save_dir, f"03_round_{round_no}_next_result", next_result)
            next_scenario = next_result.get("scenario")
            if story_mode_enabled:
                _print_story_block(
                    build_transition_story_block(
                        current_scenario=scenario,
                        next_scenario=next_scenario,
                        player_profile=player_profile,
                    )
                )
            current_bundle = {
                "scenario": next_scenario,
                "scenario_candidates": next_result.get("scenario_candidates"),
            }
            current_round_no = round_no + 1
    except KeyboardInterrupt as exc:
        print(f"\n训练已结束: {exc}")

    progress_result = training_service.get_progress(session_id)
    report_result = training_service.get_report(session_id)
    diagnostics_result = training_service.get_diagnostics(session_id)
    _save_json_artifact(save_dir, "04_progress_result", progress_result)
    _save_json_artifact(save_dir, "05_report_result", report_result)
    _save_json_artifact(save_dir, "06_diagnostics_result", diagnostics_result)

    _print_final_summary(
        player_profile=player_profile,
        training_mode=args.training_mode,
        progress_result=progress_result,
        report_result=report_result,
        diagnostics_result=diagnostics_result,
    )
    if story_mode_enabled:
        _print_story_block(build_story_epilogue_block(player_profile, report_result))
    return 0


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    return run_interactive_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
