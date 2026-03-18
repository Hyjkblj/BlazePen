"""训练运行时后果引擎。

这一层不负责改 K/S 评分算法，只负责把已经算出的评估结果
解释成世界后果、运行时 flags 和可回放事件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from training.constants import (
    TRAINING_ENDING_FAIL_PUBLIC_PANIC,
    TRAINING_ENDING_FAIL_SOURCE_SAFETY,
    TRAINING_RISK_FLAG_SOURCE_EXPOSURE,
    TRAINING_RISK_FLAG_UNVERIFIED_PUBLISH,
)
from training.contracts import RoundEvaluationPayload
from training.runtime_events import (
    EVENT_EDITOR_LOCKED,
    EVENT_EDITOR_TRUST_RECOVERED,
    EVENT_HIGH_RISK_PATH,
    EVENT_PUBLIC_PANIC_TRIGGERED,
    EVENT_SOURCE_EXPOSED,
    EVENT_STABILITY_RESTORED,
    RuntimeConsequenceEvent,
)
from training.runtime_state import GameRuntimeFlags, GameRuntimeState


def _normalize_risk_rounds(risk_rounds: List[List[str]] | None) -> List[List[str]]:
    """统一最近风险历史结构，避免服务层传入脏数据后规则失真。"""
    normalized_rounds: List[List[str]] = []
    for round_flags in risk_rounds or []:
        if not isinstance(round_flags, list):
            continue
        normalized_rounds.append(
            [str(flag) for flag in round_flags if str(flag or "").strip()]
        )
    return normalized_rounds


@dataclass(slots=True)
class ConsequenceResult:
    """运行时后果计算结果。"""

    runtime_state: GameRuntimeState
    triggered_flags: List[str] = field(default_factory=list)
    cleared_flags: List[str] = field(default_factory=list)
    consequence_events: List[RuntimeConsequenceEvent] = field(default_factory=list)
    branch_hints: List[str] = field(default_factory=list)


class ConsequenceEngine:
    """根据风险标签和状态阈值生成世界后果。"""

    def __init__(
        self,
        *,
        public_panic_trigger_threshold: float | None = None,
        public_panic_recover_threshold: float = 0.45,
        source_exposed_threshold: float | None = None,
        editor_lock_threshold: float = 0.35,
        editor_recover_threshold: float = 0.55,
        consecutive_high_risk_threshold: int = 2,
    ):
        # 直接复用现有结局阈值，避免“运行时”和“结局”两套口径分裂。
        self.public_panic_trigger_threshold = float(
            public_panic_trigger_threshold
            if public_panic_trigger_threshold is not None
            else TRAINING_ENDING_FAIL_PUBLIC_PANIC
        )
        self.public_panic_recover_threshold = float(public_panic_recover_threshold)
        self.source_exposed_threshold = float(
            source_exposed_threshold
            if source_exposed_threshold is not None
            else TRAINING_ENDING_FAIL_SOURCE_SAFETY
        )
        self.editor_lock_threshold = float(editor_lock_threshold)
        self.editor_recover_threshold = float(editor_recover_threshold)
        self.consecutive_high_risk_threshold = max(int(consecutive_high_risk_threshold), 1)

    def apply(
        self,
        *,
        runtime_state: GameRuntimeState,
        evaluation_payload: Dict[str, Any],
        round_no: int,
        scenario_payload: Dict[str, Any] | None = None,
        selected_option: str | None = None,
        recent_risk_rounds: List[List[str]] | None = None,
    ) -> ConsequenceResult:
        """把本轮评估结果解释成世界后果。"""
        normalized_eval = RoundEvaluationPayload.from_raw(evaluation_payload).to_dict()
        risk_flags = {str(flag) for flag in normalized_eval.get("risk_flags", []) if str(flag or "").strip()}
        previous_flags = GameRuntimeFlags.from_payload(runtime_state.runtime_flags.to_dict())
        next_flags = GameRuntimeFlags.from_payload(runtime_state.runtime_flags.to_dict())
        normalized_risk_rounds = _normalize_risk_rounds(recent_risk_rounds)

        current_public_panic = float(runtime_state.s_state.get("public_panic", 0.0) or 0.0)
        current_source_safety = float(runtime_state.s_state.get("source_safety", 0.0) or 0.0)
        current_editor_trust = float(runtime_state.s_state.get("editor_trust", 0.0) or 0.0)
        is_current_round_high_risk = bool(risk_flags)

        # 来源暴露属于高严重度后果，第一阶段设计为一旦触发就保留。
        if TRAINING_RISK_FLAG_SOURCE_EXPOSURE in risk_flags or current_source_safety <= self.source_exposed_threshold:
            next_flags.source_exposed = True

        # 公众恐慌允许恢复，便于后续补救分支和纠偏训练。
        if TRAINING_RISK_FLAG_UNVERIFIED_PUBLISH in risk_flags or current_public_panic >= self.public_panic_trigger_threshold:
            next_flags.panic_triggered = True
        elif current_public_panic <= self.public_panic_recover_threshold:
            next_flags.panic_triggered = False

        # 编辑部锁定也允许恢复，为后续“重建信任”分支预留空间。
        if current_editor_trust <= self.editor_lock_threshold:
            next_flags.editor_locked = True
        elif current_editor_trust >= self.editor_recover_threshold and not is_current_round_high_risk:
            next_flags.editor_locked = False

        recent_risk_window = normalized_risk_rounds[-max(self.consecutive_high_risk_threshold - 1, 0):]
        recent_high_risk_count = sum(1 for item in recent_risk_window if item)
        if is_current_round_high_risk and recent_high_risk_count + 1 >= self.consecutive_high_risk_threshold:
            next_flags.high_risk_path = True
        elif not is_current_round_high_risk and recent_high_risk_count == 0:
            next_flags.high_risk_path = False

        updated_runtime_state = GameRuntimeState(
            session_id=runtime_state.session_id,
            current_round_no=int(round_no),
            current_scene_id=runtime_state.current_scene_id,
            k_state=dict(runtime_state.k_state),
            s_state=dict(runtime_state.s_state),
            player_profile=dict(runtime_state.player_profile),
            runtime_flags=next_flags,
            state_bar=runtime_state.state_bar,
        )

        consequence_events = self._build_consequence_events(
            previous_flags=previous_flags,
            current_flags=next_flags,
            runtime_state=updated_runtime_state,
            round_no=round_no,
            scenario_payload=scenario_payload,
            selected_option=selected_option,
        )
        branch_hints = self._build_branch_hints(next_flags)

        return ConsequenceResult(
            runtime_state=updated_runtime_state,
            triggered_flags=self._resolve_flag_diff(previous_flags, next_flags, expect_value=True),
            cleared_flags=self._resolve_flag_diff(previous_flags, next_flags, expect_value=False),
            consequence_events=consequence_events,
            branch_hints=branch_hints,
        )

    def _build_consequence_events(
        self,
        *,
        previous_flags: GameRuntimeFlags,
        current_flags: GameRuntimeFlags,
        runtime_state: GameRuntimeState,
        round_no: int,
        scenario_payload: Dict[str, Any] | None,
        selected_option: str | None,
    ) -> List[RuntimeConsequenceEvent]:
        """仅在 flag 发生变化时生成事件，避免历史回放里出现重复噪音。"""
        scenario_id = str((scenario_payload or {}).get("id") or runtime_state.current_scene_id or "").strip()
        scenario_title = str((scenario_payload or {}).get("title") or scenario_id or "当前场景")
        common_payload = {
            "scenario_id": scenario_id,
            "scenario_title": scenario_title,
            "selected_option": selected_option,
            "runtime_flags": current_flags.to_dict(),
        }

        events: List[RuntimeConsequenceEvent] = []
        if not previous_flags.source_exposed and current_flags.source_exposed:
            events.append(
                RuntimeConsequenceEvent(
                    event_type=EVENT_SOURCE_EXPOSED,
                    label="来源暴露",
                    summary=f"{scenario_title}触发了来源保护红线，系统已标记来源暴露风险路径。",
                    severity="high",
                    round_no=round_no,
                    related_flag="source_exposed",
                    state_bar=runtime_state.state_bar,
                    payload=dict(common_payload),
                )
            )
        if not previous_flags.panic_triggered and current_flags.panic_triggered:
            events.append(
                RuntimeConsequenceEvent(
                    event_type=EVENT_PUBLIC_PANIC_TRIGGERED,
                    label="公众恐慌上升",
                    summary=f"{scenario_title}引发了公众稳定度下滑，后续将优先进入风险控制导向。",
                    severity="high",
                    round_no=round_no,
                    related_flag="panic_triggered",
                    state_bar=runtime_state.state_bar,
                    payload=dict(common_payload),
                )
            )
        if previous_flags.panic_triggered and not current_flags.panic_triggered:
            events.append(
                RuntimeConsequenceEvent(
                    event_type=EVENT_STABILITY_RESTORED,
                    label="局势回稳",
                    summary=f"{scenario_title}后，群众稳定度已恢复到可控区间。",
                    severity="low",
                    round_no=round_no,
                    related_flag="panic_triggered",
                    state_bar=runtime_state.state_bar,
                    payload=dict(common_payload),
                )
            )
        if not previous_flags.editor_locked and current_flags.editor_locked:
            events.append(
                RuntimeConsequenceEvent(
                    event_type=EVENT_EDITOR_LOCKED,
                    label="编辑部警戒",
                    summary=f"{scenario_title}后，编辑部信任已降到警戒线，后续将更重视纠偏与审稿。",
                    severity="medium",
                    round_no=round_no,
                    related_flag="editor_locked",
                    state_bar=runtime_state.state_bar,
                    payload=dict(common_payload),
                )
            )
        if previous_flags.editor_locked and not current_flags.editor_locked:
            events.append(
                RuntimeConsequenceEvent(
                    event_type=EVENT_EDITOR_TRUST_RECOVERED,
                    label="编辑部信任恢复",
                    summary=f"{scenario_title}后，编辑部信任回升，限制状态已解除。",
                    severity="low",
                    round_no=round_no,
                    related_flag="editor_locked",
                    state_bar=runtime_state.state_bar,
                    payload=dict(common_payload),
                )
            )
        if not previous_flags.high_risk_path and current_flags.high_risk_path:
            events.append(
                RuntimeConsequenceEvent(
                    event_type=EVENT_HIGH_RISK_PATH,
                    label="进入高风险路径",
                    summary=f"{scenario_title}使当前会话进入连续高风险路径，后续应优先处理补救与止损。",
                    severity="medium",
                    round_no=round_no,
                    related_flag="high_risk_path",
                    state_bar=runtime_state.state_bar,
                    payload=dict(common_payload),
                )
            )
        return events

    def _resolve_flag_diff(
        self,
        previous_flags: GameRuntimeFlags,
        current_flags: GameRuntimeFlags,
        *,
        expect_value: bool,
    ) -> List[str]:
        """提取本轮新触发或新解除的 flags。"""
        changed_flags: List[str] = []
        for flag_name, current_value in current_flags.to_dict().items():
            previous_value = previous_flags.to_dict().get(flag_name, False)
            if bool(current_value) == bool(expect_value) and bool(previous_value) != bool(current_value):
                changed_flags.append(flag_name)
        return changed_flags

    def _build_branch_hints(self, runtime_flags: GameRuntimeFlags) -> List[str]:
        """根据 flags 给出轻量分支提示，为下一阶段分支解析器预留接口。"""
        branch_hints: List[str] = []
        if runtime_flags.source_exposed:
            branch_hints.append("source_protection")
        if runtime_flags.panic_triggered:
            branch_hints.append("stability_control")
        if runtime_flags.editor_locked:
            branch_hints.append("editor_recovery")
        if runtime_flags.high_risk_path:
            branch_hints.append("high_risk_remediation")
        return branch_hints
