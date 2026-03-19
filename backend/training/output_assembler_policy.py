"""训练输出装配策略。

这一层负责把原始 payload、行对象和运行时对象统一转换成稳定 DTO，
避免 TrainingService 持有过多“输入是什么类型、输出该怎么转”的细节。
"""

from __future__ import annotations

from typing import Any, Dict, List

from training.runtime_events import RuntimeConsequenceEvent
from training.runtime_state import GameRuntimeState
from training.training_outputs import (
    TrainingAuditEventOutput,
    TrainingConsequenceEventOutput,
    TrainingEvaluationOutput,
    TrainingKtObservationOutput,
    TrainingPlayerProfileOutput,
    TrainingRecommendationLogOutput,
    TrainingRuntimeStateOutput,
    TrainingScenarioOutput,
)


class TrainingOutputAssemblerPolicy:
    """统一负责训练域对外 DTO 的装配。"""

    def build_scenario_output(self, payload: Dict[str, Any] | None) -> TrainingScenarioOutput | None:
        """把原始场景字典转换成稳定场景 DTO。"""
        return TrainingScenarioOutput.from_payload(payload)

    def build_scenario_output_list(
        self,
        payloads: List[Dict[str, Any]] | None,
    ) -> List[TrainingScenarioOutput] | None:
        """批量转换候选场景列表，并自动过滤无效项。"""
        if payloads is None:
            return None

        outputs: List[TrainingScenarioOutput] = []
        for item in payloads:
            output = self.build_scenario_output(item)
            if output is not None:
                outputs.append(output)
        return outputs

    def build_player_profile_output(
        self,
        payload: Dict[str, Any] | None,
    ) -> TrainingPlayerProfileOutput | None:
        """把玩家档案字典转换成稳定输出 DTO。"""
        return TrainingPlayerProfileOutput.from_payload(payload)

    def build_evaluation_output(self, payload: Dict[str, Any] | None) -> TrainingEvaluationOutput:
        """把原始评估字典转换成稳定评估 DTO。"""
        return TrainingEvaluationOutput.from_payload(payload)

    def build_runtime_state_output(
        self,
        runtime_state: GameRuntimeState | Dict[str, Any] | None,
    ) -> TrainingRuntimeStateOutput | None:
        """把运行时状态转换成稳定输出 DTO。"""
        if runtime_state is None:
            return None
        payload = runtime_state.to_dict() if isinstance(runtime_state, GameRuntimeState) else runtime_state
        return TrainingRuntimeStateOutput.from_payload(payload)

    def build_consequence_event_output(
        self,
        payload: RuntimeConsequenceEvent | Dict[str, Any] | None,
    ) -> TrainingConsequenceEventOutput | None:
        """把单个运行时后果事件转换成稳定 DTO。"""
        if payload is None:
            return None
        event_payload = payload.to_dict() if isinstance(payload, RuntimeConsequenceEvent) else payload
        return TrainingConsequenceEventOutput.from_payload(event_payload)

    def build_consequence_event_outputs(
        self,
        payloads: List[RuntimeConsequenceEvent | Dict[str, Any]] | None,
    ) -> List[TrainingConsequenceEventOutput]:
        """批量转换运行时后果事件。"""
        outputs: List[TrainingConsequenceEventOutput] = []
        for item in payloads or []:
            output = self.build_consequence_event_output(item)
            if output is not None:
                outputs.append(output)
        return outputs

    def build_kt_observation_output(self, row: Any) -> TrainingKtObservationOutput | None:
        """把 KT 观测记录转换成稳定输出 DTO。"""
        if row is None:
            return None
        return TrainingKtObservationOutput.from_payload(
            {
                "round_no": getattr(row, "round_no", None),
                "scenario_id": getattr(row, "scenario_id", None),
                "scenario_title": getattr(row, "scenario_title", ""),
                "training_mode": getattr(row, "training_mode", "guided"),
                "primary_skill_code": getattr(row, "primary_skill_code", None),
                "primary_risk_flag": getattr(row, "primary_risk_flag", None),
                "is_high_risk": getattr(row, "is_high_risk", False),
                "target_skills": getattr(row, "target_skills", []),
                "weak_skills_before": getattr(row, "weak_skills_before", []),
                "risk_flags": getattr(row, "risk_flags", []),
                "focus_tags": getattr(row, "focus_tags", []),
                "evidence": getattr(row, "evidence", []),
                "skill_observations": getattr(row, "skill_observations", []),
                "state_observations": getattr(row, "state_observations", []),
                "observation_summary": getattr(row, "observation_summary", ""),
            }
        )

    def build_kt_observation_outputs(
        self,
        rows: List[Any],
    ) -> List[TrainingKtObservationOutput]:
        """批量转换 KT 观测，统一过滤空值。"""
        outputs: List[TrainingKtObservationOutput] = []
        for row in rows:
            output = self.build_kt_observation_output(row)
            if output is not None:
                outputs.append(output)
        return outputs

    def build_recommendation_log_output(self, row: Any) -> TrainingRecommendationLogOutput | None:
        """把推荐日志记录转换成稳定输出 DTO。"""
        if row is None:
            return None
        return TrainingRecommendationLogOutput.from_payload(
            {
                "round_no": getattr(row, "round_no", None),
                "training_mode": getattr(row, "training_mode", "guided"),
                "selection_source": getattr(row, "selection_source", None),
                "recommended_scenario_id": getattr(row, "recommended_scenario_id", None),
                "selected_scenario_id": getattr(row, "selected_scenario_id", None),
                "candidate_pool": getattr(row, "candidate_pool", []),
                "recommended_recommendation": getattr(row, "recommended_recommendation", {}),
                "selected_recommendation": getattr(row, "selected_recommendation", {}),
                "decision_context": getattr(row, "decision_context", {}),
            }
        )

    def build_recommendation_log_outputs(
        self,
        rows: List[Any],
    ) -> List[TrainingRecommendationLogOutput]:
        """批量转换推荐日志，统一过滤空值。"""
        outputs: List[TrainingRecommendationLogOutput] = []
        for row in rows:
            output = self.build_recommendation_log_output(row)
            if output is not None:
                outputs.append(output)
        return outputs

    def build_audit_event_output(self, row: Any) -> TrainingAuditEventOutput | None:
        """把审计事件记录转换成稳定输出 DTO。"""
        if row is None:
            return None
        return TrainingAuditEventOutput.from_payload(
            {
                "event_type": getattr(row, "event_type", None),
                "round_no": getattr(row, "round_no", None),
                "payload": getattr(row, "payload", {}),
                "timestamp": getattr(row, "created_at", None).isoformat() if getattr(row, "created_at", None) else None,
            }
        )

    def build_audit_event_outputs(
        self,
        rows: List[Any],
    ) -> List[TrainingAuditEventOutput]:
        """批量转换审计事件，统一过滤空值。"""
        outputs: List[TrainingAuditEventOutput] = []
        for row in rows:
            output = self.build_audit_event_output(row)
            if output is not None:
                outputs.append(output)
        return outputs
