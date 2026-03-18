"""训练系统常量导出层。"""

from __future__ import annotations

from typing import Dict, Tuple

from training.config_loader import get_training_runtime_config, model_to_dict

TRAINING_RUNTIME_CONFIG = get_training_runtime_config()


def _round4(value: float) -> float:
    """统一处理浮点导出精度。"""
    return round(float(value), 4)


def _build_default_k_state() -> Dict[str, float]:
    """根据配置构建默认 K 状态。"""
    defaults = TRAINING_RUNTIME_CONFIG.defaults
    return {
        code: _round4(defaults.default_k_state.get(code, defaults.default_k_value))
        for code in TRAINING_RUNTIME_CONFIG.skill_codes
    }


def _build_default_s_state() -> Dict[str, float]:
    """根据配置构建默认 S 状态。"""
    defaults = TRAINING_RUNTIME_CONFIG.defaults
    return {
        code: _round4(defaults.default_s_state.get(code, 0.0))
        for code in TRAINING_RUNTIME_CONFIG.s_state_codes
    }


# 维度编码与快照映射。
SKILL_CODES: Tuple[str, ...] = tuple(TRAINING_RUNTIME_CONFIG.skill_codes)
S_STATE_CODES: Tuple[str, ...] = tuple(TRAINING_RUNTIME_CONFIG.s_state_codes)
SKILL_SNAPSHOT_FIELDS: Dict[str, str] = dict(TRAINING_RUNTIME_CONFIG.skill_snapshot_fields)
S_STATE_SNAPSHOT_FIELDS: Dict[str, str] = dict(TRAINING_RUNTIME_CONFIG.s_state_snapshot_fields)

# 场景配置。
TRAINING_SCENARIO_VERSION = TRAINING_RUNTIME_CONFIG.scenario.version
TRAINING_DEFAULT_SCENARIO_SEQUENCE = [
    model_to_dict(item) for item in TRAINING_RUNTIME_CONFIG.scenario.default_sequence
]

# 默认初始状态。
DEFAULT_K_VALUE = _round4(TRAINING_RUNTIME_CONFIG.defaults.default_k_value)
DEFAULT_K_STATE: Dict[str, float] = _build_default_k_state()
DEFAULT_S_STATE: Dict[str, float] = _build_default_s_state()

# 技能权重。
SKILL_WEIGHTS: Dict[str, float] = {
    code: _round4(TRAINING_RUNTIME_CONFIG.skill_weights.get(code, 0.0))
    for code in SKILL_CODES
}

# 开关与 LLM 运行参数。
TRAINING_USE_LLM_EVAL = bool(TRAINING_RUNTIME_CONFIG.switches.use_llm_eval)
TRAINING_ENFORCE_SCENARIO_ORDER = bool(TRAINING_RUNTIME_CONFIG.switches.enforce_scenario_order)
TRAINING_LLM_PROVIDER = TRAINING_RUNTIME_CONFIG.llm.provider
DEFAULT_EVAL_MODEL = TRAINING_RUNTIME_CONFIG.llm.default_eval_model
TRAINING_LLM_MAX_TOKENS = int(TRAINING_RUNTIME_CONFIG.llm.max_tokens)
TRAINING_LLM_TEMPERATURE = float(TRAINING_RUNTIME_CONFIG.llm.temperature)
TRAINING_LLM_MAX_RETRIES = int(TRAINING_RUNTIME_CONFIG.llm.max_retries)
TRAINING_LLM_RETRY_DELAY = float(TRAINING_RUNTIME_CONFIG.llm.retry_delay)

# 状态保护与默认文案。
TRAINING_MAX_SKILL_DELTA = float(TRAINING_RUNTIME_CONFIG.limits.max_skill_delta)
TRAINING_MAX_S_DELTA = float(TRAINING_RUNTIME_CONFIG.limits.max_s_delta)
TRAINING_EMPTY_EVIDENCE_TEXT = TRAINING_RUNTIME_CONFIG.messages.empty_evidence_text
TRAINING_DUPLICATE_FALLBACK_EVIDENCE = TRAINING_RUNTIME_CONFIG.messages.duplicate_fallback_evidence

