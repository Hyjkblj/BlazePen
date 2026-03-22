"""本地直连服务层的训练引擎烟测脚本。

用途：
1. 不经过 FastAPI 路由，直接实例化 TrainingService。
2. 从玩家建档开始，完整跑通初始化、回合提交、进度、报告、诊断。
3. 便于后端在本地先验证训练闭环，再接前端或控制层。
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

from api.services.training_service import TrainingService
from training_runner_bootstrap import bootstrap_database


# 为不同场景准备一组更贴合业务的默认作答文本。
# 这样本地烟测时，输出会更接近真实训练过程，而不是纯占位字符串。
DEFAULT_ACTION_TEMPLATES: Dict[str, Dict[str, str]] = {
    "S1": {
        "selected_option": "C",
        "user_input": "我会先发布已经确认的事实，同时明确说明哪些信息仍在核验，避免把未证实内容写成定论。",
    },
    "S2": {
        "selected_option": "B",
        "user_input": "我只写已经交叉核验过的战况和伤亡数据，并标清来源与不确定部分，避免情绪化放大。",
    },
    "S3": {
        "selected_option": "B",
        "user_input": "我会匿名化处理幸存者身份和藏身位置，只保留必要事实，优先保护线人和受访者安全。",
    },
    "S4": {
        "selected_option": "B",
        "user_input": "我会把风险讲清楚，再给群众分步骤、可执行的行动建议，避免制造恐慌。",
    },
    "S5": {
        "selected_option": "B",
        "user_input": "我会把材料分成已核实、待核实、不可发布三层，先提交一版清晰的核验报告给编辑部。",
    },
    "S6": {
        "selected_option": "B",
        "user_input": "我会只写已经确认的核心事实，并明确后续更新机制，保证重大节点报道稳妥可信。",
    },
}

def _configure_stdout_encoding() -> None:
    """尽量把终端输出切到 UTF-8，减少 Windows 控制台中文显示异常。"""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except ValueError:
            # 某些宿主环境不允许重新配置时，直接忽略即可。
            pass


def _build_arg_parser() -> argparse.ArgumentParser:
    """构建命令行参数。"""
    parser = argparse.ArgumentParser(description="本地直连 TrainingService 的训练引擎烟测脚本")
    parser.add_argument("--user-id", default="", help="用户 ID，不传则自动生成")
    parser.add_argument("--training-mode", default="self-paced", help="训练模式：guided / self-paced / adaptive")
    parser.add_argument("--name", default="李敏", help="玩家姓名")
    parser.add_argument("--gender", default="女", help="玩家性别")
    parser.add_argument("--identity", default="战地记者", help="玩家身份")
    parser.add_argument("--age", type=int, default=24, help="玩家年龄")
    parser.add_argument("--round-limit", type=int, default=6, help="最大自动推进回合数")
    parser.add_argument(
        "--selection-strategy",
        choices=["recommended", "first_candidate"],
        default="recommended",
        help="自选题模式下的选题策略",
    )
    parser.add_argument(
        "--skip-init-db",
        action="store_true",
        help="跳过 scripts/init_db.py，仅做连接与服务层调用",
    )
    parser.add_argument(
        "--check-db-status",
        action="store_true",
        help="在烟测前显式执行 scripts/check_database_status.py",
    )
    parser.add_argument(
        "--save-json-dir",
        default="",
        help="可选：把每一步结果落盘到指定目录，便于复盘",
    )
    return parser


def _build_player_profile(args: argparse.Namespace) -> Dict[str, Any]:
    """从命令行参数构造玩家档案。"""
    player_profile = {
        "name": args.name,
        "gender": args.gender,
        "identity": args.identity,
        "age": args.age,
    }
    return {key: value for key, value in player_profile.items() if value is not None and value != ""}


def _select_scenario(bundle: Dict[str, Any], selection_strategy: str) -> Dict[str, Any]:
    """从初始化结果或下一题结果中挑选本轮要提交的场景。"""
    scenario = bundle.get("scenario") or bundle.get("next_scenario")
    scenario_candidates = bundle.get("scenario_candidates") or []

    if selection_strategy == "first_candidate" and scenario_candidates:
        return dict(scenario_candidates[0])

    if scenario:
        return dict(scenario)

    if scenario_candidates:
        return dict(scenario_candidates[0])

    raise ValueError("当前结果中没有可提交的场景")


def _select_option_id(scenario: Dict[str, Any]) -> str | None:
    """为当前场景选择一个默认选项。"""
    scenario_id = str(scenario.get("id") or "").strip()
    preferred_option = DEFAULT_ACTION_TEMPLATES.get(scenario_id, {}).get("selected_option")
    options = list(scenario.get("options") or [])

    if preferred_option:
        for option in options:
            if str(option.get("id") or "").strip() == preferred_option:
                return preferred_option

    if options:
        return str(options[0].get("id") or "").strip() or None
    return None


def _build_user_input(scenario: Dict[str, Any]) -> str:
    """为场景生成默认作答文本。"""
    scenario_id = str(scenario.get("id") or "").strip()
    template = DEFAULT_ACTION_TEMPLATES.get(scenario_id)
    if template and template.get("user_input"):
        return str(template["user_input"])

    scenario_title = str(scenario.get("title") or scenario_id or "未知场景")
    return f"针对{scenario_title}，我会先核验事实、保护线人安全，再给出稳妥、可执行的报道表达。"


def _summarize_states(payload: Dict[str, Any], top_n: int = 3) -> Dict[str, Any]:
    """提取 K/S 状态中的重点信息，方便终端快速查看。"""
    k_state = dict(payload.get("k_state") or payload.get("k_state_final") or {})
    s_state = dict(payload.get("s_state") or payload.get("s_state_final") or {})

    sorted_k = sorted(k_state.items(), key=lambda item: item[1], reverse=True)
    sorted_s = sorted(s_state.items(), key=lambda item: item[1], reverse=True)
    return {
        "top_k": sorted_k[:top_n],
        "top_s": sorted_s[:top_n],
    }


def _print_section(title: str) -> None:
    """打印分节标题。"""
    print(f"\n=== {title} ===")


def _print_json(payload: Dict[str, Any]) -> None:
    """统一打印 JSON。"""
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _save_json_artifact(save_dir: Path | None, name: str, payload: Dict[str, Any]) -> None:
    """按步骤落盘 JSON，便于后续复盘。"""
    if save_dir is None:
        return
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_local_smoke(args: argparse.Namespace) -> int:
    """执行直连服务层的完整烟测流程。"""
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
    user_id = args.user_id or f"local-training-{uuid.uuid4().hex[:8]}"
    player_profile = _build_player_profile(args)
    save_dir = Path(args.save_json_dir).resolve() if args.save_json_dir else None

    _print_section("步骤1 初始化训练")
    init_result = training_service.init_training(
        user_id=user_id,
        training_mode=args.training_mode,
        player_profile=player_profile,
    )
    _save_json_artifact(save_dir, "01_init_result", init_result)
    print(f"session_id: {init_result['session_id']}")
    print(f"training_mode: {args.training_mode}")
    print(f"player_profile: {json.dumps(init_result.get('player_profile') or {}, ensure_ascii=False)}")
    print(f"first_scenario: {init_result.get('next_scenario', {}).get('id')} / {init_result.get('next_scenario', {}).get('title')}")

    current_bundle = {
        "next_scenario": init_result.get("next_scenario"),
        "scenario_candidates": init_result.get("scenario_candidates"),
    }
    session_id = init_result["session_id"]
    round_results: List[Dict[str, Any]] = []

    for round_index in range(1, max(int(args.round_limit), 1) + 1):
        scenario = _select_scenario(current_bundle, args.selection_strategy)
        selected_option = _select_option_id(scenario)
        user_input = _build_user_input(scenario)

        _print_section(f"步骤2 回合 {round_index} 提交")
        print(f"scenario_id: {scenario.get('id')}")
        print(f"scenario_title: {scenario.get('title')}")
        print(f"selected_option: {selected_option}")
        print(f"user_input: {user_input}")

        submit_result = training_service.submit_round(
            session_id=session_id,
            scenario_id=str(scenario.get("id")),
            user_input=user_input,
            selected_option=selected_option,
        )
        round_results.append(submit_result)
        _save_json_artifact(save_dir, f"02_round_{round_index}_submit_result", submit_result)

        summary = _summarize_states(submit_result)
        print(f"is_completed: {submit_result['is_completed']}")
        print(f"risk_flags: {submit_result.get('evaluation', {}).get('risk_flags', [])}")
        print(f"top_k: {summary['top_k']}")
        print(f"top_s: {summary['top_s']}")

        if submit_result["is_completed"]:
            break

        next_result = training_service.get_next_scenario(session_id)
        _save_json_artifact(save_dir, f"03_round_{round_index}_next_result", next_result)

        _print_section(f"步骤3 回合 {round_index} 后推荐下一题")
        next_scenario = next_result.get("scenario") or {}
        print(f"next_scenario_id: {next_scenario.get('id')}")
        print(f"next_scenario_title: {next_scenario.get('title')}")
        current_bundle = next_result

    _print_section("步骤4 训练进度")
    progress_result = training_service.get_progress(session_id)
    _save_json_artifact(save_dir, "04_progress_result", progress_result)
    _print_json(progress_result)

    _print_section("步骤5 训练报告")
    report_result = training_service.get_report(session_id)
    _save_json_artifact(save_dir, "05_report_result", report_result)
    print(f"ending: {json.dumps(report_result.get('ending') or {}, ensure_ascii=False)}")
    print(f"summary: {json.dumps(report_result.get('summary') or {}, ensure_ascii=False)}")

    _print_section("步骤6 训练诊断")
    diagnostics_result = training_service.get_diagnostics(session_id)
    _save_json_artifact(save_dir, "06_diagnostics_result", diagnostics_result)
    print(f"diagnostics_summary: {json.dumps(diagnostics_result.get('summary') or {}, ensure_ascii=False)}")

    _print_section("步骤7 最终汇总")
    ending_payload = report_result.get("ending") or {}
    final_payload = {
        "session_id": session_id,
        "player_profile": player_profile,
        "training_mode": args.training_mode,
        "total_rounds": len(round_results),
        "progress": progress_result,
        "report": report_result,
        "diagnostics": diagnostics_result,
    }
    _save_json_artifact(save_dir, "07_final_payload", final_payload)
    _print_json(
        {
            "session_id": session_id,
            "player_profile": player_profile,
            "training_mode": args.training_mode,
            "total_rounds": len(round_results),
            "ending_type": ending_payload.get("ending_type") or ending_payload.get("type"),
            "improvement": report_result.get("improvement"),
            "top_state_summary": _summarize_states(report_result),
        }
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    return run_local_smoke(args)


if __name__ == "__main__":
    raise SystemExit(main())
