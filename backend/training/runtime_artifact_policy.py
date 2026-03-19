"""训练运行时工件策略。

这一层负责统一管理：
1. 会话级 runtime_flags 的默认值、读取与合并
2. 运行时状态对象的构建
3. 回合 user_action 中运行时工件的写入与恢复

这样可以继续缩小 TrainingService 的职责边界，
避免运行时状态和 user_action 契约细节继续散落在服务层。
"""

from __future__ import annotations

from typing import Any, Dict, List

from training.runtime_events import RuntimeConsequenceEvent
from training.runtime_state import GameRuntimeFlags, GameRuntimeState
from training.training_outputs import (
    TrainingConsequenceEventOutput,
    TrainingRoundDecisionContextOutput,
    TrainingRuntimeStateOutput,
)

USER_ACTION_TEXT_KEY = "text"
USER_ACTION_SELECTED_OPTION_KEY = "selected_option"
USER_ACTION_DECISION_CONTEXT_KEY = "decision_context"
USER_ACTION_RUNTIME_STATE_KEY = "runtime_state"
USER_ACTION_CONSEQUENCE_EVENTS_KEY = "consequence_events"
USER_ACTION_BRANCH_HINTS_KEY = "branch_hints"


class TrainingRuntimeArtifactPolicy:
    """统一处理运行时状态与回合工件的策略。"""

    def build_default_runtime_flags(self) -> Dict[str, bool]:
        """构建稳定的默认运行时 flags。"""
        return GameRuntimeFlags().to_dict()

    def resolve_session_runtime_flags(
        self,
        session: Any,
    ) -> Dict[str, bool]:
        """统一从会话 session_meta 中恢复运行时 flags。"""
        session_meta = getattr(session, "session_meta", None)
        if not isinstance(session_meta, dict):
            return self.build_default_runtime_flags()
        return GameRuntimeFlags.from_payload(session_meta.get("runtime_flags")).to_dict()

    def merge_session_meta_runtime_flags(
        self,
        *,
        session_meta: Dict[str, Any] | None,
        runtime_flags: Dict[str, Any] | GameRuntimeFlags | None,
    ) -> Dict[str, Any]:
        """在保留其他 session_meta 字段的前提下更新 runtime_flags。"""
        normalized_meta = dict(session_meta or {})
        normalized_flags = (
            runtime_flags.to_dict()
            if isinstance(runtime_flags, GameRuntimeFlags)
            else GameRuntimeFlags.from_payload(runtime_flags).to_dict()
        )
        normalized_meta["runtime_flags"] = normalized_flags
        return normalized_meta

    def build_runtime_state(
        self,
        *,
        session: Any,
        player_profile: Dict[str, Any] | None = None,
        current_round_no: int | None = None,
        current_scene_id: str | None = None,
        k_state: Dict[str, Any] | None = None,
        s_state: Dict[str, Any] | None = None,
        runtime_flags: Dict[str, Any] | GameRuntimeFlags | None = None,
    ) -> GameRuntimeState:
        """聚合统一运行时状态，供后果引擎、接口和回放复用。"""
        return GameRuntimeState.from_session(
            session,
            round_no=current_round_no,
            current_scene_id=current_scene_id,
            k_state=k_state,
            s_state=s_state,
            player_profile=dict(player_profile or {}),
            runtime_flags=(
                runtime_flags
                if runtime_flags is not None
                else self.resolve_session_runtime_flags(session)
            ),
        )

    def build_round_user_action(
        self,
        *,
        user_input: str,
        selected_option: str | None,
        decision_context: TrainingRoundDecisionContextOutput | None,
    ) -> Dict[str, Any]:
        """统一封装回合提交时写入 user_action 的基础结构。"""
        payload = {
            USER_ACTION_TEXT_KEY: user_input,
            USER_ACTION_SELECTED_OPTION_KEY: selected_option,
        }
        if decision_context is not None:
            payload[USER_ACTION_DECISION_CONTEXT_KEY] = decision_context.to_dict()
        return payload

    def attach_runtime_artifacts_to_user_action(
        self,
        *,
        user_action: Dict[str, Any],
        runtime_state: GameRuntimeState,
        consequence_events: List[RuntimeConsequenceEvent],
        branch_hints: List[str] | None = None,
    ) -> Dict[str, Any]:
        """把运行时结果并入 user_action，便于历史回放和幂等重放。"""
        payload = dict(user_action or {})
        payload[USER_ACTION_RUNTIME_STATE_KEY] = runtime_state.to_dict()
        payload[USER_ACTION_CONSEQUENCE_EVENTS_KEY] = [item.to_dict() for item in consequence_events or []]
        if branch_hints:
            payload[USER_ACTION_BRANCH_HINTS_KEY] = [
                str(item) for item in branch_hints if str(item or "").strip()
            ]
        return payload

    def extract_round_decision_context(
        self,
        user_action: Dict[str, Any] | None,
    ) -> TrainingRoundDecisionContextOutput | None:
        """从回合 user_action 中恢复决策上下文。"""
        if not isinstance(user_action, dict):
            return None
        return TrainingRoundDecisionContextOutput.from_payload(user_action.get(USER_ACTION_DECISION_CONTEXT_KEY))

    def extract_round_runtime_state(
        self,
        user_action: Dict[str, Any] | None,
    ) -> TrainingRuntimeStateOutput | None:
        """从回合 user_action 中恢复运行时状态。"""
        if not isinstance(user_action, dict):
            return None
        return TrainingRuntimeStateOutput.from_payload(user_action.get(USER_ACTION_RUNTIME_STATE_KEY))

    def extract_round_runtime_flags(
        self,
        user_action: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        """从回合 user_action 中提取运行时 flags。"""
        runtime_state = self.extract_round_runtime_state(user_action)
        if runtime_state is None:
            return {}
        return runtime_state.to_dict().get("runtime_flags", {})

    def extract_round_consequence_events(
        self,
        user_action: Dict[str, Any] | None,
    ) -> List[TrainingConsequenceEventOutput]:
        """从回合 user_action 中恢复结构化后果事件。"""
        if not isinstance(user_action, dict):
            return []

        outputs: List[TrainingConsequenceEventOutput] = []
        for item in user_action.get(USER_ACTION_CONSEQUENCE_EVENTS_KEY) or []:
            output = TrainingConsequenceEventOutput.from_payload(item)
            if output is not None:
                outputs.append(output)
        return outputs
