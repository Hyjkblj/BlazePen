"""训练运行时配置加载器。"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field

TRAINING_RUNTIME_CONFIG_PATH_ENV = "TRAINING_RUNTIME_CONFIG_PATH"
DEFAULT_TRAINING_RUNTIME_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "training_runtime_config.json"
SUPPORTED_TRAINING_MODES = ("guided", "self-paced", "adaptive")


def _as_bool(value: str | None, default: bool = False) -> bool:
    """统一解析布尔型环境变量。"""
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _model_validate(model_cls: type[BaseModel], payload: Dict[str, Any]) -> BaseModel:
    """兼容 Pydantic v1 和 v2 的模型校验入口。"""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(payload)
    return model_cls.parse_obj(payload)


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """兼容 Pydantic v1 和 v2 的字典导出入口。"""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def model_copy(model: BaseModel) -> BaseModel:
    """兼容 Pydantic v1 和 v2 的深拷贝入口。"""
    if hasattr(model, "model_copy"):
        return model.model_copy(deep=True)
    return model.copy(deep=True)


def _normalize_training_mode_name(value: Any) -> str | None:
    """把训练模式名称归一到稳定写法，供配置校验复用。"""
    raw_text = str(value or "").strip()
    if not raw_text:
        return None
    normalized = re.sub(r"[\s_]+", "-", raw_text.lower())
    if normalized not in SUPPORTED_TRAINING_MODES:
        return None
    return normalized


class ScenarioItemConfig(BaseModel):
    """单个场景配置。"""

    id: str
    title: str


class ScenarioConfig(BaseModel):
    """场景序列配置。"""

    version: str = "training_scenario_v1"
    default_sequence: List[ScenarioItemConfig] = Field(default_factory=list)


class DefaultsConfig(BaseModel):
    """默认 K/S 初始状态配置。"""

    default_k_value: float = 0.45
    default_k_state: Dict[str, float] = Field(default_factory=dict)
    default_s_state: Dict[str, float] = Field(default_factory=dict)


class SwitchesConfig(BaseModel):
    """功能开关配置。"""

    use_llm_eval: bool = False
    enforce_scenario_order: bool = True


class LlmConfig(BaseModel):
    """LLM 运行参数配置。"""

    provider: str = "auto"
    default_eval_model: str = "rules_v1"
    max_tokens: int = 700
    temperature: float = 0.2
    max_retries: int = 2
    retry_delay: float = 0.8


class LimitsConfig(BaseModel):
    """单回合状态变化保护阈值。"""

    max_skill_delta: float = 0.2
    max_s_delta: float = 0.2


class MessagesConfig(BaseModel):
    """默认文案配置。"""

    empty_evidence_text: str = "本轮输入已纳入训练评估"
    duplicate_fallback_evidence: str = "复用已落库回合结果"


class RiskFlagsConfig(BaseModel):
    """风险标记配置。"""

    unverified_publish: str = "high_risk_unverified_publish"
    source_exposure: str = "source_exposure_risk"


class ConfidenceConfig(BaseModel):
    """置信度融合权重配置。"""

    llm_weight: float = 0.65
    rule_weight: float = 0.35


class HardPenaltyConfig(BaseModel):
    """高风险硬惩罚配置。"""

    flag: str
    skill_delta: Dict[str, float] = Field(default_factory=dict)
    s_delta: Dict[str, float] = Field(default_factory=dict)
    note: str = ""


class RuleConfig(BaseModel):
    """单条规则评估配置。"""

    id: str
    keywords: List[str] = Field(default_factory=list)
    keywords_en: List[str] = Field(default_factory=list)
    skill_delta: Dict[str, float] = Field(default_factory=dict)
    s_delta: Dict[str, float] = Field(default_factory=dict)
    risk_flags: List[str] = Field(default_factory=list)
    evidence: str = ""


class RuleEngineConfig(BaseModel):
    """规则评估器配置。"""

    base_confidence: float = 0.78
    default_skill_delta: float = 0.01
    llm_merge_weights: Dict[str, float] = Field(default_factory=lambda: {"llm": 0.7, "rule": 0.3})
    rules: List[RuleConfig] = Field(default_factory=list)


class EndingThresholdsConfig(BaseModel):
    """结局阈值配置。"""

    fail_source_safety: float = 0.35
    fail_public_panic: float = 0.75
    excellent_score: float = 0.82
    excellent_accuracy: float = 0.8
    excellent_source_safety: float = 0.85
    recovery_score: float = 0.64
    recovery_improvement: float = 0.18
    steady_score: float = 0.7


class EndingTypesConfig(BaseModel):
    """结局名称配置。"""

    costly: str = "代价沉重"
    excellent: str = "史笔如铁"
    recovery: str = "逆风修正"
    steady: str = "艰难守真"
    fail: str = "失真扩散"


class EndingConfig(BaseModel):
    """结局策略配置。"""

    severe_flags: List[str] = Field(default_factory=list)
    thresholds: EndingThresholdsConfig = Field(default_factory=EndingThresholdsConfig)
    types: EndingTypesConfig = Field(default_factory=EndingTypesConfig)


class RecommendationWeightsConfig(BaseModel):
    """推荐评分权重配置。"""

    weakness: float = 0.7
    state_boost: float = 0.3
    recent_risk: float = 0.2
    phase_alignment: float = 0.08


class RecommendationStateBoostConfig(BaseModel):
    """状态触发的技能加权配置。"""

    state_key: str
    trigger: str = "lt"
    threshold: float = 0.0
    boost_skills: List[str] = Field(default_factory=list)
    boost: float = 0.0
    reason: str = ""


class RecommendationRiskBoostConfig(BaseModel):
    """最近风险信号触发的技能加权配置。"""

    risk_flag: str
    boost_skills: List[str] = Field(default_factory=list)
    boost: float = 0.0
    consecutive_bonus: float = 0.0
    reason: str = ""


class RecommendationPhaseBoostConfig(BaseModel):
    """剧情阶段对齐加权配置。"""

    # `distance` 保留给旧的“按序列邻近度加权”逻辑，作为没有阶段标签时的兜底。
    distance: int | None = Field(default=None, ge=0)
    # `current_phase_tags` 与 `scenario_phase_tags` 用于新的“阶段窗口 + 场景阶段标签”匹配。
    current_phase_tags: List[str] = Field(default_factory=list)
    scenario_phase_tags: List[str] = Field(default_factory=list)
    boost: float = 0.0
    reason: str = ""


class RecommendationConfig(BaseModel):
    """下一题推荐策略配置。"""

    enabled_modes: List[str] = Field(default_factory=lambda: ["adaptive"])
    strict_modes: List[str] = Field(default_factory=lambda: ["adaptive"])
    candidate_limit: int = Field(default=3, ge=1)
    fallback_mode: str = "guided"
    recent_risk_window: int = Field(default=2, ge=1)
    weights: RecommendationWeightsConfig = Field(default_factory=RecommendationWeightsConfig)
    state_boosts: List[RecommendationStateBoostConfig] = Field(default_factory=list)
    risk_boosts: List[RecommendationRiskBoostConfig] = Field(default_factory=list)
    phase_boosts: List[RecommendationPhaseBoostConfig] = Field(default_factory=list)


class FlowForcedRoundConfig(BaseModel):
    """关键节点强制触发配置。"""

    round_no: int = Field(ge=1)
    scenario_id: str
    modes: List[str] = Field(default_factory=list)
    reason: str = ""


class FlowStageWindowConfig(BaseModel):
    """训练阶段窗口配置。"""

    start_round: int = Field(default=1, ge=1)
    end_round: int | None = Field(default=None, ge=1)
    phase_tags: List[str] = Field(default_factory=list)
    modes: List[str] = Field(default_factory=list)
    reason: str = ""


class FlowConfig(BaseModel):
    """训练流程编排配置。"""

    stage_windows: List[FlowStageWindowConfig] = Field(default_factory=list)
    forced_rounds: List[FlowForcedRoundConfig] = Field(default_factory=list)


class ReportingThresholdsConfig(BaseModel):
    """训练报告建议阈值配置。"""

    weak_skill_threshold: float = 0.6
    strong_improvement_threshold: float = 0.1
    limited_improvement_threshold: float = 0.03


class ReportingConfig(BaseModel):
    """训练报告聚合配置。"""

    max_review_suggestions: int = 4
    high_risk_round_preview_limit: int = 3
    thresholds: ReportingThresholdsConfig = Field(default_factory=ReportingThresholdsConfig)


class TrainingRuntimeConfig(BaseModel):
    """训练系统运行时总配置。"""

    skill_codes: List[str] = Field(default_factory=list)
    s_state_codes: List[str] = Field(default_factory=list)
    skill_snapshot_fields: Dict[str, str] = Field(default_factory=dict)
    s_state_snapshot_fields: Dict[str, str] = Field(default_factory=dict)
    scenario: ScenarioConfig = Field(default_factory=ScenarioConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    skill_weights: Dict[str, float] = Field(default_factory=dict)
    switches: SwitchesConfig = Field(default_factory=SwitchesConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    messages: MessagesConfig = Field(default_factory=MessagesConfig)
    risk_flags: RiskFlagsConfig = Field(default_factory=RiskFlagsConfig)
    confidence: ConfidenceConfig = Field(default_factory=ConfidenceConfig)
    hard_penalties: List[HardPenaltyConfig] = Field(default_factory=list)
    rule_engine: RuleEngineConfig = Field(default_factory=RuleEngineConfig)
    ending: EndingConfig = Field(default_factory=EndingConfig)
    recommendation: RecommendationConfig = Field(default_factory=RecommendationConfig)
    flow: FlowConfig = Field(default_factory=FlowConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)


def resolve_training_runtime_config_path(config_path: str | Path | None = None) -> Path:
    """解析训练运行时配置文件路径。"""
    if config_path:
        return Path(config_path).expanduser().resolve()

    env_path = os.getenv(TRAINING_RUNTIME_CONFIG_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser().resolve()

    return DEFAULT_TRAINING_RUNTIME_CONFIG_PATH


def _apply_environment_overrides(config: TrainingRuntimeConfig) -> TrainingRuntimeConfig:
    """只允许少量部署级参数通过环境变量覆盖，业务规则仍由 JSON 管理。"""
    runtime_config = model_copy(config)

    runtime_config.switches.use_llm_eval = _as_bool(
        os.getenv("TRAINING_USE_LLM_EVAL"),
        default=runtime_config.switches.use_llm_eval,
    )
    runtime_config.switches.enforce_scenario_order = _as_bool(
        os.getenv("TRAINING_ENFORCE_SCENARIO_ORDER"),
        default=runtime_config.switches.enforce_scenario_order,
    )

    runtime_config.llm.provider = os.getenv("TRAINING_LLM_PROVIDER", runtime_config.llm.provider).strip() or runtime_config.llm.provider
    runtime_config.llm.default_eval_model = os.getenv("TRAINING_EVAL_MODEL", runtime_config.llm.default_eval_model).strip() or runtime_config.llm.default_eval_model
    runtime_config.llm.max_tokens = int(os.getenv("TRAINING_LLM_MAX_TOKENS", str(runtime_config.llm.max_tokens)))
    runtime_config.llm.temperature = float(os.getenv("TRAINING_LLM_TEMPERATURE", str(runtime_config.llm.temperature)))
    runtime_config.llm.max_retries = int(os.getenv("TRAINING_LLM_MAX_RETRIES", str(runtime_config.llm.max_retries)))
    runtime_config.llm.retry_delay = float(os.getenv("TRAINING_LLM_RETRY_DELAY", str(runtime_config.llm.retry_delay)))

    return runtime_config


def _validate_runtime_config_business_rules(config: TrainingRuntimeConfig) -> TrainingRuntimeConfig:
    """补充 Pydantic 字段校验之外的业务级配置约束。"""
    _validate_recommendation_mode_scope(config)
    _validate_phase_boost_configs(config)
    _validate_stage_window_configs(config)
    _validate_forced_round_configs(config)
    return config


def _validate_recommendation_mode_scope(config: TrainingRuntimeConfig) -> None:
    """校验推荐模式、严格模式和兜底模式之间的关系。"""
    enabled_modes = _normalize_training_modes(
        config.recommendation.enabled_modes,
        field_name="recommendation.enabled_modes",
        allow_empty=True,
        expand_all_on_empty=False,
    )
    strict_modes = _normalize_training_modes(
        config.recommendation.strict_modes,
        field_name="recommendation.strict_modes",
        allow_empty=True,
        expand_all_on_empty=False,
    )
    fallback_mode = _normalize_training_mode_name(config.recommendation.fallback_mode)
    if fallback_mode is None:
        raise ValueError(
            f"recommendation.fallback_mode contains unsupported mode: {config.recommendation.fallback_mode}"
        )

    undefined_strict_modes = [mode for mode in strict_modes if mode not in enabled_modes]
    if undefined_strict_modes:
        raise ValueError(
            f"recommendation.strict_modes must be subset of enabled_modes: {','.join(undefined_strict_modes)}"
        )


def _validate_phase_boost_configs(config: TrainingRuntimeConfig) -> None:
    """校验阶段加权配置的写法清晰且可执行。"""
    for index, boost_config in enumerate(config.recommendation.phase_boosts):
        has_distance = boost_config.distance is not None
        has_current_phase_tags = bool(boost_config.current_phase_tags)
        has_scenario_phase_tags = bool(boost_config.scenario_phase_tags)

        if has_current_phase_tags != has_scenario_phase_tags:
            raise ValueError(
                "recommendation.phase_boosts[{index}] must set current_phase_tags and scenario_phase_tags together".format(
                    index=index
                )
            )
        if not has_distance and not (has_current_phase_tags and has_scenario_phase_tags):
            raise ValueError(
                f"recommendation.phase_boosts[{index}] must define either distance or phase tag mapping"
            )
        if has_distance and (has_current_phase_tags or has_scenario_phase_tags):
            raise ValueError(
                f"recommendation.phase_boosts[{index}] should not mix distance fallback with phase tag mapping"
            )


def _validate_stage_window_configs(config: TrainingRuntimeConfig) -> None:
    """校验训练阶段窗口的轮次范围与模式声明。"""
    for index, stage_window in enumerate(config.flow.stage_windows):
        if not stage_window.phase_tags:
            raise ValueError(f"flow.stage_windows[{index}] must provide at least one phase tag")
        if stage_window.end_round is not None and int(stage_window.end_round) < int(stage_window.start_round):
            raise ValueError(f"flow.stage_windows[{index}] end_round must be greater than or equal to start_round")
        _normalize_training_modes(
            stage_window.modes,
            field_name=f"flow.stage_windows[{index}].modes",
            allow_empty=True,
            expand_all_on_empty=True,
        )


def _validate_forced_round_configs(config: TrainingRuntimeConfig) -> None:
    """校验关键轮配置，避免同一轮次同一模式出现多条冲突规则。"""
    indexed_rules: list[tuple[int, list[str]]] = []
    for index, forced_round in enumerate(config.flow.forced_rounds):
        normalized_modes = _normalize_training_modes(
            forced_round.modes,
            field_name=f"flow.forced_rounds[{index}].modes",
            allow_empty=True,
            expand_all_on_empty=True,
        )
        indexed_rules.append((index, normalized_modes))

    for left_index, left_modes in indexed_rules:
        left_rule = config.flow.forced_rounds[left_index]
        for right_index, right_modes in indexed_rules[left_index + 1 :]:
            right_rule = config.flow.forced_rounds[right_index]
            if int(left_rule.round_no) != int(right_rule.round_no):
                continue
            overlapped_modes = sorted(set(left_modes).intersection(right_modes))
            if overlapped_modes:
                raise ValueError(
                    "flow.forced_rounds[{left}] conflicts with flow.forced_rounds[{right}] on round {round_no} modes: {modes}".format(
                        left=left_index,
                        right=right_index,
                        round_no=left_rule.round_no,
                        modes=",".join(overlapped_modes),
                    )
                )


def _normalize_training_modes(
    modes: List[Any],
    *,
    field_name: str,
    allow_empty: bool,
    expand_all_on_empty: bool,
) -> List[str]:
    """把模式列表归一化成 canonical 形式，并校验是否存在未知模式。"""
    normalized_modes: List[str] = []
    for raw_mode in modes or []:
        normalized_mode = _normalize_training_mode_name(raw_mode)
        if normalized_mode is None:
            raise ValueError(f"{field_name} contains unsupported mode: {raw_mode}")
        if normalized_mode not in normalized_modes:
            normalized_modes.append(normalized_mode)

    if normalized_modes:
        return normalized_modes
    if allow_empty:
        if expand_all_on_empty:
            # 空数组在流程配置里表示“适用于所有模式”。
            return list(SUPPORTED_TRAINING_MODES)
        return []
    raise ValueError(f"{field_name} must not be empty")


def load_training_runtime_config(config_path: str | Path | None = None) -> TrainingRuntimeConfig:
    """加载并校验训练运行时配置。"""
    resolved_path = resolve_training_runtime_config_path(config_path)
    with resolved_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    config = _model_validate(TrainingRuntimeConfig, payload)
    runtime_config = _apply_environment_overrides(config)
    return _validate_runtime_config_business_rules(runtime_config)


@lru_cache(maxsize=1)
def get_training_runtime_config() -> TrainingRuntimeConfig:
    """获取缓存后的训练运行时配置。"""
    return load_training_runtime_config()


def reset_training_runtime_config_cache() -> None:
    """为测试场景提供缓存清理入口。"""
    get_training_runtime_config.cache_clear()
