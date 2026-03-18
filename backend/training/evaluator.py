"""训练回合评估器：负责 LLM 评估、规则校准与失败回退。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError

from llm import LLMException, LLMService
from training.constants import DEFAULT_EVAL_MODEL, DEFAULT_K_STATE, S_STATE_CODES, SKILL_CODES, TRAINING_RUNTIME_CONFIG
from training.contracts import RoundEvaluationPayload
from utils.logger import get_logger

logger = get_logger(__name__)


def _clamp(value: float, lower: float, upper: float) -> float:
    """把浮点数约束在指定区间。"""
    return max(lower, min(upper, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全解析浮点数，失败时返回默认值。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _round4(value: float) -> float:
    """统一控制小数精度，避免链路中数值漂移。"""
    return round(float(value), 4)


class _LLMOutput(BaseModel):
    """LLM 原始输出的最小校验模型。"""

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_flags: List[str] = Field(default_factory=list)
    skill_delta: Dict[str, float] = Field(default_factory=dict)
    s_delta: Dict[str, float] = Field(default_factory=dict)
    evidence: List[str] = Field(default_factory=list)


class TrainingRoundEvaluator:
    """训练回合评估器，保证输出可回退、可审计、可校准。"""

    def __init__(
        self,
        use_llm: bool | None = None,
        llm_provider: str | None = None,
        llm_service: Any = None,
        runtime_config: Any = None,
    ):
        self.runtime_config = runtime_config or TRAINING_RUNTIME_CONFIG
        self.rule_engine_config = self.runtime_config.rule_engine
        self.limits_config = self.runtime_config.limits
        self.messages_config = self.runtime_config.messages
        self.confidence_config = self.runtime_config.confidence
        self.use_llm = self.runtime_config.switches.use_llm_eval if use_llm is None else bool(use_llm)
        self.llm_provider = llm_provider or self.runtime_config.llm.provider or "auto"
        self._llm_service = None

        # 显式关闭时直接走规则链路，不初始化任何 LLM 资源。
        if not self.use_llm:
            return

        # 支持测试场景注入 mock service，避免真实网络依赖。
        if llm_service is not None:
            self._llm_service = llm_service
            return

        try:
            self._llm_service = LLMService(provider=self.llm_provider)
            logger.info(
                "training evaluator LLM enabled: provider=%s model=%s",
                self._llm_service.get_provider(),
                self._llm_service.get_model(),
            )
        except Exception as exc:
            self._llm_service = None
            logger.warning("training evaluator fallback to rules: llm init failed: %s", str(exc))

    def evaluate_round(
        self,
        user_input: str,
        scenario_id: str,
        round_no: int,
        k_before: Optional[Dict[str, float]] = None,
        s_before: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """评估单回合输入，并始终返回合法完整的评估结果。"""
        # 规则基线始终先跑，既是兜底，也是后续融合的校准基准。
        rules_result = self._evaluate_by_rules(user_input=user_input)

        if not self.use_llm:
            return self._finalize_payload(
                payload=rules_result,
                k_before=k_before,
                llm_model=self._get_default_eval_model(),
                eval_mode="rules_only",
            )

        if self._llm_service is None:
            fallback = dict(rules_result)
            fallback["fallback_reason"] = "llm_service_unavailable"
            return self._finalize_payload(
                payload=fallback,
                k_before=k_before,
                llm_model=self._get_default_eval_model(),
                eval_mode="rules_fallback",
            )

        # LLM 解析失败时自动回退到规则结果，并记录失败原因。
        llm_payload, llm_error = self._evaluate_by_llm(
            user_input=user_input,
            scenario_id=scenario_id,
            round_no=round_no,
            k_before=k_before,
            s_before=s_before,
        )
        if llm_payload is None:
            fallback = dict(rules_result)
            fallback["fallback_reason"] = llm_error or "llm_evaluation_failed"
            return self._finalize_payload(
                payload=fallback,
                k_before=k_before,
                llm_model=self._get_default_eval_model(),
                eval_mode="rules_fallback",
            )

        merged_payload = self._merge_with_calibration(rules_payload=rules_result, llm_payload=llm_payload)
        return self._finalize_payload(
            payload=merged_payload,
            k_before=k_before,
            llm_model=llm_payload.get("llm_model") or self._get_runtime_model_name(),
            eval_mode="llm_plus_rules",
        )

    def _evaluate_by_llm(
        self,
        user_input: str,
        scenario_id: str,
        round_no: int,
        k_before: Optional[Dict[str, float]],
        s_before: Optional[Dict[str, float]],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """调用 LLM 并把输出归一为内部评估结构。"""
        if self._llm_service is None:
            return None, "llm_service_unavailable"

        # 提示词里注入 round 上下文与状态快照，提升语义评估稳定性。
        messages = self._build_llm_messages(
            user_input=user_input,
            scenario_id=scenario_id,
            round_no=round_no,
            k_before=k_before,
            s_before=s_before,
        )

        try:
            response = self._llm_service.call_with_retry(
                messages=messages,
                max_tokens=self.runtime_config.llm.max_tokens,
                temperature=self.runtime_config.llm.temperature,
                max_retries=self.runtime_config.llm.max_retries,
                retry_delay=self.runtime_config.llm.retry_delay,
            )
            parsed = self._parse_llm_json(response.text)
            validated = _LLMOutput(**parsed)

            # 输出统一再归一化，避免模型字段缺失或超界值污染状态更新。
            normalized = {
                "confidence": _round4(_safe_float(validated.confidence, 0.5)),
                "risk_flags": self._normalize_risk_flags(validated.risk_flags),
                "skill_delta": self._normalize_skill_delta(validated.skill_delta),
                "s_delta": self._normalize_s_delta(validated.s_delta),
                "evidence": self._normalize_evidence(validated.evidence),
                "llm_model": self._get_model_from_response(response),
                "llm_raw_text": response.text,
            }
            return normalized, None
        except (LLMException, ValidationError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("training evaluator LLM parse/validate failed: %s", str(exc))
            return None, str(exc)
        except Exception as exc:
            logger.warning("training evaluator LLM unexpected failure: %s", str(exc))
            return None, str(exc)

    def _build_llm_messages(
        self,
        user_input: str,
        scenario_id: str,
        round_no: int,
        k_before: Optional[Dict[str, float]],
        s_before: Optional[Dict[str, float]],
    ) -> List[Dict[str, str]]:
        """构建面向 LLM 的结构化评估提示词。"""
        skill_template = {code: 0.0 for code in SKILL_CODES}
        s_template = {code: 0.0 for code in S_STATE_CODES}
        k_context = self._normalize_state_map(k_before, DEFAULT_K_STATE)
        s_context = self._normalize_state_map(s_before, {code: 0.0 for code in S_STATE_CODES})
        risk_flags = [
            self.runtime_config.risk_flags.unverified_publish,
            self.runtime_config.risk_flags.source_exposure,
            "emotional_language_risk",
            "rumor_spread_risk",
            "privacy_leak_risk",
        ]

        # 强制要求纯 JSON 输出，降低后续解析复杂度。
        system_prompt = (
            "You are a strict evaluator for journalism training rounds. "
            "Return JSON only, no markdown, no extra text. "
            "Output schema: "
            "{\"confidence\":0~1, \"risk_flags\":[...], \"skill_delta\":{K1..K8}, "
            "\"s_delta\":{credibility,accuracy,public_panic,source_safety,editor_trust,actionability}, "
            "\"evidence\":[1-6 concise reasons]}. "
            "All delta values must be in [-0.2, 0.2]."
        )
        user_prompt = (
            f"round_no={round_no}\n"
            f"scenario_id={scenario_id}\n"
            f"user_input={user_input}\n"
            f"k_before={json.dumps(k_context, ensure_ascii=False)}\n"
            f"s_before={json.dumps(s_context, ensure_ascii=False)}\n"
            f"skill_delta_template={json.dumps(skill_template, ensure_ascii=False)}\n"
            f"s_delta_template={json.dumps(s_template, ensure_ascii=False)}\n"
            f"Risk flags vocabulary suggestions: {', '.join(risk_flags)}.\n"
            "Return one JSON object only."
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _parse_llm_json(self, text: str) -> Dict[str, Any]:
        """兼容多种常见模型输出格式，并抽取 JSON 对象。"""
        if not text or not str(text).strip():
            raise ValueError("empty llm output")

        candidates: List[str] = [str(text).strip()]

        fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
        if fenced_match:
            candidates.insert(0, fenced_match.group(1).strip())

        object_match = re.search(r"\{[\s\S]*\}", text)
        if object_match:
            candidates.insert(0, object_match.group(0).strip())

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data

        raise ValueError("llm output is not valid json object")

    def _merge_with_calibration(self, rules_payload: Dict[str, Any], llm_payload: Dict[str, Any]) -> Dict[str, Any]:
        """融合规则评估与 LLM 评估，并施加硬惩罚和限幅。"""
        llm_skill_delta = self._normalize_skill_delta(llm_payload.get("skill_delta", {}))
        llm_s_delta = self._normalize_s_delta(llm_payload.get("s_delta", {}))
        rule_skill_delta = self._normalize_skill_delta(rules_payload.get("skill_delta", {}))
        rule_s_delta = self._normalize_s_delta(rules_payload.get("s_delta", {}))

        llm_weight = max(0.0, _safe_float(self.rule_engine_config.llm_merge_weights.get("llm"), 0.7))
        rule_weight = max(0.0, _safe_float(self.rule_engine_config.llm_merge_weights.get("rule"), 0.3))
        if llm_weight <= 0.0 and rule_weight <= 0.0:
            llm_weight = 0.7
            rule_weight = 0.3
        denominator = max(llm_weight + rule_weight, 1e-6)
        llm_weight = llm_weight / denominator
        rule_weight = rule_weight / denominator

        # 先融合再限幅，防止某一路极值直接主导状态更新。
        merged_skill_delta = {
            code: _round4(
                _clamp(
                    llm_skill_delta[code] * llm_weight + rule_skill_delta[code] * rule_weight,
                    -self.limits_config.max_skill_delta,
                    self.limits_config.max_skill_delta,
                )
            )
            for code in SKILL_CODES
        }
        merged_s_delta = {
            code: _round4(
                _clamp(
                    llm_s_delta[code] * llm_weight + rule_s_delta[code] * rule_weight,
                    -self.limits_config.max_s_delta,
                    self.limits_config.max_s_delta,
                )
            )
            for code in S_STATE_CODES
        }

        risk_flags = self._normalize_risk_flags(
            list(llm_payload.get("risk_flags", [])) + list(rules_payload.get("risk_flags", []))
        )
        hard_penalties = self._apply_hard_penalty(risk_flags, merged_skill_delta, merged_s_delta)

        llm_confidence = _safe_float(llm_payload.get("confidence"), 0.5)
        rules_confidence = _safe_float(rules_payload.get("confidence"), 0.5)
        confidence = _round4(
            _clamp(
                llm_confidence * self.confidence_config.llm_weight + rules_confidence * self.confidence_config.rule_weight,
                0.0,
                1.0,
            )
        )

        evidence = self._normalize_evidence(
            list(llm_payload.get("evidence", [])) + list(rules_payload.get("evidence", []))
        )

        merged = {
            "confidence": confidence,
            "risk_flags": risk_flags,
            "skill_delta": merged_skill_delta,
            "s_delta": merged_s_delta,
            "evidence": evidence,
            "calibration": {
                "llm_weight": _round4(llm_weight),
                "rule_weight": _round4(rule_weight),
                "hard_penalties": hard_penalties,
            },
        }
        if llm_payload.get("llm_raw_text"):
            merged["llm_raw_text"] = llm_payload.get("llm_raw_text")
        return merged

    def _apply_hard_penalty(
        self,
        risk_flags: List[str],
        skill_delta: Dict[str, float],
        s_delta: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """对触发底线风险的标记追加刚性惩罚。"""
        penalties: List[Dict[str, Any]] = []

        for penalty in self.runtime_config.hard_penalties:
            if penalty.flag not in risk_flags:
                continue

            for code, delta in penalty.skill_delta.items():
                if code not in skill_delta:
                    continue
                skill_delta[code] = _round4(
                    _clamp(
                        skill_delta.get(code, 0.0) + _safe_float(delta, 0.0),
                        -self.limits_config.max_skill_delta,
                        self.limits_config.max_skill_delta,
                    )
                )

            for code, delta in penalty.s_delta.items():
                if code not in s_delta:
                    continue
                s_delta[code] = _round4(
                    _clamp(
                        s_delta.get(code, 0.0) + _safe_float(delta, 0.0),
                        -self.limits_config.max_s_delta,
                        self.limits_config.max_s_delta,
                    )
                )

            penalties.append({"flag": penalty.flag, "note": penalty.note})

        return penalties

    def _evaluate_by_rules(self, user_input: str) -> Dict[str, Any]:
        """规则基线评估器，用于兜底与校准参考。"""
        text = (user_input or "").strip()
        lower = text.lower()

        # 默认轻微正向增益，鼓励参与；后续由命中规则做增减校正。
        skill_delta = {code: self.rule_engine_config.default_skill_delta for code in SKILL_CODES}
        s_delta = {code: 0.0 for code in S_STATE_CODES}
        risk_flags: List[str] = []
        evidence: List[str] = []

        for rule in self.rule_engine_config.rules:
            if not self._rule_matched(rule, text, lower):
                continue
            self._apply_rule(rule, skill_delta, s_delta, risk_flags, evidence)

        return {
            "confidence": self.rule_engine_config.base_confidence if text else 0.5,
            "risk_flags": self._normalize_risk_flags(risk_flags),
            "skill_delta": self._normalize_skill_delta(skill_delta),
            "s_delta": self._normalize_s_delta(s_delta),
            "evidence": self._normalize_evidence(evidence),
        }

    def _rule_matched(self, rule: Any, text: str, lower: str) -> bool:
        """判断一条规则是否命中当前输入。"""
        return any(keyword in text for keyword in rule.keywords) or any(
            keyword.lower() in lower for keyword in rule.keywords_en
        )

    def _apply_rule(
        self,
        rule: Any,
        skill_delta: Dict[str, float],
        s_delta: Dict[str, float],
        risk_flags: List[str],
        evidence: List[str],
    ) -> None:
        """把规则配置映射到当前回合的增减分结果。"""
        for code, delta in rule.skill_delta.items():
            if code not in skill_delta:
                continue
            skill_delta[code] += _safe_float(delta, 0.0)

        for code, delta in rule.s_delta.items():
            if code not in s_delta:
                continue
            s_delta[code] += _safe_float(delta, 0.0)

        for risk_flag in rule.risk_flags:
            risk_flags.append(str(risk_flag))

        if rule.evidence:
            evidence.append(str(rule.evidence))

    def _finalize_payload(
        self,
        payload: Dict[str, Any],
        k_before: Optional[Dict[str, float]],
        llm_model: str,
        eval_mode: str,
    ) -> Dict[str, Any]:
        """在最终出口再次做一轮归一化，保证下游拿到稳定契约。"""
        skill_delta = self._normalize_skill_delta(payload.get("skill_delta", {}))
        s_delta = self._normalize_s_delta(payload.get("s_delta", {}))
        confidence = _round4(_clamp(_safe_float(payload.get("confidence"), 0.5), 0.0, 1.0))

        base_k = self._normalize_state_map(k_before, DEFAULT_K_STATE)
        preview = {
            code: _round4(_clamp(base_k[code] + skill_delta[code], 0.0, 1.0))
            for code in SKILL_CODES
        }

        result = {
            "llm_model": llm_model or self._get_default_eval_model(),
            "confidence": confidence,
            "risk_flags": self._normalize_risk_flags(payload.get("risk_flags", [])),
            "skill_delta": skill_delta,
            "s_delta": s_delta,
            "evidence": self._normalize_evidence(payload.get("evidence", [])),
            "skill_scores_preview": preview,
            "eval_mode": eval_mode,
        }
        if payload.get("fallback_reason"):
            result["fallback_reason"] = str(payload.get("fallback_reason"))
        if payload.get("calibration"):
            result["calibration"] = payload.get("calibration")
        if payload.get("llm_raw_text"):
            result["llm_raw_text"] = payload.get("llm_raw_text")

        # 统一走共享契约，保证服务层、存储层、报表层看到同一结构。
        return RoundEvaluationPayload.from_raw(result).to_dict()

    def _normalize_skill_delta(self, raw: Dict[str, Any]) -> Dict[str, float]:
        """归一化技能增减分，并做保护限幅。"""
        normalized: Dict[str, float] = {}
        source = raw or {}
        for code in SKILL_CODES:
            value = _safe_float(source.get(code), 0.0)
            normalized[code] = _round4(
                _clamp(value, -self.limits_config.max_skill_delta, self.limits_config.max_skill_delta)
            )
        return normalized

    def _normalize_s_delta(self, raw: Dict[str, Any]) -> Dict[str, float]:
        """归一化剧情状态增减分，并做保护限幅。"""
        normalized: Dict[str, float] = {}
        source = raw or {}
        for code in S_STATE_CODES:
            value = _safe_float(source.get(code), 0.0)
            normalized[code] = _round4(
                _clamp(value, -self.limits_config.max_s_delta, self.limits_config.max_s_delta)
            )
        return normalized

    def _normalize_risk_flags(self, flags: Any) -> List[str]:
        """统一风险标签格式，减少下游判断分支。"""
        if not isinstance(flags, list):
            return []

        normalized: List[str] = []
        for item in flags:
            text = str(item or "").strip()
            if not text:
                continue
            flag = re.sub(r"[^a-zA-Z0-9_]+", "_", text.lower()).strip("_")
            if not flag:
                flag = text[:64]
            if flag not in normalized:
                normalized.append(flag)
        return normalized

    def _normalize_evidence(self, evidence: Any) -> List[str]:
        """统一证据文案列表，并保证至少有一个兜底文案。"""
        if not isinstance(evidence, list):
            evidence = []

        normalized: List[str] = []
        for item in evidence:
            text = str(item or "").strip()
            if not text:
                continue
            if text not in normalized:
                normalized.append(text)
            if len(normalized) >= 8:
                break

        if not normalized:
            normalized.append(self.messages_config.empty_evidence_text)
        return normalized

    def _normalize_state_map(self, source: Optional[Dict[str, float]], defaults: Dict[str, float]) -> Dict[str, float]:
        """把任意状态字典归一为完整结构。"""
        state = dict(defaults)
        if isinstance(source, dict):
            for key in defaults.keys():
                if key in source:
                    state[key] = _round4(_safe_float(source.get(key), defaults[key]))
        return state

    def _get_default_eval_model(self) -> str:
        """读取当前默认评估模型名。"""
        return self.runtime_config.llm.default_eval_model or DEFAULT_EVAL_MODEL

    def _get_runtime_model_name(self) -> str:
        """优先读取已初始化的运行时模型名。"""
        if self._llm_service is not None:
            try:
                return self._llm_service.get_model()
            except Exception:
                pass
        return self._get_default_eval_model()

    def _get_model_from_response(self, response: Any) -> str:
        """从响应对象中提取模型名，没有时回退到运行时配置。"""
        model = getattr(response, "model", None)
        if model:
            return str(model)
        return self._get_runtime_model_name()