# 风险标记与置信度权重。
TRAINING_RISK_FLAG_UNVERIFIED_PUBLISH = TRAINING_RUNTIME_CONFIG.risk_flags.unverified_publish
TRAINING_RISK_FLAG_SOURCE_EXPOSURE = TRAINING_RUNTIME_CONFIG.risk_flags.source_exposure
TRAINING_CONFIDENCE_LLM_WEIGHT = float(TRAINING_RUNTIME_CONFIG.confidence.llm_weight)
TRAINING_CONFIDENCE_RULE_WEIGHT = float(TRAINING_RUNTIME_CONFIG.confidence.rule_weight)

# 规则引擎与结局配置导出，供旧接口兼容和少量外部模块使用。
TRAINING_RULE_ENGINE_CONFIG = TRAINING_RUNTIME_CONFIG.rule_engine
TRAINING_HARD_PENALTY_CONFIGS = tuple(TRAINING_RUNTIME_CONFIG.hard_penalties)
TRAINING_ENDING_CONFIG = TRAINING_RUNTIME_CONFIG.ending
TRAINING_RECOMMENDATION_CONFIG = TRAINING_RUNTIME_CONFIG.recommendation
TRAINING_FLOW_CONFIG = TRAINING_RUNTIME_CONFIG.flow
TRAINING_REPORTING_CONFIG = TRAINING_RUNTIME_CONFIG.reporting

TRAINING_EVAL_LLM_WEIGHT = float(TRAINING_RUNTIME_CONFIG.rule_engine.llm_merge_weights.get("llm", 0.7))
TRAINING_EVAL_RULE_WEIGHT = float(TRAINING_RUNTIME_CONFIG.rule_engine.llm_merge_weights.get("rule", 0.3))

TRAINING_ENDING_SEVERE_FLAGS: Tuple[str, ...] = tuple(TRAINING_RUNTIME_CONFIG.ending.severe_flags)
TRAINING_ENDING_FAIL_SOURCE_SAFETY = float(TRAINING_RUNTIME_CONFIG.ending.thresholds.fail_source_safety)
TRAINING_ENDING_FAIL_PUBLIC_PANIC = float(TRAINING_RUNTIME_CONFIG.ending.thresholds.fail_public_panic)
TRAINING_ENDING_EXCELLENT_SCORE = float(TRAINING_RUNTIME_CONFIG.ending.thresholds.excellent_score)
TRAINING_ENDING_EXCELLENT_ACCURACY = float(TRAINING_RUNTIME_CONFIG.ending.thresholds.excellent_accuracy)
TRAINING_ENDING_EXCELLENT_SOURCE_SAFETY = float(TRAINING_RUNTIME_CONFIG.ending.thresholds.excellent_source_safety)
TRAINING_ENDING_RECOVERY_SCORE = float(TRAINING_RUNTIME_CONFIG.ending.thresholds.recovery_score)
TRAINING_ENDING_RECOVERY_IMPROVEMENT = float(TRAINING_RUNTIME_CONFIG.ending.thresholds.recovery_improvement)
TRAINING_ENDING_STEADY_SCORE = float(TRAINING_RUNTIME_CONFIG.ending.thresholds.steady_score)
TRAINING_ENDING_TYPE_COSTLY = TRAINING_RUNTIME_CONFIG.ending.types.costly
TRAINING_ENDING_TYPE_EXCELLENT = TRAINING_RUNTIME_CONFIG.ending.types.excellent
TRAINING_ENDING_TYPE_RECOVERY = TRAINING_RUNTIME_CONFIG.ending.types.recovery
TRAINING_ENDING_TYPE_STEADY = TRAINING_RUNTIME_CONFIG.ending.types.steady
TRAINING_ENDING_TYPE_FAIL = TRAINING_RUNTIME_CONFIG.ending.types.fail
