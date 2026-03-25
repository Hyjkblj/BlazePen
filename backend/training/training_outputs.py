"""训练服务输出 DTO。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from training.contracts import RoundEvaluationPayload


def _copy_dict(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    """对输出字典做浅拷贝，避免上层意外修改内部对象。"""
    return dict(payload or {})


def _copy_dict_list(payloads: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    """对输出列表中的字典逐项拷贝，保持 DTO 对外只暴露副本。"""
    return [dict(item) for item in payloads or []]


def _to_non_negative_int(value: Any, default: int = 0) -> int:
    """把输入安全归一成非负整数，避免摘要统计因脏值直接抛错。"""
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return max(int(default), 0)


def _serialize_player_profile(
    player_profile: "TrainingPlayerProfileOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出玩家档案，兼容直接传字典的旧调用方式。"""
    if player_profile is None:
        return None
    if isinstance(player_profile, TrainingPlayerProfileOutput):
        return player_profile.to_dict()
    if isinstance(player_profile, dict):
        normalized = TrainingPlayerProfileOutput.from_payload(player_profile)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_scenario(
    scenario: "TrainingScenarioOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """兼容旧调用方直接传字典，同时统一从场景 DTO 导出稳定结构。"""
    if scenario is None:
        return None
    if isinstance(scenario, TrainingScenarioOutput):
        return scenario.to_dict()
    if isinstance(scenario, dict):
        normalized = TrainingScenarioOutput.from_payload(scenario)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_scenario_list(
    scenarios: List["TrainingScenarioOutput | Dict[str, Any]"] | None,
) -> List[Dict[str, Any]] | None:
    """批量序列化场景列表，并自动过滤无效项。"""
    if scenarios is None:
        return None

    serialized_items: List[Dict[str, Any]] = []
    for item in scenarios:
        serialized = _serialize_scenario(item)
        if serialized is not None:
            serialized_items.append(serialized)
    return serialized_items


def _serialize_evaluation(
    evaluation: "TrainingEvaluationOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """兼容旧调用方直接传评估字典，同时统一导出稳定评估结构。"""
    if evaluation is None:
        return None
    if isinstance(evaluation, TrainingEvaluationOutput):
        return evaluation.to_dict()
    if isinstance(evaluation, dict):
        return TrainingEvaluationOutput.from_payload(evaluation).to_dict()
    return None


def _serialize_decision_context(
    decision_context: "TrainingRoundDecisionContextOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """兼容旧调用方直接传字典，同时统一导出稳定决策上下文结构。"""
    if decision_context is None:
        return None
    if isinstance(decision_context, TrainingRoundDecisionContextOutput):
        return decision_context.to_dict()
    if isinstance(decision_context, dict):
        return TrainingRoundDecisionContextOutput.from_payload(decision_context).to_dict()
    return None


def _serialize_branch_transition(
    branch_transition: "TrainingBranchTransitionOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出单个分支跳转上下文。"""
    if branch_transition is None:
        return None
    if isinstance(branch_transition, TrainingBranchTransitionOutput):
        return branch_transition.to_dict()
    if isinstance(branch_transition, dict):
        normalized = TrainingBranchTransitionOutput.from_payload(branch_transition)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_branch_transition_summary(
    summary: "TrainingBranchTransitionSummaryOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出分支跳转聚合摘要。"""
    if summary is None:
        return None
    if isinstance(summary, TrainingBranchTransitionSummaryOutput):
        return summary.to_dict()
    if isinstance(summary, dict):
        normalized = TrainingBranchTransitionSummaryOutput.from_payload(summary)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_branch_transition_summary_list(
    summaries: List["TrainingBranchTransitionSummaryOutput | Dict[str, Any]"] | None,
) -> List[Dict[str, Any]]:
    """批量导出分支跳转聚合摘要列表。"""
    serialized_items: List[Dict[str, Any]] = []
    for item in summaries or []:
        serialized = _serialize_branch_transition_summary(item)
        if serialized is not None:
            serialized_items.append(serialized)
    return serialized_items


def _serialize_runtime_flags(
    runtime_flags: "TrainingRuntimeFlagsOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出运行时 flags。"""
    if runtime_flags is None:
        return None
    if isinstance(runtime_flags, TrainingRuntimeFlagsOutput):
        return runtime_flags.to_dict()
    if isinstance(runtime_flags, dict):
        normalized = TrainingRuntimeFlagsOutput.from_payload(runtime_flags)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_runtime_state_bar(
    state_bar: "TrainingRuntimeStateBarOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出状态条。"""
    if state_bar is None:
        return None
    if isinstance(state_bar, TrainingRuntimeStateBarOutput):
        return state_bar.to_dict()
    if isinstance(state_bar, dict):
        normalized = TrainingRuntimeStateBarOutput.from_payload(state_bar)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_runtime_state(
    runtime_state: "TrainingRuntimeStateOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出运行时状态。"""
    if runtime_state is None:
        return None
    if isinstance(runtime_state, TrainingRuntimeStateOutput):
        return runtime_state.to_dict()
    if isinstance(runtime_state, dict):
        normalized = TrainingRuntimeStateOutput.from_payload(runtime_state)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_consequence_event(
    event: "TrainingConsequenceEventOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出单个后果事件。"""
    if event is None:
        return None
    if isinstance(event, TrainingConsequenceEventOutput):
        return event.to_dict()
    if isinstance(event, dict):
        normalized = TrainingConsequenceEventOutput.from_payload(event)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_consequence_event_list(
    events: List["TrainingConsequenceEventOutput | Dict[str, Any]"] | None,
) -> List[Dict[str, Any]]:
    """批量导出后果事件列表。"""
    serialized_items: List[Dict[str, Any]] = []
    for item in events or []:
        serialized = _serialize_consequence_event(item)
        if serialized is not None:
            serialized_items.append(serialized)
    return serialized_items


def _serialize_kt_observation(
    observation: "TrainingKtObservationOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """兼容旧调用方直接传字典，同时统一导出 KT 观测结构。"""
    if observation is None:
        return None
    if isinstance(observation, TrainingKtObservationOutput):
        return observation.to_dict()
    if isinstance(observation, dict):
        normalized = TrainingKtObservationOutput.from_payload(observation)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_kt_observation_list(
    observations: List["TrainingKtObservationOutput | Dict[str, Any]"] | None,
) -> List[Dict[str, Any]]:
    """批量序列化 KT 观测列表，并自动过滤无效项。"""
    serialized_items: List[Dict[str, Any]] = []
    for item in observations or []:
        serialized = _serialize_kt_observation(item)
        if serialized is not None:
            serialized_items.append(serialized)
    return serialized_items


def _serialize_recommendation_log(
    log_item: "TrainingRecommendationLogOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出推荐日志结构。"""
    if log_item is None:
        return None
    if isinstance(log_item, TrainingRecommendationLogOutput):
        return log_item.to_dict()
    if isinstance(log_item, dict):
        normalized = TrainingRecommendationLogOutput.from_payload(log_item)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_recommendation_log_list(
    log_items: List["TrainingRecommendationLogOutput | Dict[str, Any]"] | None,
) -> List[Dict[str, Any]]:
    """批量序列化推荐日志列表。"""
    serialized_items: List[Dict[str, Any]] = []
    for item in log_items or []:
        serialized = _serialize_recommendation_log(item)
        if serialized is not None:
            serialized_items.append(serialized)
    return serialized_items


def _serialize_audit_event(
    event: "TrainingAuditEventOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出审计事件结构。"""
    if event is None:
        return None
    if isinstance(event, TrainingAuditEventOutput):
        return event.to_dict()
    if isinstance(event, dict):
        normalized = TrainingAuditEventOutput.from_payload(event)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_audit_event_list(
    events: List["TrainingAuditEventOutput | Dict[str, Any]"] | None,
) -> List[Dict[str, Any]]:
    """批量序列化审计事件列表。"""
    serialized_items: List[Dict[str, Any]] = []
    for item in events or []:
        serialized = _serialize_audit_event(item)
        if serialized is not None:
            serialized_items.append(serialized)
    return serialized_items


def _serialize_diagnostics_count_item(
    item: "TrainingDiagnosticsCountItemOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出诊断统计项，避免摘要层重新退化成松散字典。"""
    if item is None:
        return None
    if isinstance(item, TrainingDiagnosticsCountItemOutput):
        return item.to_dict()
    if isinstance(item, dict):
        normalized = TrainingDiagnosticsCountItemOutput.from_payload(item)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_diagnostics_count_item_list(
    items: List["TrainingDiagnosticsCountItemOutput | Dict[str, Any]"] | None,
) -> List[Dict[str, Any]]:
    """批量序列化诊断统计项，并自动过滤无效记录。"""
    serialized_items: List[Dict[str, Any]] = []
    for item in items or []:
        serialized = _serialize_diagnostics_count_item(item)
        if serialized is not None:
            serialized_items.append(serialized)
    return serialized_items


def _serialize_diagnostics_summary(
    summary: "TrainingDiagnosticsSummaryOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """兼容旧调用方直接传字典，同时导出稳定的诊断摘要结构。"""
    if summary is None:
        return None
    if isinstance(summary, TrainingDiagnosticsSummaryOutput):
        return summary.to_dict()
    if isinstance(summary, dict):
        normalized = TrainingDiagnosticsSummaryOutput.from_payload(summary)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_report_metric(
    metric: "TrainingReportMetricOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出报告中的单个指标摘要。"""
    if metric is None:
        return None
    if isinstance(metric, TrainingReportMetricOutput):
        return metric.to_dict()
    if isinstance(metric, dict):
        normalized = TrainingReportMetricOutput.from_payload(metric)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_report_metric_list(
    metrics: List["TrainingReportMetricOutput | Dict[str, Any]"] | None,
) -> List[Dict[str, Any]]:
    """批量序列化报告指标摘要列表。"""
    serialized_items: List[Dict[str, Any]] = []
    for item in metrics or []:
        serialized = _serialize_report_metric(item)
        if serialized is not None:
            serialized_items.append(serialized)
    return serialized_items


def _serialize_report_curve_point(
    point: "TrainingReportCurvePointOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出报告成长曲线点。"""
    if point is None:
        return None
    if isinstance(point, TrainingReportCurvePointOutput):
        return point.to_dict()
    if isinstance(point, dict):
        normalized = TrainingReportCurvePointOutput.from_payload(point)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_report_curve_point_list(
    points: List["TrainingReportCurvePointOutput | Dict[str, Any]"] | None,
) -> List[Dict[str, Any]]:
    """批量序列化成长曲线点。"""
    serialized_items: List[Dict[str, Any]] = []
    for item in points or []:
        serialized = _serialize_report_curve_point(item)
        if serialized is not None:
            serialized_items.append(serialized)
    return serialized_items


def _serialize_report_summary(
    summary: "TrainingReportSummaryOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """统一导出训练报告摘要。"""
    if summary is None:
        return None
    if isinstance(summary, TrainingReportSummaryOutput):
        return summary.to_dict()
    if isinstance(summary, dict):
        normalized = TrainingReportSummaryOutput.from_payload(summary)
        return normalized.to_dict() if normalized is not None else None
    return None


def _serialize_progress_anchor(
    anchor: "TrainingSessionProgressAnchorOutput | Dict[str, Any] | None",
) -> Dict[str, Any] | None:
    """Serialize the stable session progress anchor used by recovery reads."""
    if anchor is None:
        return None
    if isinstance(anchor, TrainingSessionProgressAnchorOutput):
        return anchor.to_dict()
    if isinstance(anchor, dict):
        normalized = TrainingSessionProgressAnchorOutput.from_payload(anchor)
        return normalized.to_dict() if normalized is not None else None
    return None


@dataclass(slots=True)
class TrainingPlayerProfileOutput:
    """玩家档案输出。"""

    name: Optional[str] = None
    gender: Optional[str] = None
    identity: Optional[str] = None
    age: Optional[int] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingPlayerProfileOutput | None":
        """把玩家档案字典转换成稳定 DTO，便于后续渐进扩展。"""
        if not isinstance(payload, dict):
            return None

        normalized_payload = dict(payload)
        known_keys = {"name", "gender", "identity", "age"}
        extra_fields = {
            str(key): value
            for key, value in normalized_payload.items()
            if str(key) not in known_keys and value is not None
        }

        age_value = normalized_payload.get("age")
        normalized_age: Optional[int] = None
        if age_value is not None and str(age_value).strip():
            try:
                parsed_age = int(age_value)
            except (TypeError, ValueError):
                parsed_age = None
            if parsed_age is not None and parsed_age >= 0:
                normalized_age = parsed_age

        profile = cls(
            name=str(normalized_payload.get("name")).strip() if normalized_payload.get("name") is not None else None,
            gender=(
                str(normalized_payload.get("gender")).strip()
                if normalized_payload.get("gender") is not None
                else None
            ),
            identity=(
                str(normalized_payload.get("identity")).strip()
                if normalized_payload.get("identity") is not None
                else None
            ),
            age=normalized_age,
            extra_fields=extra_fields,
        )
        if not any(
            [
                profile.name,
                profile.gender,
                profile.identity,
                profile.age is not None,
                bool(profile.extra_fields),
            ]
        ):
            return None
        return profile

    def to_dict(self) -> Dict[str, Any]:
        """导出玩家档案字典，并保留扩展字段。"""
        payload: Dict[str, Any] = {}
        if self.name:
            payload["name"] = self.name
        if self.gender:
            payload["gender"] = self.gender
        if self.identity:
            payload["identity"] = self.identity
        if self.age is not None:
            payload["age"] = self.age
        payload.update(_copy_dict(self.extra_fields))
        return payload


@dataclass(slots=True)
class TrainingScenarioOptionOutput:
    """训练场景中的单个选项输出。"""

    id: str
    label: str
    impact_hint: str = ""

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingScenarioOptionOutput | None":
        """把原始选项字典转成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        option_id = str(payload.get("id") or "").strip()
        if not option_id:
            return None

        return cls(
            id=option_id,
            label=str(payload.get("label") or option_id),
            impact_hint=str(payload.get("impact_hint") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出选项字典。"""
        return {
            "id": self.id,
            "label": self.label,
            "impact_hint": self.impact_hint,
        }


@dataclass(slots=True)
class TrainingScenarioRecommendationOutput:
    """训练场景推荐元信息输出。"""

    mode: str
    rank_score: float = 0.0
    weakness_score: float = 0.0
    state_boost_score: float = 0.0
    risk_boost_score: float = 0.0
    phase_boost_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    rank: Optional[int] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingScenarioRecommendationOutput | None":
        """把原始推荐字典转成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        mode = str(payload.get("mode") or "").strip()
        if not mode:
            return None

        rank_value = payload.get("rank")
        return cls(
            mode=mode,
            rank_score=float(payload.get("rank_score", 0.0) or 0.0),
            weakness_score=float(payload.get("weakness_score", 0.0) or 0.0),
            state_boost_score=float(payload.get("state_boost_score", 0.0) or 0.0),
            risk_boost_score=float(payload.get("risk_boost_score", 0.0) or 0.0),
            phase_boost_score=float(payload.get("phase_boost_score", 0.0) or 0.0),
            reasons=[str(item) for item in payload.get("reasons", []) if str(item or "").strip()],
            rank=int(rank_value) if rank_value is not None else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出推荐元信息字典。"""
        payload = {
            "mode": self.mode,
            "rank_score": self.rank_score,
            "weakness_score": self.weakness_score,
            "state_boost_score": self.state_boost_score,
            "risk_boost_score": self.risk_boost_score,
            "phase_boost_score": self.phase_boost_score,
            "reasons": list(self.reasons),
        }
        if self.rank is not None:
            payload["rank"] = self.rank
        return payload


@dataclass(slots=True)
class TrainingScenarioOutput:
    """训练场景输出。"""

    id: str
    title: str
    era_date: str = ""
    location: str = ""
    brief: str = ""
    mission: str = ""
    decision_focus: str = ""
    target_skills: List[str] = field(default_factory=list)
    risk_tags: List[str] = field(default_factory=list)
    options: List[TrainingScenarioOptionOutput] = field(default_factory=list)
    completion_hint: str = ""
    recommendation: Optional[TrainingScenarioRecommendationOutput] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingScenarioOutput | None":
        """把原始场景字典转成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        scenario_id = str(payload.get("id") or "").strip()
        if not scenario_id:
            return None

        # Canonical scenario summary field is `brief`.
        # Ignore legacy `briefing` input and keep output DTO canonical-only.
        canonical_brief = str(payload.get("brief") or "")

        option_items: List[TrainingScenarioOptionOutput] = []
        for option in payload.get("options", []) or []:
            option_output = TrainingScenarioOptionOutput.from_payload(option)
            if option_output is not None:
                option_items.append(option_output)

        known_keys = {
            "id",
            "title",
            "era_date",
            "location",
            "brief",
            "mission",
            "decision_focus",
            "target_skills",
            "risk_tags",
            "options",
            "completion_hint",
            "recommendation",
        }
        extra_fields = {
            str(key): value
            for key, value in payload.items()
            if key not in known_keys and str(key) != "briefing"
        }

        return cls(
            id=scenario_id,
            title=str(payload.get("title") or scenario_id),
            era_date=str(payload.get("era_date") or ""),
            location=str(payload.get("location") or ""),
            brief=canonical_brief,
            mission=str(payload.get("mission") or ""),
            decision_focus=str(payload.get("decision_focus") or ""),
            target_skills=[str(item) for item in payload.get("target_skills", []) if str(item or "").strip()],
            risk_tags=[str(item) for item in payload.get("risk_tags", []) if str(item or "").strip()],
            options=option_items,
            completion_hint=str(payload.get("completion_hint") or ""),
            recommendation=TrainingScenarioRecommendationOutput.from_payload(payload.get("recommendation")),
            extra_fields=extra_fields,
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出场景字典，并保留未识别扩展字段。"""
        payload = {
            "id": self.id,
            "title": self.title,
            "era_date": self.era_date,
            "location": self.location,
            "brief": self.brief,
            "mission": self.mission,
            "decision_focus": self.decision_focus,
            "target_skills": list(self.target_skills),
            "risk_tags": list(self.risk_tags),
            "options": [item.to_dict() for item in self.options],
            "completion_hint": self.completion_hint,
        }
        if self.recommendation is not None:
            payload["recommendation"] = self.recommendation.to_dict()
        payload.update(_copy_dict(self.extra_fields))
        return payload


@dataclass(slots=True)
class TrainingEvaluationOutput:
    """训练回合评估输出。"""

    llm_model: str
    confidence: float
    risk_flags: List[str] = field(default_factory=list)
    skill_delta: Dict[str, float] = field(default_factory=dict)
    s_delta: Dict[str, float] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    skill_scores_preview: Dict[str, float] = field(default_factory=dict)
    eval_mode: str = "rules_only"
    fallback_reason: Optional[str] = None
    calibration: Optional[Dict[str, Any]] = None
    llm_raw_text: Optional[str] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingEvaluationOutput":
        """把原始评估字典收口成稳定 DTO，并复用统一评估契约做归一化。"""
        normalized_payload = RoundEvaluationPayload.from_raw(payload).to_dict()
        known_keys = {
            "llm_model",
            "confidence",
            "risk_flags",
            "skill_delta",
            "s_delta",
            "evidence",
            "skill_scores_preview",
            "eval_mode",
            "fallback_reason",
            "calibration",
            "llm_raw_text",
        }
        extra_fields = {
            str(key): value
            for key, value in (payload or {}).items()
            if key not in known_keys
        }

        return cls(
            llm_model=str(normalized_payload.get("llm_model") or ""),
            confidence=float(normalized_payload.get("confidence", 0.5) or 0.5),
            risk_flags=[str(item) for item in normalized_payload.get("risk_flags", [])],
            skill_delta=_copy_dict(normalized_payload.get("skill_delta")),
            s_delta=_copy_dict(normalized_payload.get("s_delta")),
            evidence=[str(item) for item in normalized_payload.get("evidence", [])],
            skill_scores_preview=_copy_dict(normalized_payload.get("skill_scores_preview")),
            eval_mode=str(normalized_payload.get("eval_mode") or "rules_only"),
            fallback_reason=normalized_payload.get("fallback_reason"),
            calibration=_copy_dict(normalized_payload.get("calibration")),
            llm_raw_text=normalized_payload.get("llm_raw_text"),
            extra_fields=extra_fields,
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定评估字典，并保留未识别的扩展字段。"""
        payload = {
            "llm_model": self.llm_model,
            "confidence": self.confidence,
            "risk_flags": list(self.risk_flags),
            "skill_delta": _copy_dict(self.skill_delta),
            "s_delta": _copy_dict(self.s_delta),
            "evidence": list(self.evidence),
            "skill_scores_preview": _copy_dict(self.skill_scores_preview),
            "eval_mode": self.eval_mode,
        }
        if self.fallback_reason is not None:
            payload["fallback_reason"] = self.fallback_reason
        if self.calibration is not None:
            payload["calibration"] = _copy_dict(self.calibration)
        if self.llm_raw_text is not None:
            payload["llm_raw_text"] = self.llm_raw_text
        payload.update(_copy_dict(self.extra_fields))
        return payload


@dataclass(slots=True)
class TrainingRuntimeFlagsOutput:
    """运行时世界 flags 输出。"""

    panic_triggered: bool = False
    source_exposed: bool = False
    editor_locked: bool = False
    high_risk_path: bool = False

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingRuntimeFlagsOutput | None":
        """把原始 flags 字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None
        return cls(
            panic_triggered=bool(payload.get("panic_triggered", False)),
            source_exposed=bool(payload.get("source_exposed", False)),
            editor_locked=bool(payload.get("editor_locked", False)),
            high_risk_path=bool(payload.get("high_risk_path", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定 flags 字典。"""
        return {
            "panic_triggered": self.panic_triggered,
            "source_exposed": self.source_exposed,
            "editor_locked": self.editor_locked,
            "high_risk_path": self.high_risk_path,
        }


@dataclass(slots=True)
class TrainingRuntimeStateBarOutput:
    """运行时状态条输出。"""

    editor_trust: float = 0.0
    public_stability: float = 0.0
    source_safety: float = 0.0

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingRuntimeStateBarOutput | None":
        """把原始状态条字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None
        return cls(
            editor_trust=float(payload.get("editor_trust", 0.0) or 0.0),
            public_stability=float(payload.get("public_stability", 0.0) or 0.0),
            source_safety=float(payload.get("source_safety", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定状态条字典。"""
        return {
            "editor_trust": self.editor_trust,
            "public_stability": self.public_stability,
            "source_safety": self.source_safety,
        }


@dataclass(slots=True)
class TrainingConsequenceEventOutput:
    """运行时后果事件输出。"""

    event_type: str
    label: str = ""
    summary: str = ""
    severity: str = "medium"
    round_no: Optional[int] = None
    related_flag: Optional[str] = None
    state_bar: Optional["TrainingRuntimeStateBarOutput | Dict[str, Any]"] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingConsequenceEventOutput | None":
        """把原始后果事件字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        event_type = str(payload.get("event_type") or "").strip()
        if not event_type:
            return None

        round_value = payload.get("round_no")
        return cls(
            event_type=event_type,
            label=str(payload.get("label") or ""),
            summary=str(payload.get("summary") or ""),
            severity=str(payload.get("severity") or "medium"),
            round_no=int(round_value) if round_value is not None else None,
            related_flag=str(payload.get("related_flag")) if payload.get("related_flag") is not None else None,
            state_bar=TrainingRuntimeStateBarOutput.from_payload(payload.get("state_bar")),
            payload=_copy_dict(payload.get("payload")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定后果事件字典。"""
        event_payload = {
            "event_type": self.event_type,
            "label": self.label,
            "summary": self.summary,
            "severity": self.severity,
            "payload": _copy_dict(self.payload),
        }
        if self.round_no is not None:
            event_payload["round_no"] = self.round_no
        if self.related_flag is not None:
            event_payload["related_flag"] = self.related_flag
        if self.state_bar is not None:
            event_payload["state_bar"] = _serialize_runtime_state_bar(self.state_bar)
        return event_payload


@dataclass(slots=True)
class TrainingRuntimeStateOutput:
    """统一运行时状态输出。"""

    current_round_no: int
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    runtime_flags: "TrainingRuntimeFlagsOutput | Dict[str, Any]"
    state_bar: "TrainingRuntimeStateBarOutput | Dict[str, Any]"
    current_scene_id: Optional[str] = None
    player_profile: Optional["TrainingPlayerProfileOutput | Dict[str, Any]"] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingRuntimeStateOutput | None":
        """把原始运行时状态字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        round_value = payload.get("current_round_no")
        if round_value is None:
            return None

        return cls(
            current_round_no=int(round_value),
            current_scene_id=(
                str(payload.get("current_scene_id"))
                if payload.get("current_scene_id") is not None and str(payload.get("current_scene_id")).strip()
                else None
            ),
            k_state=_copy_dict(payload.get("k_state")),
            s_state=_copy_dict(payload.get("s_state")),
            runtime_flags=TrainingRuntimeFlagsOutput.from_payload(payload.get("runtime_flags")) or TrainingRuntimeFlagsOutput(),
            state_bar=TrainingRuntimeStateBarOutput.from_payload(payload.get("state_bar")) or TrainingRuntimeStateBarOutput(),
            player_profile=TrainingPlayerProfileOutput.from_payload(payload.get("player_profile")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定运行时状态字典。"""
        payload = {
            "current_round_no": self.current_round_no,
            "k_state": _copy_dict(self.k_state),
            "s_state": _copy_dict(self.s_state),
            "runtime_flags": _serialize_runtime_flags(self.runtime_flags) or {},
            "state_bar": _serialize_runtime_state_bar(self.state_bar) or {},
        }
        if self.current_scene_id is not None:
            payload["current_scene_id"] = self.current_scene_id
        if self.player_profile is not None:
            payload["player_profile"] = _serialize_player_profile(self.player_profile)
        return payload


@dataclass(slots=True)
class TrainingDecisionCandidateOutput:
    """训练决策上下文中的候选题摘要。"""

    scenario_id: str
    title: str = ""
    rank: Optional[int] = None
    rank_score: float = 0.0
    is_selected: bool = False
    is_recommended: bool = False

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingDecisionCandidateOutput | None":
        """把候选题字典转换成稳定决策摘要 DTO。"""
        if not isinstance(payload, dict):
            return None

        scenario_id = str(payload.get("scenario_id") or payload.get("id") or "").strip()
        if not scenario_id:
            return None

        # 兼容两种输入：
        # 1. 已压平的 candidate 摘要
        # 2. 直接传入带 recommendation 的原始 scenario 载荷
        recommendation_payload = payload.get("recommendation")
        if not isinstance(recommendation_payload, dict):
            recommendation_payload = {}

        rank_value = payload.get("rank", recommendation_payload.get("rank"))
        return cls(
            scenario_id=scenario_id,
            title=str(payload.get("title") or scenario_id),
            rank=int(rank_value) if rank_value is not None else None,
            rank_score=float(payload.get("rank_score", recommendation_payload.get("rank_score", 0.0)) or 0.0),
            is_selected=bool(payload.get("is_selected", False)),
            is_recommended=bool(payload.get("is_recommended", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出候选题决策摘要。"""
        payload = {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "rank_score": self.rank_score,
            "is_selected": self.is_selected,
            "is_recommended": self.is_recommended,
        }
        if self.rank is not None:
            payload["rank"] = self.rank
        return payload


@dataclass(slots=True)
class TrainingBranchTransitionOutput:
    """训练分支跳转上下文。"""

    source_scenario_id: str
    target_scenario_id: str
    transition_type: str = "branch"
    reason: str = ""
    triggered_flags: List[str] = field(default_factory=list)
    matched_rule: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingBranchTransitionOutput | None":
        """把原始分支跳转字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        source_scenario_id = str(payload.get("source_scenario_id") or "").strip()
        target_scenario_id = str(payload.get("target_scenario_id") or "").strip()
        transition_type = str(payload.get("transition_type") or "branch").strip()
        if not source_scenario_id or not target_scenario_id or not transition_type:
            return None

        return cls(
            source_scenario_id=source_scenario_id,
            target_scenario_id=target_scenario_id,
            transition_type=transition_type,
            reason=str(payload.get("reason") or ""),
            triggered_flags=[
                str(item)
                for item in payload.get("triggered_flags", []) or []
                if str(item or "").strip()
            ],
            matched_rule=_copy_dict(payload.get("matched_rule")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定分支跳转字典。"""
        payload = {
            "source_scenario_id": self.source_scenario_id,
            "target_scenario_id": self.target_scenario_id,
            "transition_type": self.transition_type,
            "triggered_flags": list(self.triggered_flags),
        }
        if self.reason:
            payload["reason"] = self.reason
        if self.matched_rule:
            payload["matched_rule"] = _copy_dict(self.matched_rule)
        return payload


@dataclass(slots=True)
class TrainingBranchTransitionSummaryOutput:
    """训练分支跳转聚合摘要。"""

    source_scenario_id: str
    target_scenario_id: str
    transition_type: str = "branch"
    reason: str = ""
    count: int = 0
    round_nos: List[int] = field(default_factory=list)
    triggered_flags: List[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingBranchTransitionSummaryOutput | None":
        """把原始分支聚合字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        source_scenario_id = str(payload.get("source_scenario_id") or "").strip()
        target_scenario_id = str(payload.get("target_scenario_id") or "").strip()
        transition_type = str(payload.get("transition_type") or "branch").strip()
        if not source_scenario_id or not target_scenario_id or not transition_type:
            return None

        round_nos: List[int] = []
        for item in payload.get("round_nos", []) or []:
            try:
                round_no = int(item)
            except (TypeError, ValueError):
                continue
            if round_no not in round_nos:
                round_nos.append(round_no)

        triggered_flags: List[str] = []
        for item in payload.get("triggered_flags", []) or []:
            text = str(item or "").strip()
            if not text or text in triggered_flags:
                continue
            triggered_flags.append(text)

        return cls(
            source_scenario_id=source_scenario_id,
            target_scenario_id=target_scenario_id,
            transition_type=transition_type,
            reason=str(payload.get("reason") or ""),
            count=_to_non_negative_int(payload.get("count")),
            round_nos=round_nos,
            triggered_flags=triggered_flags,
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定分支聚合摘要字典。"""
        payload = {
            "source_scenario_id": self.source_scenario_id,
            "target_scenario_id": self.target_scenario_id,
            "transition_type": self.transition_type,
            "count": _to_non_negative_int(self.count),
            "round_nos": [int(item) for item in self.round_nos],
            "triggered_flags": list(self.triggered_flags),
        }
        if self.reason:
            payload["reason"] = self.reason
        return payload


@dataclass(slots=True)
class TrainingRoundDecisionContextOutput:
    """训练回合提交时的推荐与选择上下文。"""

    mode: str
    selection_source: str
    selected_scenario_id: str
    recommended_scenario_id: Optional[str] = None
    candidate_pool: List[TrainingDecisionCandidateOutput] = field(default_factory=list)
    selected_recommendation: Optional[TrainingScenarioRecommendationOutput] = None
    recommended_recommendation: Optional[TrainingScenarioRecommendationOutput] = None
    selected_branch_transition: Optional[TrainingBranchTransitionOutput] = None
    recommended_branch_transition: Optional[TrainingBranchTransitionOutput] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingRoundDecisionContextOutput | None":
        """把原始决策上下文字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        selected_scenario_id = str(payload.get("selected_scenario_id") or "").strip()
        mode = str(payload.get("mode") or "").strip()
        selection_source = str(payload.get("selection_source") or "").strip()
        if not selected_scenario_id or not mode or not selection_source:
            return None

        candidate_items: List[TrainingDecisionCandidateOutput] = []
        for item in payload.get("candidate_pool", []) or []:
            candidate_output = TrainingDecisionCandidateOutput.from_payload(item)
            if candidate_output is not None:
                candidate_items.append(candidate_output)

        recommended_scenario_id = payload.get("recommended_scenario_id")
        return cls(
            mode=mode,
            selection_source=selection_source,
            selected_scenario_id=selected_scenario_id,
            recommended_scenario_id=str(recommended_scenario_id) if recommended_scenario_id is not None else None,
            candidate_pool=candidate_items,
            selected_recommendation=TrainingScenarioRecommendationOutput.from_payload(payload.get("selected_recommendation")),
            recommended_recommendation=TrainingScenarioRecommendationOutput.from_payload(payload.get("recommended_recommendation")),
            selected_branch_transition=TrainingBranchTransitionOutput.from_payload(payload.get("selected_branch_transition")),
            recommended_branch_transition=TrainingBranchTransitionOutput.from_payload(
                payload.get("recommended_branch_transition")
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定决策上下文字典。"""
        payload = {
            "mode": self.mode,
            "selection_source": self.selection_source,
            "selected_scenario_id": self.selected_scenario_id,
            "candidate_pool": [item.to_dict() for item in self.candidate_pool],
        }
        if self.recommended_scenario_id is not None:
            payload["recommended_scenario_id"] = self.recommended_scenario_id
        if self.selected_recommendation is not None:
            payload["selected_recommendation"] = self.selected_recommendation.to_dict()
        if self.recommended_recommendation is not None:
            payload["recommended_recommendation"] = self.recommended_recommendation.to_dict()
        if self.selected_branch_transition is not None:
            payload["selected_branch_transition"] = self.selected_branch_transition.to_dict()
        if self.recommended_branch_transition is not None:
            payload["recommended_branch_transition"] = self.recommended_branch_transition.to_dict()
        return payload


@dataclass(slots=True)
class TrainingMetricObservationOutput:
    """单个能力或状态观测项输出。"""

    code: str
    before: float = 0.0
    delta: float = 0.0
    after: float = 0.0
    is_target: bool = False

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingMetricObservationOutput | None":
        """把原始观测项字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        code = str(payload.get("code") or "").strip()
        if not code:
            return None

        return cls(
            code=code,
            before=float(payload.get("before", 0.0) or 0.0),
            delta=float(payload.get("delta", 0.0) or 0.0),
            after=float(payload.get("after", 0.0) or 0.0),
            is_target=bool(payload.get("is_target", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定观测项字典。"""
        return {
            "code": self.code,
            "before": self.before,
            "delta": self.delta,
            "after": self.after,
            "is_target": self.is_target,
        }


@dataclass(slots=True)
class TrainingKtObservationOutput:
    """训练回合的 KT 结构化观测输出。"""

    scenario_id: str
    scenario_title: str = ""
    training_mode: str = "guided"
    round_no: Optional[int] = None
    primary_skill_code: Optional[str] = None
    primary_risk_flag: Optional[str] = None
    is_high_risk: bool = False
    target_skills: List[str] = field(default_factory=list)
    weak_skills_before: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    focus_tags: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    skill_observations: List[TrainingMetricObservationOutput] = field(default_factory=list)
    state_observations: List[TrainingMetricObservationOutput] = field(default_factory=list)
    observation_summary: str = ""

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingKtObservationOutput | None":
        """把原始 KT 观测字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        scenario_id = str(payload.get("scenario_id") or "").strip()
        if not scenario_id:
            return None

        skill_items: List[TrainingMetricObservationOutput] = []
        for item in payload.get("skill_observations", []) or []:
            output = TrainingMetricObservationOutput.from_payload(item)
            if output is not None:
                skill_items.append(output)

        state_items: List[TrainingMetricObservationOutput] = []
        for item in payload.get("state_observations", []) or []:
            output = TrainingMetricObservationOutput.from_payload(item)
            if output is not None:
                state_items.append(output)

        round_value = payload.get("round_no")
        return cls(
            scenario_id=scenario_id,
            scenario_title=str(payload.get("scenario_title") or ""),
            training_mode=str(payload.get("training_mode") or "guided"),
            round_no=int(round_value) if round_value is not None else None,
            primary_skill_code=str(payload.get("primary_skill_code")) if payload.get("primary_skill_code") is not None else None,
            primary_risk_flag=str(payload.get("primary_risk_flag")) if payload.get("primary_risk_flag") is not None else None,
            is_high_risk=bool(payload.get("is_high_risk", False)),
            target_skills=[str(item) for item in payload.get("target_skills", []) if str(item or "").strip()],
            weak_skills_before=[str(item) for item in payload.get("weak_skills_before", []) if str(item or "").strip()],
            risk_flags=[str(item) for item in payload.get("risk_flags", []) if str(item or "").strip()],
            focus_tags=[str(item) for item in payload.get("focus_tags", []) if str(item or "").strip()],
            evidence=[str(item) for item in payload.get("evidence", []) if str(item or "").strip()],
            skill_observations=skill_items,
            state_observations=state_items,
            observation_summary=str(payload.get("observation_summary") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定 KT 观测字典。"""
        payload = {
            "scenario_id": self.scenario_id,
            "scenario_title": self.scenario_title,
            "training_mode": self.training_mode,
            "is_high_risk": self.is_high_risk,
            "target_skills": list(self.target_skills),
            "weak_skills_before": list(self.weak_skills_before),
            "risk_flags": list(self.risk_flags),
            "focus_tags": list(self.focus_tags),
            "evidence": list(self.evidence),
            "skill_observations": [item.to_dict() for item in self.skill_observations],
            "state_observations": [item.to_dict() for item in self.state_observations],
            "observation_summary": self.observation_summary,
        }
        if self.round_no is not None:
            payload["round_no"] = self.round_no
        if self.primary_skill_code is not None:
            payload["primary_skill_code"] = self.primary_skill_code
        if self.primary_risk_flag is not None:
            payload["primary_risk_flag"] = self.primary_risk_flag
        return payload


@dataclass(slots=True)
class TrainingRecommendationLogOutput:
    """训练推荐日志输出。"""

    round_no: int
    training_mode: str = "guided"
    selection_source: Optional[str] = None
    recommended_scenario_id: Optional[str] = None
    selected_scenario_id: Optional[str] = None
    candidate_pool: List[TrainingDecisionCandidateOutput] = field(default_factory=list)
    recommended_recommendation: Optional[TrainingScenarioRecommendationOutput] = None
    selected_recommendation: Optional[TrainingScenarioRecommendationOutput] = None
    decision_context: Optional[TrainingRoundDecisionContextOutput] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingRecommendationLogOutput | None":
        """把原始推荐日志字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        round_value = payload.get("round_no")
        if round_value is None:
            return None

        candidate_items: List[TrainingDecisionCandidateOutput] = []
        for item in payload.get("candidate_pool", []) or []:
            candidate_output = TrainingDecisionCandidateOutput.from_payload(item)
            if candidate_output is not None:
                candidate_items.append(candidate_output)

        return cls(
            round_no=int(round_value),
            training_mode=str(payload.get("training_mode") or "guided"),
            selection_source=str(payload.get("selection_source")) if payload.get("selection_source") is not None else None,
            recommended_scenario_id=str(payload.get("recommended_scenario_id")) if payload.get("recommended_scenario_id") is not None else None,
            selected_scenario_id=str(payload.get("selected_scenario_id")) if payload.get("selected_scenario_id") is not None else None,
            candidate_pool=candidate_items,
            recommended_recommendation=TrainingScenarioRecommendationOutput.from_payload(payload.get("recommended_recommendation")),
            selected_recommendation=TrainingScenarioRecommendationOutput.from_payload(payload.get("selected_recommendation")),
            decision_context=TrainingRoundDecisionContextOutput.from_payload(payload.get("decision_context")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定推荐日志字典。"""
        payload = {
            "round_no": self.round_no,
            "training_mode": self.training_mode,
            "candidate_pool": [item.to_dict() for item in self.candidate_pool],
        }
        if self.selection_source is not None:
            payload["selection_source"] = self.selection_source
        if self.recommended_scenario_id is not None:
            payload["recommended_scenario_id"] = self.recommended_scenario_id
        if self.selected_scenario_id is not None:
            payload["selected_scenario_id"] = self.selected_scenario_id
        if self.recommended_recommendation is not None:
            payload["recommended_recommendation"] = self.recommended_recommendation.to_dict()
        if self.selected_recommendation is not None:
            payload["selected_recommendation"] = self.selected_recommendation.to_dict()
        if self.decision_context is not None:
            payload["decision_context"] = self.decision_context.to_dict()
        return payload


@dataclass(slots=True)
class TrainingAuditEventOutput:
    """训练审计事件输出。"""

    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    round_no: Optional[int] = None
    timestamp: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingAuditEventOutput | None":
        """把原始审计事件字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        event_type = str(payload.get("event_type") or "").strip()
        if not event_type:
            return None

        round_value = payload.get("round_no")
        return cls(
            event_type=event_type,
            payload=_copy_dict(payload.get("payload")),
            round_no=int(round_value) if round_value is not None else None,
            timestamp=str(payload.get("timestamp")) if payload.get("timestamp") is not None else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定审计事件字典。"""
        payload = {
            "event_type": self.event_type,
            "payload": _copy_dict(self.payload),
        }
        if self.round_no is not None:
            payload["round_no"] = self.round_no
        if self.timestamp is not None:
            payload["timestamp"] = self.timestamp
        return payload


@dataclass(slots=True)
class TrainingDiagnosticsCountItemOutput:
    """训练诊断摘要中的单个统计项。"""

    code: str
    count: int = 0

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingDiagnosticsCountItemOutput | None":
        """把计数字典归一成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        code = str(payload.get("code") or "").strip()
        if not code:
            return None

        return cls(
            code=code,
            count=_to_non_negative_int(payload.get("count")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定统计项字典。"""
        return {
            "code": self.code,
            "count": _to_non_negative_int(self.count),
        }


@dataclass(slots=True)
class TrainingDiagnosticsSummaryOutput:
    """训练诊断摘要输出，供前端和运营直接消费关键统计结果。"""

    total_recommendation_logs: int = 0
    total_audit_events: int = 0
    total_kt_observations: int = 0
    high_risk_round_count: int = 0
    high_risk_round_nos: List[int] = field(default_factory=list)
    recommended_vs_selected_mismatch_count: int = 0
    recommended_vs_selected_mismatch_rounds: List[int] = field(default_factory=list)
    risk_flag_counts: List["TrainingDiagnosticsCountItemOutput | Dict[str, Any]"] = field(default_factory=list)
    primary_skill_focus_counts: List["TrainingDiagnosticsCountItemOutput | Dict[str, Any]"] = field(default_factory=list)
    top_weak_skills: List["TrainingDiagnosticsCountItemOutput | Dict[str, Any]"] = field(default_factory=list)
    selection_source_counts: List["TrainingDiagnosticsCountItemOutput | Dict[str, Any]"] = field(default_factory=list)
    event_type_counts: List["TrainingDiagnosticsCountItemOutput | Dict[str, Any]"] = field(default_factory=list)
    phase_tag_counts: List["TrainingDiagnosticsCountItemOutput | Dict[str, Any]"] = field(default_factory=list)
    phase_transition_count: int = 0
    phase_transition_rounds: List[int] = field(default_factory=list)
    panic_trigger_round_count: int = 0
    panic_trigger_rounds: List[int] = field(default_factory=list)
    source_exposed_round_count: int = 0
    source_exposed_rounds: List[int] = field(default_factory=list)
    editor_locked_round_count: int = 0
    editor_locked_rounds: List[int] = field(default_factory=list)
    high_risk_path_round_count: int = 0
    high_risk_path_rounds: List[int] = field(default_factory=list)
    branch_transition_count: int = 0
    branch_transition_rounds: List[int] = field(default_factory=list)
    branch_transitions: List["TrainingBranchTransitionSummaryOutput | Dict[str, Any]"] = field(default_factory=list)
    last_primary_skill_code: Optional[str] = None
    last_primary_risk_flag: Optional[str] = None
    last_event_type: Optional[str] = None
    last_phase_tags: List[str] = field(default_factory=list)
    last_branch_transition: Optional["TrainingBranchTransitionOutput | Dict[str, Any]"] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingDiagnosticsSummaryOutput | None":
        """把诊断摘要字典归一成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        def _normalize_round_list(items: List[Any] | None) -> List[int]:
            normalized_items: List[int] = []
            for item in items or []:
                try:
                    round_no = int(item)
                except (TypeError, ValueError):
                    continue
                if round_no not in normalized_items:
                    normalized_items.append(round_no)
            return normalized_items

        def _normalize_text_list(items: List[Any] | None) -> List[str]:
            normalized_items: List[str] = []
            for item in items or []:
                text = str(item or "").strip()
                if not text or text in normalized_items:
                    continue
                normalized_items.append(text)
            return normalized_items

        return cls(
            total_recommendation_logs=_to_non_negative_int(payload.get("total_recommendation_logs")),
            total_audit_events=_to_non_negative_int(payload.get("total_audit_events")),
            total_kt_observations=_to_non_negative_int(payload.get("total_kt_observations")),
            high_risk_round_count=_to_non_negative_int(payload.get("high_risk_round_count")),
            high_risk_round_nos=_normalize_round_list(payload.get("high_risk_round_nos")),
            recommended_vs_selected_mismatch_count=_to_non_negative_int(
                payload.get("recommended_vs_selected_mismatch_count")
            ),
            recommended_vs_selected_mismatch_rounds=_normalize_round_list(
                payload.get("recommended_vs_selected_mismatch_rounds")
            ),
            risk_flag_counts=_serialize_diagnostics_count_item_list(payload.get("risk_flag_counts")),
            primary_skill_focus_counts=_serialize_diagnostics_count_item_list(payload.get("primary_skill_focus_counts")),
            top_weak_skills=_serialize_diagnostics_count_item_list(payload.get("top_weak_skills")),
            selection_source_counts=_serialize_diagnostics_count_item_list(payload.get("selection_source_counts")),
            event_type_counts=_serialize_diagnostics_count_item_list(payload.get("event_type_counts")),
            phase_tag_counts=_serialize_diagnostics_count_item_list(payload.get("phase_tag_counts")),
            phase_transition_count=_to_non_negative_int(payload.get("phase_transition_count")),
            phase_transition_rounds=_normalize_round_list(payload.get("phase_transition_rounds")),
            panic_trigger_round_count=_to_non_negative_int(payload.get("panic_trigger_round_count")),
            panic_trigger_rounds=_normalize_round_list(payload.get("panic_trigger_rounds")),
            source_exposed_round_count=_to_non_negative_int(payload.get("source_exposed_round_count")),
            source_exposed_rounds=_normalize_round_list(payload.get("source_exposed_rounds")),
            editor_locked_round_count=_to_non_negative_int(payload.get("editor_locked_round_count")),
            editor_locked_rounds=_normalize_round_list(payload.get("editor_locked_rounds")),
            high_risk_path_round_count=_to_non_negative_int(payload.get("high_risk_path_round_count")),
            high_risk_path_rounds=_normalize_round_list(payload.get("high_risk_path_rounds")),
            branch_transition_count=_to_non_negative_int(payload.get("branch_transition_count")),
            branch_transition_rounds=_normalize_round_list(payload.get("branch_transition_rounds")),
            branch_transitions=_serialize_branch_transition_summary_list(payload.get("branch_transitions")),
            last_primary_skill_code=(
                str(payload.get("last_primary_skill_code"))
                if payload.get("last_primary_skill_code") is not None
                else None
            ),
            last_primary_risk_flag=(
                str(payload.get("last_primary_risk_flag"))
                if payload.get("last_primary_risk_flag") is not None
                else None
            ),
            last_event_type=str(payload.get("last_event_type")) if payload.get("last_event_type") is not None else None,
            last_phase_tags=_normalize_text_list(payload.get("last_phase_tags")),
            last_branch_transition=_serialize_branch_transition(payload.get("last_branch_transition")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定诊断摘要字典。"""
        payload = {
            "total_recommendation_logs": _to_non_negative_int(self.total_recommendation_logs),
            "total_audit_events": _to_non_negative_int(self.total_audit_events),
            "total_kt_observations": _to_non_negative_int(self.total_kt_observations),
            "high_risk_round_count": _to_non_negative_int(self.high_risk_round_count),
            "high_risk_round_nos": [int(item) for item in self.high_risk_round_nos],
            "recommended_vs_selected_mismatch_count": _to_non_negative_int(
                self.recommended_vs_selected_mismatch_count
            ),
            "recommended_vs_selected_mismatch_rounds": [
                int(item) for item in self.recommended_vs_selected_mismatch_rounds
            ],
            "risk_flag_counts": _serialize_diagnostics_count_item_list(self.risk_flag_counts),
            "primary_skill_focus_counts": _serialize_diagnostics_count_item_list(self.primary_skill_focus_counts),
            "top_weak_skills": _serialize_diagnostics_count_item_list(self.top_weak_skills),
            "selection_source_counts": _serialize_diagnostics_count_item_list(self.selection_source_counts),
            "event_type_counts": _serialize_diagnostics_count_item_list(self.event_type_counts),
            "phase_tag_counts": _serialize_diagnostics_count_item_list(self.phase_tag_counts),
            "phase_transition_count": _to_non_negative_int(self.phase_transition_count),
            "phase_transition_rounds": [int(item) for item in self.phase_transition_rounds],
            "panic_trigger_round_count": _to_non_negative_int(self.panic_trigger_round_count),
            "panic_trigger_rounds": [int(item) for item in self.panic_trigger_rounds],
            "source_exposed_round_count": _to_non_negative_int(self.source_exposed_round_count),
            "source_exposed_rounds": [int(item) for item in self.source_exposed_rounds],
            "editor_locked_round_count": _to_non_negative_int(self.editor_locked_round_count),
            "editor_locked_rounds": [int(item) for item in self.editor_locked_rounds],
            "high_risk_path_round_count": _to_non_negative_int(self.high_risk_path_round_count),
            "high_risk_path_rounds": [int(item) for item in self.high_risk_path_rounds],
            "branch_transition_count": _to_non_negative_int(self.branch_transition_count),
            "branch_transition_rounds": [int(item) for item in self.branch_transition_rounds],
            "branch_transitions": _serialize_branch_transition_summary_list(self.branch_transitions),
            "last_phase_tags": [str(item) for item in self.last_phase_tags if str(item or "").strip()],
        }
        if self.last_primary_skill_code is not None:
            payload["last_primary_skill_code"] = self.last_primary_skill_code
        if self.last_primary_risk_flag is not None:
            payload["last_primary_risk_flag"] = self.last_primary_risk_flag
        if self.last_event_type is not None:
            payload["last_event_type"] = self.last_event_type
        if self.last_branch_transition is not None:
            payload["last_branch_transition"] = _serialize_branch_transition(self.last_branch_transition)
        return payload


@dataclass(slots=True)
class TrainingInitOutput:
    """训练初始化结果。"""

    session_id: str
    status: str
    round_no: int
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    character_id: Optional[int] = None
    player_profile: Optional[TrainingPlayerProfileOutput | Dict[str, Any]] = None
    runtime_state: Optional["TrainingRuntimeStateOutput | Dict[str, Any]"] = None
    # 兼容旧测试和旧调用方，允许直接注入原始字典；服务内部仍优先传 DTO。
    next_scenario: Optional[TrainingScenarioOutput | Dict[str, Any]] = None
    scenario_candidates: Optional[List[TrainingScenarioOutput | Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定字典结构，并按需省略可选字段。"""
        payload = {
            "session_id": self.session_id,
            "character_id": self.character_id,
            "status": self.status,
            "round_no": self.round_no,
            "k_state": _copy_dict(self.k_state),
            "s_state": _copy_dict(self.s_state),
            "next_scenario": _serialize_scenario(self.next_scenario),
        }
        if self.player_profile is not None:
            payload["player_profile"] = _serialize_player_profile(self.player_profile)
        if self.runtime_state is not None:
            payload["runtime_state"] = _serialize_runtime_state(self.runtime_state)
        if self.scenario_candidates is not None:
            payload["scenario_candidates"] = _serialize_scenario_list(self.scenario_candidates)
        return payload


@dataclass(slots=True)
class TrainingNextScenarioOutput:
    """下一场景结果。"""

    session_id: str
    status: str
    round_no: int
    # 兼容旧测试和旧调用方，允许直接注入原始字典；服务内部仍优先传 DTO。
    scenario: Optional[TrainingScenarioOutput | Dict[str, Any]]
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    player_profile: Optional[TrainingPlayerProfileOutput | Dict[str, Any]] = None
    runtime_state: Optional["TrainingRuntimeStateOutput | Dict[str, Any]"] = None
    scenario_candidates: Optional[List[TrainingScenarioOutput | Dict[str, Any]]] = None
    ending: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """导出下一场景响应，支持 completed 状态的稳定字段形状。"""
        payload = {
            "session_id": self.session_id,
            "status": self.status,
            "round_no": self.round_no,
            "scenario": _serialize_scenario(self.scenario),
            "k_state": _copy_dict(self.k_state),
            "s_state": _copy_dict(self.s_state),
        }
        if self.player_profile is not None:
            payload["player_profile"] = _serialize_player_profile(self.player_profile)
        if self.runtime_state is not None:
            payload["runtime_state"] = _serialize_runtime_state(self.runtime_state)
        if self.scenario_candidates is not None:
            payload["scenario_candidates"] = _serialize_scenario_list(self.scenario_candidates)
        if self.ending is not None:
            payload["ending"] = _copy_dict(self.ending)
        return payload


@dataclass(slots=True)
class TrainingRoundSubmitOutput:
    """提交回合结果。"""

    session_id: str
    round_no: int
    # 兼容旧测试和旧调用方，允许直接传评估字典；服务内部仍优先传 DTO。
    evaluation: TrainingEvaluationOutput | Dict[str, Any]
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    is_completed: bool
    player_profile: Optional[TrainingPlayerProfileOutput | Dict[str, Any]] = None
    runtime_state: Optional["TrainingRuntimeStateOutput | Dict[str, Any]"] = None
    consequence_events: List["TrainingConsequenceEventOutput | Dict[str, Any]"] = field(default_factory=list)
    ending: Optional[Dict[str, Any]] = None
    decision_context: Optional["TrainingRoundDecisionContextOutput | Dict[str, Any]"] = None

    def to_dict(self) -> Dict[str, Any]:
        """导出提交结果。"""
        payload = {
            "session_id": self.session_id,
            "round_no": self.round_no,
            "evaluation": _serialize_evaluation(self.evaluation) or {},
            "k_state": _copy_dict(self.k_state),
            "s_state": _copy_dict(self.s_state),
            "is_completed": self.is_completed,
            "ending": _copy_dict(self.ending) if self.ending is not None else None,
        }
        if self.player_profile is not None:
            payload["player_profile"] = _serialize_player_profile(self.player_profile)
        if self.runtime_state is not None:
            payload["runtime_state"] = _serialize_runtime_state(self.runtime_state)
        payload["consequence_events"] = _serialize_consequence_event_list(self.consequence_events)
        if self.decision_context is not None:
            payload["decision_context"] = _serialize_decision_context(self.decision_context)
        return payload


@dataclass(slots=True)
class TrainingProgressOutput:
    """训练进度结果。"""

    session_id: str
    status: str
    round_no: int
    total_rounds: int
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    character_id: Optional[int] = None
    player_profile: Optional[TrainingPlayerProfileOutput | Dict[str, Any]] = None
    runtime_state: Optional["TrainingRuntimeStateOutput | Dict[str, Any]"] = None
    decision_context: Optional["TrainingRoundDecisionContextOutput | Dict[str, Any]"] = None
    consequence_events: List["TrainingConsequenceEventOutput | Dict[str, Any]"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """导出训练进度。"""
        payload = {
            "session_id": self.session_id,
            "character_id": self.character_id,
            "status": self.status,
            "round_no": self.round_no,
            "total_rounds": self.total_rounds,
            "k_state": _copy_dict(self.k_state),
            "s_state": _copy_dict(self.s_state),
        }
        if self.player_profile is not None:
            payload["player_profile"] = _serialize_player_profile(self.player_profile)
        if self.runtime_state is not None:
            payload["runtime_state"] = _serialize_runtime_state(self.runtime_state)
        if self.decision_context is not None:
            payload["decision_context"] = _serialize_decision_context(self.decision_context)
        payload["consequence_events"] = _serialize_consequence_event_list(self.consequence_events)
        return payload


@dataclass(slots=True)
class TrainingSessionProgressAnchorOutput:
    """Stable progress anchor for training session recovery reads."""

    current_round_no: int
    total_rounds: int
    completed_rounds: int
    remaining_rounds: int
    progress_percent: float = 0.0
    next_round_no: Optional[int] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingSessionProgressAnchorOutput | None":
        """Normalize a raw progress anchor payload into a stable DTO."""
        if not isinstance(payload, dict):
            return None

        current_round_no = payload.get("current_round_no")
        total_rounds = payload.get("total_rounds")
        completed_rounds = payload.get("completed_rounds")
        remaining_rounds = payload.get("remaining_rounds")
        if current_round_no is None or total_rounds is None or completed_rounds is None or remaining_rounds is None:
            return None

        next_round_no = payload.get("next_round_no")
        return cls(
            current_round_no=_to_non_negative_int(current_round_no),
            total_rounds=_to_non_negative_int(total_rounds),
            completed_rounds=_to_non_negative_int(completed_rounds),
            remaining_rounds=_to_non_negative_int(remaining_rounds),
            progress_percent=float(payload.get("progress_percent", 0.0) or 0.0),
            next_round_no=_to_non_negative_int(next_round_no) if next_round_no is not None else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Export the stable progress anchor payload."""
        payload = {
            "current_round_no": self.current_round_no,
            "total_rounds": self.total_rounds,
            "completed_rounds": self.completed_rounds,
            "remaining_rounds": self.remaining_rounds,
            "progress_percent": self.progress_percent,
        }
        if self.next_round_no is not None:
            payload["next_round_no"] = self.next_round_no
        return payload


def calculate_progress_percent(*, completed_rounds: int, total_rounds: int) -> float:
    """Freeze progress_percent semantics to a real 0-100 percentage value."""
    normalized_total_rounds = max(int(total_rounds), 0)
    normalized_completed_rounds = max(int(completed_rounds), 0)
    if normalized_total_rounds <= 0:
        return 0.0
    ratio = normalized_completed_rounds / normalized_total_rounds
    return round(max(0.0, min(ratio, 1.0)) * 100, 2)


@dataclass(slots=True)
class TrainingSessionSummaryOutput:
    """Stable training session recovery summary."""

    session_id: str
    status: str
    training_mode: str
    current_round_no: int
    total_rounds: int
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    progress_anchor: "TrainingSessionProgressAnchorOutput | Dict[str, Any]"
    can_resume: bool
    is_completed: bool
    character_id: Optional[int] = None
    player_profile: Optional["TrainingPlayerProfileOutput | Dict[str, Any]"] = None
    runtime_state: Optional["TrainingRuntimeStateOutput | Dict[str, Any]"] = None
    resumable_scenario: Optional["TrainingScenarioOutput | Dict[str, Any]"] = None
    scenario_candidates: List["TrainingScenarioOutput | Dict[str, Any]"] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    end_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Export the stable session summary payload."""
        payload = {
            "session_id": self.session_id,
            "character_id": self.character_id,
            "status": self.status,
            "training_mode": self.training_mode,
            "current_round_no": self.current_round_no,
            "total_rounds": self.total_rounds,
            "k_state": _copy_dict(self.k_state),
            "s_state": _copy_dict(self.s_state),
            "progress_anchor": _serialize_progress_anchor(self.progress_anchor) or {},
            "resumable_scenario": _serialize_scenario(self.resumable_scenario),
            "scenario_candidates": _serialize_scenario_list(self.scenario_candidates) or [],
            "can_resume": self.can_resume,
            "is_completed": self.is_completed,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "end_time": self.end_time,
        }
        if self.player_profile is not None:
            payload["player_profile"] = _serialize_player_profile(self.player_profile)
        if self.runtime_state is not None:
            payload["runtime_state"] = _serialize_runtime_state(self.runtime_state)
        return payload


@dataclass(slots=True)
class TrainingHistoryOutput:
    """Stable training history read model."""

    session_id: str
    status: str
    training_mode: str
    current_round_no: int
    total_rounds: int
    progress_anchor: "TrainingSessionProgressAnchorOutput | Dict[str, Any]"
    character_id: Optional[int] = None
    history: List["TrainingReportHistoryItemOutput"] = field(default_factory=list)
    is_completed: bool = False
    player_profile: Optional["TrainingPlayerProfileOutput | Dict[str, Any]"] = None
    runtime_state: Optional["TrainingRuntimeStateOutput | Dict[str, Any]"] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    end_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Export the stable training history payload."""
        payload = {
            "session_id": self.session_id,
            "character_id": self.character_id,
            "status": self.status,
            "training_mode": self.training_mode,
            "current_round_no": self.current_round_no,
            "total_rounds": self.total_rounds,
            "progress_anchor": _serialize_progress_anchor(self.progress_anchor) or {},
            "history": [item.to_dict() for item in self.history],
            "is_completed": self.is_completed,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "end_time": self.end_time,
        }
        if self.player_profile is not None:
            payload["player_profile"] = _serialize_player_profile(self.player_profile)
        if self.runtime_state is not None:
            payload["runtime_state"] = _serialize_runtime_state(self.runtime_state)
        return payload


@dataclass(slots=True)
class TrainingReportHistoryItemOutput:
    """训练报告中的单回合回放项。"""

    round_no: int
    scenario_id: str
    user_input: str
    selected_option: Optional[str]
    evaluation: Optional[TrainingEvaluationOutput | Dict[str, Any]]
    k_state_before: Dict[str, float]
    k_state_after: Dict[str, float]
    s_state_before: Dict[str, float]
    s_state_after: Dict[str, float]
    timestamp: Optional[str] = None
    decision_context: Optional["TrainingRoundDecisionContextOutput | Dict[str, Any]"] = None
    kt_observation: Optional["TrainingKtObservationOutput | Dict[str, Any]"] = None
    runtime_state: Optional["TrainingRuntimeStateOutput | Dict[str, Any]"] = None
    consequence_events: List["TrainingConsequenceEventOutput | Dict[str, Any]"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """导出单回合历史记录。"""
        payload = {
            "round_no": self.round_no,
            "scenario_id": self.scenario_id,
            "user_input": self.user_input,
            "selected_option": self.selected_option,
            "evaluation": _serialize_evaluation(self.evaluation),
            "k_state_before": _copy_dict(self.k_state_before),
            "k_state_after": _copy_dict(self.k_state_after),
            "s_state_before": _copy_dict(self.s_state_before),
            "s_state_after": _copy_dict(self.s_state_after),
            "timestamp": self.timestamp,
        }
        if self.decision_context is not None:
            payload["decision_context"] = _serialize_decision_context(self.decision_context)
        if self.kt_observation is not None:
            payload["kt_observation"] = _serialize_kt_observation(self.kt_observation)
        if self.runtime_state is not None:
            payload["runtime_state"] = _serialize_runtime_state(self.runtime_state)
        payload["consequence_events"] = _serialize_consequence_event_list(self.consequence_events)
        return payload


@dataclass(slots=True)
class TrainingReportMetricOutput:
    """训练报告中的单个能力或状态指标摘要。"""

    code: str
    initial: float = 0.0
    final: float = 0.0
    delta: float = 0.0
    weight: Optional[float] = None
    is_lowest_final: bool = False
    is_highest_gain: bool = False

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingReportMetricOutput | None":
        """把原始指标字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        code = str(payload.get("code") or "").strip()
        if not code:
            return None

        weight_value = payload.get("weight")
        return cls(
            code=code,
            initial=float(payload.get("initial", 0.0) or 0.0),
            final=float(payload.get("final", 0.0) or 0.0),
            delta=float(payload.get("delta", 0.0) or 0.0),
            weight=float(weight_value) if weight_value is not None else None,
            is_lowest_final=bool(payload.get("is_lowest_final", False)),
            is_highest_gain=bool(payload.get("is_highest_gain", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定指标摘要。"""
        payload = {
            "code": self.code,
            "initial": self.initial,
            "final": self.final,
            "delta": self.delta,
            "is_lowest_final": self.is_lowest_final,
            "is_highest_gain": self.is_highest_gain,
        }
        if self.weight is not None:
            payload["weight"] = self.weight
        return payload


@dataclass(slots=True)
class TrainingReportCurvePointOutput:
    """训练报告中的成长曲线点。"""

    round_no: int
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    weighted_k_score: float = 0.0
    scenario_id: Optional[str] = None
    scenario_title: str = ""
    is_high_risk: bool = False
    risk_flags: List[str] = field(default_factory=list)
    primary_skill_code: Optional[str] = None
    timestamp: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingReportCurvePointOutput | None":
        """把原始曲线点字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        round_value = payload.get("round_no")
        if round_value is None:
            return None

        scenario_id = payload.get("scenario_id")
        primary_skill_code = payload.get("primary_skill_code")
        return cls(
            round_no=int(round_value),
            k_state=_copy_dict(payload.get("k_state")),
            s_state=_copy_dict(payload.get("s_state")),
            weighted_k_score=float(payload.get("weighted_k_score", 0.0) or 0.0),
            scenario_id=str(scenario_id) if scenario_id is not None and str(scenario_id).strip() else None,
            scenario_title=str(payload.get("scenario_title") or ""),
            is_high_risk=bool(payload.get("is_high_risk", False)),
            risk_flags=[str(item) for item in payload.get("risk_flags", []) if str(item or "").strip()],
            primary_skill_code=(
                str(primary_skill_code) if primary_skill_code is not None and str(primary_skill_code).strip() else None
            ),
            timestamp=payload.get("timestamp"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定成长曲线点。"""
        payload = {
            "round_no": self.round_no,
            "k_state": _copy_dict(self.k_state),
            "s_state": _copy_dict(self.s_state),
            "weighted_k_score": self.weighted_k_score,
            "scenario_title": self.scenario_title,
            "is_high_risk": self.is_high_risk,
            "risk_flags": list(self.risk_flags),
            "timestamp": self.timestamp,
        }
        if self.scenario_id is not None:
            payload["scenario_id"] = self.scenario_id
        if self.primary_skill_code is not None:
            payload["primary_skill_code"] = self.primary_skill_code
        return payload


@dataclass(slots=True)
class TrainingReportSummaryOutput:
    """训练报告摘要：服务端直接产出可视化和复盘所需聚合结果。"""

    weighted_score_initial: float = 0.0
    weighted_score_final: float = 0.0
    weighted_score_delta: float = 0.0
    strongest_improved_skill_code: Optional[str] = None
    strongest_improved_skill_delta: float = 0.0
    weakest_skill_code: Optional[str] = None
    weakest_skill_score: float = 0.0
    dominant_risk_flag: Optional[str] = None
    high_risk_round_count: int = 0
    high_risk_round_nos: List[int] = field(default_factory=list)
    panic_trigger_round_count: int = 0
    source_exposed_round_count: int = 0
    editor_locked_round_count: int = 0
    high_risk_path_round_count: int = 0
    branch_transition_count: int = 0
    branch_transition_rounds: List[int] = field(default_factory=list)
    branch_transitions: List["TrainingBranchTransitionSummaryOutput | Dict[str, Any]"] = field(default_factory=list)
    risk_flag_counts: List["TrainingDiagnosticsCountItemOutput | Dict[str, Any]"] = field(default_factory=list)
    completed_scenario_ids: List[str] = field(default_factory=list)
    review_suggestions: List[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "TrainingReportSummaryOutput | None":
        """把原始报告摘要字典转换成稳定 DTO。"""
        if not isinstance(payload, dict):
            return None

        return cls(
            weighted_score_initial=float(payload.get("weighted_score_initial", 0.0) or 0.0),
            weighted_score_final=float(payload.get("weighted_score_final", 0.0) or 0.0),
            weighted_score_delta=float(payload.get("weighted_score_delta", 0.0) or 0.0),
            strongest_improved_skill_code=payload.get("strongest_improved_skill_code"),
            strongest_improved_skill_delta=float(payload.get("strongest_improved_skill_delta", 0.0) or 0.0),
            weakest_skill_code=payload.get("weakest_skill_code"),
            weakest_skill_score=float(payload.get("weakest_skill_score", 0.0) or 0.0),
            dominant_risk_flag=payload.get("dominant_risk_flag"),
            high_risk_round_count=_to_non_negative_int(payload.get("high_risk_round_count")),
            high_risk_round_nos=[max(int(item), 0) for item in payload.get("high_risk_round_nos", []) if item is not None],
            panic_trigger_round_count=_to_non_negative_int(payload.get("panic_trigger_round_count")),
            source_exposed_round_count=_to_non_negative_int(payload.get("source_exposed_round_count")),
            editor_locked_round_count=_to_non_negative_int(payload.get("editor_locked_round_count")),
            high_risk_path_round_count=_to_non_negative_int(payload.get("high_risk_path_round_count")),
            branch_transition_count=_to_non_negative_int(payload.get("branch_transition_count")),
            branch_transition_rounds=[max(int(item), 0) for item in payload.get("branch_transition_rounds", []) if item is not None],
            branch_transitions=_serialize_branch_transition_summary_list(payload.get("branch_transitions")),
            risk_flag_counts=_serialize_diagnostics_count_item_list(payload.get("risk_flag_counts")),
            completed_scenario_ids=[str(item) for item in payload.get("completed_scenario_ids", []) if str(item or "").strip()],
            review_suggestions=[str(item) for item in payload.get("review_suggestions", []) if str(item or "").strip()],
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定报告摘要。"""
        return {
            "weighted_score_initial": self.weighted_score_initial,
            "weighted_score_final": self.weighted_score_final,
            "weighted_score_delta": self.weighted_score_delta,
            "strongest_improved_skill_code": self.strongest_improved_skill_code,
            "strongest_improved_skill_delta": self.strongest_improved_skill_delta,
            "weakest_skill_code": self.weakest_skill_code,
            "weakest_skill_score": self.weakest_skill_score,
            "dominant_risk_flag": self.dominant_risk_flag,
            "high_risk_round_count": self.high_risk_round_count,
            "high_risk_round_nos": list(self.high_risk_round_nos),
            "panic_trigger_round_count": self.panic_trigger_round_count,
            "source_exposed_round_count": self.source_exposed_round_count,
            "editor_locked_round_count": self.editor_locked_round_count,
            "high_risk_path_round_count": self.high_risk_path_round_count,
            "branch_transition_count": self.branch_transition_count,
            "branch_transition_rounds": [int(item) for item in self.branch_transition_rounds],
            "branch_transitions": _serialize_branch_transition_summary_list(self.branch_transitions),
            "risk_flag_counts": _serialize_diagnostics_count_item_list(self.risk_flag_counts),
            "completed_scenario_ids": list(self.completed_scenario_ids),
            "review_suggestions": list(self.review_suggestions),
        }


@dataclass(slots=True)
class TrainingReportOutput:
    """训练报告结果。"""

    session_id: str
    status: str
    rounds: int
    k_state_final: Dict[str, float]
    s_state_final: Dict[str, float]
    improvement: float
    character_id: Optional[int] = None
    player_profile: Optional[TrainingPlayerProfileOutput | Dict[str, Any]] = None
    runtime_state: Optional["TrainingRuntimeStateOutput | Dict[str, Any]"] = None
    ending: Optional[Dict[str, Any]] = None
    summary: Optional["TrainingReportSummaryOutput | Dict[str, Any]"] = None
    ability_radar: List["TrainingReportMetricOutput | Dict[str, Any]"] = field(default_factory=list)
    state_radar: List["TrainingReportMetricOutput | Dict[str, Any]"] = field(default_factory=list)
    growth_curve: List["TrainingReportCurvePointOutput | Dict[str, Any]"] = field(default_factory=list)
    history: List[TrainingReportHistoryItemOutput] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """导出训练报告。"""
        payload = {
            "session_id": self.session_id,
            "character_id": self.character_id,
            "status": self.status,
            "rounds": self.rounds,
            "k_state_final": _copy_dict(self.k_state_final),
            "s_state_final": _copy_dict(self.s_state_final),
            "improvement": self.improvement,
            "ending": _copy_dict(self.ending) if self.ending is not None else None,
            "summary": _serialize_report_summary(self.summary),
            "ability_radar": _serialize_report_metric_list(self.ability_radar),
            "state_radar": _serialize_report_metric_list(self.state_radar),
            "growth_curve": _serialize_report_curve_point_list(self.growth_curve),
            "history": [item.to_dict() for item in self.history],
        }
        if self.player_profile is not None:
            payload["player_profile"] = _serialize_player_profile(self.player_profile)
        if self.runtime_state is not None:
            payload["runtime_state"] = _serialize_runtime_state(self.runtime_state)
        return payload


@dataclass(slots=True)
class TrainingDiagnosticsOutput:
    """训练诊断输出：聚合推荐、审计和 KT 观测工件。"""

    session_id: str
    status: str
    round_no: int
    character_id: Optional[int] = None
    player_profile: "TrainingPlayerProfileOutput | Dict[str, Any] | None" = None
    runtime_state: "TrainingRuntimeStateOutput | Dict[str, Any] | None" = None
    summary: "TrainingDiagnosticsSummaryOutput | Dict[str, Any] | None" = None
    recommendation_logs: List[TrainingRecommendationLogOutput | Dict[str, Any]] = field(default_factory=list)
    audit_events: List[TrainingAuditEventOutput | Dict[str, Any]] = field(default_factory=list)
    kt_observations: List[TrainingKtObservationOutput | Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定诊断字典。"""
        payload = {
            "session_id": self.session_id,
            "character_id": self.character_id,
            "status": self.status,
            "round_no": self.round_no,
            "summary": _serialize_diagnostics_summary(self.summary),
            "recommendation_logs": _serialize_recommendation_log_list(self.recommendation_logs),
            "audit_events": _serialize_audit_event_list(self.audit_events),
            "kt_observations": _serialize_kt_observation_list(self.kt_observations),
        }
        if self.player_profile is not None:
            payload["player_profile"] = _serialize_player_profile(self.player_profile)
        if self.runtime_state is not None:
            payload["runtime_state"] = _serialize_runtime_state(self.runtime_state)
        return payload
