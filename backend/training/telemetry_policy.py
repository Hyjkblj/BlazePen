"""训练观测与审计策略。

这一层负责把服务编排中产生的上下文，转换成稳定的推荐日志、
审计事件和 KT 结构化观测，避免这些字典结构继续散落在 service 中。
"""

from __future__ import annotations

from typing import Any, Dict, List

from training.constants import DEFAULT_K_STATE, DEFAULT_S_STATE, SKILL_CODES
from training.contracts import (
    KtObservationPayload,
    RoundEvaluationPayload,
    RoundMetricObservationPayload,
    ScenarioRecommendationLogPayload,
    TrainingAuditEventPayload,
)
from training.phase_policy import TrainingPhasePolicy, TrainingPhaseSnapshot
from training.runtime_events import RuntimeConsequenceEvent
from training.runtime_state import GameRuntimeFlags


class TrainingTelemetryPolicy:
    """训练观测策略：统一生成推荐日志、审计事件和 KT 观测。"""

    def __init__(self, phase_policy: TrainingPhasePolicy | None = None):
        # 阶段切换判断统一交给阶段策略，避免同一条规则在多个策略里重复维护。
        self.phase_policy = phase_policy or TrainingPhasePolicy()

    def build_session_initialized_audit_event(
        self,
        training_mode: str,
        scenario_bank_version: str,
        scenario_count: int,
        phase_snapshot: TrainingPhaseSnapshot | None = None,
    ) -> TrainingAuditEventPayload:
        """生成训练初始化事件。"""
        payload = {
            "training_mode": training_mode,
            "scenario_bank_version": scenario_bank_version,
            "scenario_count": int(scenario_count),
        }
        if phase_snapshot is not None:
            payload["phase"] = phase_snapshot.to_dict()

        return TrainingAuditEventPayload(
            event_type="session_initialized",
            round_no=0,
            payload=payload,
        )

    def build_recommendation_log(
        self,
        training_mode: str,
        decision_context: Any,
    ) -> ScenarioRecommendationLogPayload | None:
        """把决策上下文转换成结构化推荐日志。"""
        if decision_context is None:
            return None

        return ScenarioRecommendationLogPayload.from_raw(
            {
                "training_mode": training_mode,
                "selection_source": getattr(decision_context, "selection_source", None),
                "recommended_scenario_id": getattr(decision_context, "recommended_scenario_id", None),
                "selected_scenario_id": getattr(decision_context, "selected_scenario_id", None),
                "candidate_pool": [
                    item.to_dict()
                    for item in getattr(decision_context, "candidate_pool", []) or []
                ],
                "recommended_recommendation": (
                    decision_context.recommended_recommendation.to_dict()
                    if getattr(decision_context, "recommended_recommendation", None) is not None
                    else {}
                ),
                "selected_recommendation": (
                    decision_context.selected_recommendation.to_dict()
                    if getattr(decision_context, "selected_recommendation", None) is not None
                    else {}
                ),
                "decision_context": decision_context.to_dict(),
            }
        )

    def build_round_audit_events(
        self,
        training_mode: str,
        round_no: int,
        scenario_id: str,
        selected_option: str | None,
        evaluation_payload: Dict[str, Any],
        decision_context: Any,
        phase_snapshot: TrainingPhaseSnapshot | None,
        previous_phase_snapshot: TrainingPhaseSnapshot | None,
        is_completed: bool,
        ending_payload: Dict[str, Any] | None,
    ) -> List[TrainingAuditEventPayload]:
        """生成回合提交相关的审计事件集合。"""
        normalized_eval = RoundEvaluationPayload.from_raw(evaluation_payload).to_dict()
        round_submitted_payload = {
            "training_mode": training_mode,
            "scenario_id": scenario_id,
            "selected_option": selected_option,
            "selection_source": getattr(decision_context, "selection_source", None)
            if decision_context is not None
            else None,
            "risk_flags": list(normalized_eval.get("risk_flags", [])),
            "confidence": float(normalized_eval.get("confidence", 0.5) or 0.5),
            "is_completed": bool(is_completed),
        }
        if phase_snapshot is not None:
            round_submitted_payload["phase"] = phase_snapshot.to_dict()

        events = [
            TrainingAuditEventPayload(
                event_type="round_submitted",
                round_no=round_no,
                payload=round_submitted_payload,
            )
        ]
        if self.phase_policy.has_phase_transition(previous_phase_snapshot, phase_snapshot):
            events.append(
                TrainingAuditEventPayload(
                    event_type="phase_transition",
                    round_no=round_no,
                    payload={
                        "training_mode": training_mode,
                        "scenario_id": scenario_id,
                        "from_phase": previous_phase_snapshot.to_dict() if previous_phase_snapshot is not None else None,
                        "to_phase": phase_snapshot.to_dict() if phase_snapshot is not None else None,
                    },
                )
            )
        if is_completed and ending_payload is not None:
            events.append(
                TrainingAuditEventPayload(
                    event_type="session_completed",
                    round_no=round_no,
                    payload={
                        "training_mode": training_mode,
                        "ending_type": ending_payload.get("type"),
                        "ending_score": ending_payload.get("score"),
                        "selected_scenario_id": scenario_id,
                    },
                )
            )
        return events

    def build_runtime_consequence_audit_events(
        self,
        *,
        round_no: int,
        training_mode: str,
        runtime_flags: GameRuntimeFlags | Dict[str, Any],
        consequence_events: List[RuntimeConsequenceEvent],
        branch_hints: List[str] | None = None,
    ) -> List[TrainingAuditEventPayload]:
        """把运行时后果事件转换成审计事件。

        这样报告、诊断和排障都可以直接复用同一份结构化事实，
        不需要再从 user_action 或文案里反推世界状态变化。
        """
        normalized_flags = (
            runtime_flags.to_dict()
            if isinstance(runtime_flags, GameRuntimeFlags)
            else GameRuntimeFlags.from_payload(runtime_flags).to_dict()
        )

        audit_events: List[TrainingAuditEventPayload] = []
        for event in consequence_events or []:
            payload = event.to_dict()
            payload["training_mode"] = training_mode
            payload["runtime_flags"] = dict(normalized_flags)
            payload["branch_hints"] = [str(item) for item in branch_hints or [] if str(item or "").strip()]
            audit_events.append(
                TrainingAuditEventPayload(
                    event_type=event.event_type,
                    round_no=round_no,
                    payload=payload,
                )
            )
        return audit_events

    def build_kt_observation(
        self,
        training_mode: str,
        round_no: int,
        scenario_payload: Dict[str, Any] | None,
        k_before: Dict[str, float],
        k_after: Dict[str, float],
        s_before: Dict[str, float],
        s_after: Dict[str, float],
        evaluation_payload: Dict[str, Any],
    ) -> KtObservationPayload | None:
        """构建每轮的结构化 KT 观测，供后续复盘、诊断和分析使用。"""
        normalized_eval = RoundEvaluationPayload.from_raw(evaluation_payload).to_dict()
        scenario_source = dict(scenario_payload or {})
        scenario_id = str(scenario_source.get("id") or "").strip()
        if not scenario_id:
            return None

        scenario_title = str(scenario_source.get("title") or scenario_id)
        target_skills = [
            str(item)
            for item in scenario_source.get("target_skills", []) or []
            if str(item or "").strip()
        ]
        weak_skills_before = self._resolve_weak_skill_codes(k_before)
        skill_observations = self._build_skill_observations(
            target_skills=target_skills,
            weak_skills_before=weak_skills_before,
            k_before=k_before,
            k_after=k_after,
            evaluation_payload=normalized_eval,
        )
        state_observations = self._build_state_observations(
            s_before=s_before,
            s_after=s_after,
            evaluation_payload=normalized_eval,
        )
        risk_flags = list(normalized_eval.get("risk_flags", []))
        primary_skill_code = self._resolve_primary_skill_code(target_skills, skill_observations, weak_skills_before)
        primary_risk_flag = risk_flags[0] if risk_flags else None
        focus_tags = self._resolve_focus_tags(
            target_skills=target_skills,
            scenario_risk_tags=scenario_source.get("risk_tags", []),
            risk_flags=risk_flags,
        )
        observation_summary = self._build_observation_summary(
            round_no=round_no,
            scenario_title=scenario_title,
            primary_skill_code=primary_skill_code,
            risk_flags=risk_flags,
            skill_observations=skill_observations,
        )

        return KtObservationPayload.from_raw(
            {
                "training_mode": training_mode,
                "scenario_id": scenario_id,
                "scenario_title": scenario_title,
                "primary_skill_code": primary_skill_code,
                "primary_risk_flag": primary_risk_flag,
                "is_high_risk": bool(risk_flags),
                "target_skills": target_skills,
                "weak_skills_before": weak_skills_before,
                "risk_flags": risk_flags,
                "focus_tags": focus_tags,
                "evidence": normalized_eval.get("evidence", []),
                "skill_observations": [item.to_dict() for item in skill_observations],
                "state_observations": [item.to_dict() for item in state_observations],
                "observation_summary": observation_summary,
            }
        )

    def _resolve_weak_skill_codes(self, k_before: Dict[str, float], limit: int = 3) -> List[str]:
        """找出当前最薄弱的几个能力点。"""
        ordered_codes = sorted(
            SKILL_CODES,
            key=lambda code: (float(k_before.get(code, DEFAULT_K_STATE.get(code, 0.0))), code),
        )
        return [code for code in ordered_codes[:limit]]

    def _build_skill_observations(
        self,
        target_skills: List[str],
        weak_skills_before: List[str],
        k_before: Dict[str, float],
        k_after: Dict[str, float],
        evaluation_payload: Dict[str, Any],
        limit: int = 4,
    ) -> List[RoundMetricObservationPayload]:
        """提炼本轮最值得记录的能力变化。"""
        skill_delta = dict(evaluation_payload.get("skill_delta", {}) or {})
        prioritized_codes: List[str] = []

        ordered_target_skills = sorted(
            [code for code in target_skills if str(code or "").strip()],
            key=lambda code: (float(k_before.get(code, DEFAULT_K_STATE.get(code, 0.0))), str(code)),
        )
        for code in ordered_target_skills:
            if code not in prioritized_codes:
                prioritized_codes.append(code)

        delta_codes = [
            code
            for code, _ in sorted(
                skill_delta.items(),
                key=lambda item: (-abs(float(item[1] or 0.0)), str(item[0])),
            )
            if abs(float(skill_delta.get(code, 0.0) or 0.0)) > 0
        ]
        for code in delta_codes:
            code_text = str(code or "").strip()
            if code_text and code_text not in prioritized_codes:
                prioritized_codes.append(code_text)

        for code in weak_skills_before:
            if code not in prioritized_codes:
                prioritized_codes.append(code)

        observations: List[RoundMetricObservationPayload] = []
        for code in prioritized_codes[:limit]:
            observations.append(
                RoundMetricObservationPayload(
                    code=code,
                    before=round(float(k_before.get(code, DEFAULT_K_STATE.get(code, 0.0))), 4),
                    delta=round(float(skill_delta.get(code, 0.0) or 0.0), 4),
                    after=round(float(k_after.get(code, DEFAULT_K_STATE.get(code, 0.0))), 4),
                    is_target=code in target_skills,
                )
            )
        return observations

    def _build_state_observations(
        self,
        s_before: Dict[str, float],
        s_after: Dict[str, float],
        evaluation_payload: Dict[str, Any],
        limit: int = 3,
    ) -> List[RoundMetricObservationPayload]:
        """提炼本轮最显著的剧情状态变化。"""
        s_delta = dict(evaluation_payload.get("s_delta", {}) or {})
        ordered_codes = [
            code
            for code, _ in sorted(
                s_delta.items(),
                key=lambda item: (-abs(float(item[1] or 0.0)), str(item[0])),
            )
            if abs(float(s_delta.get(code, 0.0) or 0.0)) > 0
        ]

        observations: List[RoundMetricObservationPayload] = []
        for code in ordered_codes[:limit]:
            observations.append(
                RoundMetricObservationPayload(
                    code=str(code),
                    before=round(float(s_before.get(code, DEFAULT_S_STATE.get(code, 0.0))), 4),
                    delta=round(float(s_delta.get(code, 0.0) or 0.0), 4),
                    after=round(float(s_after.get(code, DEFAULT_S_STATE.get(code, 0.0))), 4),
                    is_target=False,
                )
            )
        return observations

    def _resolve_primary_skill_code(
        self,
        target_skills: List[str],
        skill_observations: List[RoundMetricObservationPayload],
        weak_skills_before: List[str],
    ) -> str | None:
        """确定本轮最值得追踪的主能力标签。"""
        if skill_observations:
            return skill_observations[0].code
        if target_skills:
            return target_skills[0]
        if weak_skills_before:
            return weak_skills_before[0]
        return None

    def _resolve_focus_tags(
        self,
        target_skills: List[str],
        scenario_risk_tags: List[Any] | None,
        risk_flags: List[str],
        limit: int = 8,
    ) -> List[str]:
        """收口后续分析最常用的关注标签。"""
        tags: List[str] = []
        for item in list(target_skills) + list(scenario_risk_tags or []) + list(risk_flags):
            text = str(item or "").strip()
            if not text or text in tags:
                continue
            tags.append(text)
            if len(tags) >= limit:
                break
        return tags

    def _build_observation_summary(
        self,
        round_no: int,
        scenario_title: str,
        primary_skill_code: str | None,
        risk_flags: List[str],
        skill_observations: List[RoundMetricObservationPayload],
    ) -> str:
        """生成便于人工巡检的简短摘要。"""
        summary_parts = [f"第{round_no}轮场景《{scenario_title}》"]
        if primary_skill_code:
            summary_parts.append(f"重点关注 {primary_skill_code}")
        if risk_flags:
            summary_parts.append(f"风险标记 {', '.join(risk_flags[:2])}")

        delta_texts: List[str] = []
        for item in skill_observations:
            if abs(float(item.delta)) <= 0:
                continue
            sign = "+" if item.delta > 0 else ""
            delta_texts.append(f"{item.code}{sign}{item.delta:.4f}")
            if len(delta_texts) >= 2:
                break
        if delta_texts:
            summary_parts.append(f"能力变化 {'、'.join(delta_texts)}")

        return "；".join(summary_parts)
