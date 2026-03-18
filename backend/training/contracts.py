"""训练评估结果的数据契约。"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from training.constants import (
    DEFAULT_EVAL_MODEL,
    DEFAULT_K_STATE,
    S_STATE_CODES,
    SKILL_CODES,
    TRAINING_EMPTY_EVIDENCE_TEXT,
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    """安全解析整数，避免脏数据把契约层直接打断。"""
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _normalize_str_list(values: Any, limit: int = 12) -> List[str]:
    if not isinstance(values, list):
        return []

    normalized: List[str] = []
    for item in values:
        text = str(item or "").strip()
        if not text:
            continue
        if text in normalized:
            continue
        normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def _normalize_optional_str(value: Any) -> Optional[str]:
    """把任意输入规整为可选字符串，统一空值口径。"""
    text = str(value or "").strip()
    return text or None


def _normalize_risk_flags(values: Any) -> List[str]:
    """统一风险标签格式，避免下游判断口径不一致。"""
    normalized: List[str] = []
    for item in _normalize_str_list(values, limit=16):
        flag = re.sub(r"[^a-zA-Z0-9_]+", "_", item.lower()).strip("_")
        if not flag:
            continue
        if flag not in normalized:
            normalized.append(flag)
    return normalized


def _normalize_delta_map(raw: Any, keys: List[str] | tuple) -> Dict[str, float]:
    source = raw if isinstance(raw, dict) else {}
    return {str(key): round(_safe_float(source.get(key), 0.0), 4) for key in keys}


def _normalize_bool(value: Any) -> bool:
    """统一布尔值解析，兼容字符串和数字输入。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _normalize_skill_preview(raw: Any, skill_delta: Dict[str, float]) -> Dict[str, float]:
    source = raw if isinstance(raw, dict) else {}
    preview: Dict[str, float] = {}
    for code in SKILL_CODES:
        default_value = DEFAULT_K_STATE.get(code, 0.0) + skill_delta.get(code, 0.0)
        value = _safe_float(source.get(code), default_value)
        preview[code] = round(_clamp(value, 0.0, 1.0), 4)
    return preview


class RoundEvaluationPayload(BaseModel):
    """评估层、服务层、存储层共用的标准评估载荷。"""

    llm_model: str = DEFAULT_EVAL_MODEL
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_flags: List[str] = Field(default_factory=list)
    skill_delta: Dict[str, float] = Field(default_factory=dict)
    s_delta: Dict[str, float] = Field(default_factory=dict)
    evidence: List[str] = Field(default_factory=list)
    skill_scores_preview: Dict[str, float] = Field(default_factory=dict)
    eval_mode: str = "rules_only"
    fallback_reason: Optional[str] = None
    calibration: Optional[Dict[str, Any]] = None
    llm_raw_text: Optional[str] = None

    @classmethod
    def from_raw(cls, payload: Dict[str, Any] | None) -> "RoundEvaluationPayload":
        """对任意评估字典做归一化与校验。"""
        source = payload if isinstance(payload, dict) else {}
        skill_delta = _normalize_delta_map(source.get("skill_delta"), SKILL_CODES)
        normalized = {
            "llm_model": str(source.get("llm_model") or DEFAULT_EVAL_MODEL),
            "confidence": round(_clamp(_safe_float(source.get("confidence"), 0.5), 0.0, 1.0), 4),
            "risk_flags": _normalize_risk_flags(source.get("risk_flags")),
            "skill_delta": skill_delta,
            "s_delta": _normalize_delta_map(source.get("s_delta"), S_STATE_CODES),
            "evidence": _normalize_str_list(source.get("evidence"), limit=8) or [TRAINING_EMPTY_EVIDENCE_TEXT],
            "skill_scores_preview": _normalize_skill_preview(source.get("skill_scores_preview"), skill_delta),
            "eval_mode": str(source.get("eval_mode") or "rules_only"),
        }

        fallback_reason = source.get("fallback_reason")
        if fallback_reason is not None:
            normalized["fallback_reason"] = str(fallback_reason)

        calibration = source.get("calibration")
        if isinstance(calibration, dict):
            normalized["calibration"] = calibration

        llm_raw_text = source.get("llm_raw_text")
        if llm_raw_text is not None:
            normalized["llm_raw_text"] = str(llm_raw_text)

        return cls(**normalized)

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定字典，兼容 Pydantic v1/v2。"""
        if hasattr(self, "model_dump"):
            return self.model_dump(exclude_none=True)
        return self.dict(exclude_none=True)


class DecisionCandidatePayload(BaseModel):
    """推荐候选题的稳定契约。"""

    scenario_id: str
    title: str = ""
    rank: Optional[int] = None
    rank_score: float = 0.0
    is_selected: bool = False
    is_recommended: bool = False

    @classmethod
    def from_raw(cls, payload: Dict[str, Any] | None) -> "DecisionCandidatePayload | None":
        """把任意候选题字典规整成统一结构。"""
        if not isinstance(payload, dict):
            return None

        scenario_id = str(payload.get("scenario_id") or payload.get("id") or "").strip()
        if not scenario_id:
            return None

        rank_value = payload.get("rank")
        return cls(
            scenario_id=scenario_id,
            title=str(payload.get("title") or scenario_id),
            rank=_safe_int(rank_value),
            rank_score=round(_safe_float(payload.get("rank_score"), 0.0), 4),
            is_selected=_normalize_bool(payload.get("is_selected")),
            is_recommended=_normalize_bool(payload.get("is_recommended")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定候选题字典。"""
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


