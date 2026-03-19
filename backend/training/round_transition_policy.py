"""训练回合状态推进策略。

这一层负责把“玩家提交一次选择”解释成稳定的运行时推进结果，包括：
1. 统一构建基础 user_action
2. 统一归一化评估结果
3. 更新 K/S 状态
4. 驱动运行时后果引擎
5. 合并会话级 runtime_flags
6. 把运行时工件重新写回 user_action

这样可以把 TrainingService 中最厚的一段“状态推进流水线”抽出来，
让服务层继续回到业务编排职责。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from training.constants import DEFAULT_K_STATE, DEFAULT_S_STATE, SKILL_CODES
from training.consequence_engine import ConsequenceEngine, ConsequenceResult
from training.contracts import RoundEvaluationPayload
from training.runtime_artifact_policy import TrainingRuntimeArtifactPolicy
from training.runtime_state import GameRuntimeState
from training.training_outputs import TrainingRoundDecisionContextOutput


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """统一裁剪数值区间，避免状态推进后出现越界。"""
    return max(lower, min(upper, float(value)))


@dataclass(slots=True)
class TrainingRoundTransitionArtifacts:
    """单回合状态推进后的标准工件集合。"""

    evaluation_payload: Dict[str, Any]
    updated_k_state: Dict[str, float]
    updated_s_state: Dict[str, float]
    runtime_state: GameRuntimeState
    consequence_result: ConsequenceResult
    updated_session_meta: Dict[str, Any]
    user_action: Dict[str, Any]


class TrainingRoundTransitionPolicy:
    """统一处理单回合的评估、状态推进和运行时工件回写。"""

    def __init__(
        self,
        runtime_artifact_policy: TrainingRuntimeArtifactPolicy | None = None,
    ):
        self.runtime_artifact_policy = runtime_artifact_policy or TrainingRuntimeArtifactPolicy()

    def build_round_transition_artifacts(
        self,
        *,
        session: Any,
        evaluator: Any,
        consequence_engine: ConsequenceEngine,
        round_no: int,
        scenario_id: str,
        user_input: str,
        selected_option: str | None,
        decision_context: TrainingRoundDecisionContextOutput | None,
        k_before: Dict[str, float],
        s_before: Dict[str, float],
        recent_risk_rounds: List[List[str]] | None,
        scenario_payload: Dict[str, Any] | None,
    ) -> TrainingRoundTransitionArtifacts:
        """构建单回合推进后需要落库和回包的核心工件。"""
        user_action = self.runtime_artifact_policy.build_round_user_action(
            user_input=user_input,
            selected_option=selected_option,
            decision_context=decision_context,
        )

        evaluation_payload = RoundEvaluationPayload.from_raw(
            evaluator.evaluate_round(
                user_input=user_input,
                scenario_id=scenario_id,
                round_no=round_no,
                k_before=k_before,
                s_before=s_before,
            )
        ).to_dict()

        updated_k_state = self._update_k(k_before, evaluation_payload.get("skill_delta"))
        updated_s_state = self._update_s(s_before, evaluation_payload.get("s_delta"))
        runtime_state = self.runtime_artifact_policy.build_runtime_state(
            session=session,
            current_round_no=round_no,
            current_scene_id=scenario_id,
            k_state=updated_k_state,
            s_state=updated_s_state,
        )
        consequence_result = consequence_engine.apply(
            runtime_state=runtime_state,
            evaluation_payload=evaluation_payload,
            round_no=round_no,
            scenario_payload=scenario_payload,
            selected_option=selected_option,
            recent_risk_rounds=recent_risk_rounds,
        )
        runtime_state = consequence_result.runtime_state
        updated_session_meta = self.runtime_artifact_policy.merge_session_meta_runtime_flags(
            session_meta=getattr(session, "session_meta", None),
            runtime_flags=runtime_state.runtime_flags.to_dict(),
        )
        user_action = self.runtime_artifact_policy.attach_runtime_artifacts_to_user_action(
            user_action=user_action,
            runtime_state=runtime_state,
            consequence_events=consequence_result.consequence_events,
            branch_hints=consequence_result.branch_hints,
        )

        return TrainingRoundTransitionArtifacts(
            evaluation_payload=evaluation_payload,
            updated_k_state=updated_k_state,
            updated_s_state=updated_s_state,
            runtime_state=runtime_state,
            consequence_result=consequence_result,
            updated_session_meta=updated_session_meta,
            user_action=user_action,
        )

    def _update_k(
        self,
        k_state: Dict[str, float],
        skill_delta: Dict[str, Any] | None,
    ) -> Dict[str, float]:
        """统一更新 K 状态，避免服务层重复维护同一套公式。"""
        normalized_delta = skill_delta if isinstance(skill_delta, dict) else {}
        updated: Dict[str, float] = {}
        for code in SKILL_CODES:
            updated[code] = round(
                _clamp(float(k_state.get(code, DEFAULT_K_STATE[code])) + float(normalized_delta.get(code, 0.0))),
                4,
            )
        return updated

    def _update_s(
        self,
        s_state: Dict[str, float],
        s_delta: Dict[str, Any] | None,
    ) -> Dict[str, float]:
        """统一更新 S 状态，避免服务层重复维护同一套公式。"""
        normalized_delta = s_delta if isinstance(s_delta, dict) else {}
        updated: Dict[str, float] = {}
        for key in DEFAULT_S_STATE.keys():
            updated[key] = round(
                _clamp(float(s_state.get(key, DEFAULT_S_STATE[key])) + float(normalized_delta.get(key, 0.0))),
                4,
            )
        return updated