class ScenarioRecommendationLogPayload(BaseModel):
    """推荐日志载荷契约，避免日志字段散落在服务层。"""

    training_mode: str = "guided"
    selection_source: Optional[str] = None
    recommended_scenario_id: Optional[str] = None
    selected_scenario_id: Optional[str] = None
    candidate_pool: List[DecisionCandidatePayload] = Field(default_factory=list)
    recommended_recommendation: Dict[str, Any] = Field(default_factory=dict)
    selected_recommendation: Dict[str, Any] = Field(default_factory=dict)
    decision_context: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, payload: Dict[str, Any] | None) -> "ScenarioRecommendationLogPayload":
        """对推荐日志做归一化，保证后续持久化字段形状稳定。"""
        source = payload if isinstance(payload, dict) else {}

        candidate_pool: List[DecisionCandidatePayload] = []
        for item in source.get("candidate_pool", []) or []:
            normalized_item = DecisionCandidatePayload.from_raw(item)
            if normalized_item is not None:
                candidate_pool.append(normalized_item)

        return cls(
            training_mode=str(source.get("training_mode") or "guided"),
            selection_source=_normalize_optional_str(source.get("selection_source")),
            recommended_scenario_id=_normalize_optional_str(source.get("recommended_scenario_id")),
            selected_scenario_id=_normalize_optional_str(source.get("selected_scenario_id")),
            candidate_pool=candidate_pool,
            recommended_recommendation=dict(source.get("recommended_recommendation", {}) or {}),
            selected_recommendation=dict(source.get("selected_recommendation", {}) or {}),
            decision_context=dict(source.get("decision_context", {}) or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定推荐日志字典。"""
        payload = {
            "training_mode": self.training_mode,
            "candidate_pool": [item.to_dict() for item in self.candidate_pool],
            "recommended_recommendation": dict(self.recommended_recommendation),
            "selected_recommendation": dict(self.selected_recommendation),
            "decision_context": dict(self.decision_context),
        }
        if self.selection_source is not None:
            payload["selection_source"] = self.selection_source
        if self.recommended_scenario_id is not None:
            payload["recommended_scenario_id"] = self.recommended_scenario_id
        if self.selected_scenario_id is not None:
            payload["selected_scenario_id"] = self.selected_scenario_id
        return payload


class TrainingAuditEventPayload(BaseModel):
    """训练审计事件契约。"""

    event_type: str
    round_no: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, payload: Dict[str, Any] | None) -> "TrainingAuditEventPayload | None":
        """对事件字典做归一化；无事件类型时直接丢弃。"""
        if not isinstance(payload, dict):
            return None

        event_type = str(payload.get("event_type") or "").strip()
        if not event_type:
            return None

        round_no = payload.get("round_no")
        return cls(
            event_type=event_type,
            round_no=_safe_int(round_no),
            payload=dict(payload.get("payload", {}) or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定审计事件字典。"""
        payload = {
            "event_type": self.event_type,
            "payload": dict(self.payload),
        }
        if self.round_no is not None:
            payload["round_no"] = self.round_no
        return payload


class RoundMetricObservationPayload(BaseModel):
    """单个能力/状态观测项契约。"""

    code: str
    before: float = 0.0
    delta: float = 0.0
    after: float = 0.0
    is_target: bool = False

    @classmethod
    def from_raw(cls, payload: Dict[str, Any] | None) -> "RoundMetricObservationPayload | None":
        """把任意观测项字典规整成统一结构。"""
        if not isinstance(payload, dict):
            return None

        code = str(payload.get("code") or "").strip()
        if not code:
            return None

        return cls(
            code=code,
            before=round(_safe_float(payload.get("before"), 0.0), 4),
            delta=round(_safe_float(payload.get("delta"), 0.0), 4),
            after=round(_safe_float(payload.get("after"), 0.0), 4),
            is_target=_normalize_bool(payload.get("is_target")),
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


class KtObservationPayload(BaseModel):
    """KT 结构化观测契约。"""

    training_mode: str = "guided"
    scenario_id: str
    scenario_title: str = ""
    primary_skill_code: Optional[str] = None
    primary_risk_flag: Optional[str] = None
    is_high_risk: bool = False
    target_skills: List[str] = Field(default_factory=list)
    weak_skills_before: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    focus_tags: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    skill_observations: List[RoundMetricObservationPayload] = Field(default_factory=list)
    state_observations: List[RoundMetricObservationPayload] = Field(default_factory=list)
    observation_summary: str = ""

    @classmethod
    def from_raw(cls, payload: Dict[str, Any] | None) -> "KtObservationPayload | None":
        """对 KT 观测做归一化；缺少场景 ID 时不生成观测。"""
        if not isinstance(payload, dict):
            return None

        scenario_id = str(payload.get("scenario_id") or "").strip()
        if not scenario_id:
            return None

        skill_observations: List[RoundMetricObservationPayload] = []
        for item in payload.get("skill_observations", []) or []:
            normalized_item = RoundMetricObservationPayload.from_raw(item)
            if normalized_item is not None:
                skill_observations.append(normalized_item)

        state_observations: List[RoundMetricObservationPayload] = []
        for item in payload.get("state_observations", []) or []:
            normalized_item = RoundMetricObservationPayload.from_raw(item)
            if normalized_item is not None:
                state_observations.append(normalized_item)

        return cls(
            training_mode=str(payload.get("training_mode") or "guided"),
            scenario_id=scenario_id,
            scenario_title=str(payload.get("scenario_title") or ""),
            primary_skill_code=_normalize_optional_str(payload.get("primary_skill_code")),
            primary_risk_flag=_normalize_optional_str(payload.get("primary_risk_flag")),
            is_high_risk=_normalize_bool(payload.get("is_high_risk")),
            target_skills=_normalize_str_list(payload.get("target_skills"), limit=8),
            weak_skills_before=_normalize_str_list(payload.get("weak_skills_before"), limit=8),
            risk_flags=_normalize_risk_flags(payload.get("risk_flags")),
            focus_tags=_normalize_str_list(payload.get("focus_tags"), limit=12),
            evidence=_normalize_str_list(payload.get("evidence"), limit=8) or [TRAINING_EMPTY_EVIDENCE_TEXT],
            skill_observations=skill_observations,
            state_observations=state_observations,
            observation_summary=str(payload.get("observation_summary") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定 KT 观测字典。"""
        payload = {
            "training_mode": self.training_mode,
            "scenario_id": self.scenario_id,
            "scenario_title": self.scenario_title,
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
        if self.primary_skill_code is not None:
            payload["primary_skill_code"] = self.primary_skill_code
        if self.primary_risk_flag is not None:
            payload["primary_risk_flag"] = self.primary_risk_flag
        return payload
