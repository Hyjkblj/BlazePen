"""Behavior Profile Agent — 用户行为模式抽象层。

职责：
- 从历史回合数据中抽象出用户的行为模式（pattern）、风险趋势（risk_trend）和技能趋势（skill_trend）
- 供 Director Agent、RecommendationAgent、Evaluator 消费，提升上下文感知能力

保护机制：
- data_rounds < MIN_DATA_ROUNDS 时返回 None，避免少量数据过拟合
- LLM 路径失败时静默降级到规则路径，不抛出异常

Phase 2 实现计划：
- Phase 2.1（当前）：骨架 + 规则版 pattern 分类，接口稳定
- Phase 2.2：接入 LLM，将 risk_flags 历史升级为结构化行为摘要
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# 最少需要多少轮数据才生成 profile，低于此值返回 None
MIN_DATA_ROUNDS = 4

# 行为模式枚举（规则版分类）
BEHAVIOR_PATTERN_AGGRESSIVE_PUBLISHER = "aggressive_publisher"   # 倾向快速发布，忽视核验
BEHAVIOR_PATTERN_OVER_CAUTIOUS = "over_cautious"                 # 过度谨慎，频繁延迟发布
BEHAVIOR_PATTERN_SOURCE_RISK = "source_risk"                     # 反复触发来源暴露风险
BEHAVIOR_PATTERN_PANIC_AMPLIFIER = "panic_amplifier"             # 反复触发公众恐慌
BEHAVIOR_PATTERN_BALANCED = "balanced"                           # 均衡，无明显偏向

# 趋势枚举
TREND_INCREASING = "increasing"
TREND_DECREASING = "decreasing"
TREND_STABLE = "stable"


@dataclass(frozen=True)
class BehaviorProfile:
    """用户行为模式快照，由 BehaviorProfileAgent 生成。

    所有字段均为只读，供下游 Agent 消费。
    """

    behavior_pattern: str
    """主行为模式，取值见 BEHAVIOR_PATTERN_* 常量。"""

    risk_trend: str
    """风险趋势：increasing / decreasing / stable。"""

    skill_trend: Dict[str, str]
    """各技能趋势，key 为技能代码（K1-K8），value 为 increasing/decreasing/stable。"""

    confidence: float
    """置信度 0.0-1.0，data_rounds 越多越高。"""

    data_rounds: int
    """生成本 profile 使用的回合数。"""

    dominant_risk_flags: List[str] = field(default_factory=list)
    """出现频率最高的风险标记（最多 3 个）。"""

    summary: str = ""
    """一句话摘要，供 LLM prompt 注入使用。"""


class BehaviorProfileAgent:
    """用户行为模式抽象 Agent。

    当前版本（Phase 2.1）：纯规则实现，接口稳定。
    Phase 2.2 可通过 use_llm=True 开启 LLM 增强路径。
    """

    def __init__(
        self,
        *,
        use_llm: bool = False,
        llm_service: Any = None,
        runtime_config: Any = None,
    ):
        self.use_llm = use_llm
        self._llm_service = llm_service
        self.runtime_config = runtime_config

    def build_profile(
        self,
        *,
        session_id: str,
        round_history: List[Dict[str, Any]],
    ) -> Optional[BehaviorProfile]:
        """从历史回合数据构建行为 profile。

        Args:
            session_id: 会话 ID，仅用于日志。
            round_history: 历史回合摘要列表，每条包含：
                - round_no: int
                - scenario_id: str
                - risk_flags: List[str]
                - skill_delta: Dict[str, float]  （可选）
                - k_state_after: Dict[str, float]  （可选）

        Returns:
            BehaviorProfile 或 None（数据不足时）。
        """
        if not round_history or len(round_history) < MIN_DATA_ROUNDS:
            logger.debug(
                "BehaviorProfileAgent: insufficient data rounds=%d session_id=%s",
                len(round_history) if round_history else 0,
                session_id,
            )
            return None

        try:
            return self._build_by_rules(round_history=round_history)
        except Exception as exc:
            logger.warning(
                "BehaviorProfileAgent: rule-based profile failed, returning None: session_id=%s error=%s",
                session_id,
                str(exc),
            )
            return None

    # ------------------------------------------------------------------
    # 规则版实现（Phase 2.1）
    # ------------------------------------------------------------------

    def _build_by_rules(self, round_history: List[Dict[str, Any]]) -> BehaviorProfile:
        """纯规则版行为模式分类。"""
        data_rounds = len(round_history)

        # 1. 收集所有 risk_flags
        all_flags: List[str] = []
        for entry in round_history:
            flags = entry.get("risk_flags") or []
            if isinstance(flags, list):
                all_flags.extend(str(f) for f in flags if f)

        # 2. 统计 flag 频率
        flag_counts: Dict[str, int] = {}
        for flag in all_flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

        dominant_flags = sorted(flag_counts, key=lambda k: flag_counts[k], reverse=True)[:3]

        # 3. 判断主行为模式（规则优先级：source_risk > panic > aggressive > cautious > balanced）
        high_risk_rounds = sum(1 for e in round_history if e.get("risk_flags"))
        risk_ratio = high_risk_rounds / data_rounds

        source_flags = {"source_exposure", "source_safety", "source_exposed", "privacy_leak_risk"}
        panic_flags = {"public_panic", "panic_triggered", "rumor_spread_risk", "emotional_language_risk"}
        publish_flags = {"unverified_publish", "verification_chain"}

        source_count = sum(flag_counts.get(f, 0) for f in source_flags)
        panic_count = sum(flag_counts.get(f, 0) for f in panic_flags)
        publish_count = sum(flag_counts.get(f, 0) for f in publish_flags)

        if source_count >= 2:
            pattern = BEHAVIOR_PATTERN_SOURCE_RISK
        elif panic_count >= 2:
            pattern = BEHAVIOR_PATTERN_PANIC_AMPLIFIER
        elif publish_count >= 2:
            pattern = BEHAVIOR_PATTERN_AGGRESSIVE_PUBLISHER
        elif risk_ratio < 0.2:
            pattern = BEHAVIOR_PATTERN_OVER_CAUTIOUS
        else:
            pattern = BEHAVIOR_PATTERN_BALANCED

        # 4. 风险趋势：比较前半段和后半段的高风险轮次比例
        risk_trend = self._compute_risk_trend(round_history)

        # 5. 技能趋势：比较前后 k_state 变化
        skill_trend = self._compute_skill_trend(round_history)

        # 6. 置信度：随数据量线性增长，上限 0.9
        confidence = min(0.9, 0.4 + (data_rounds - MIN_DATA_ROUNDS) * 0.05)

        # 7. 摘要（供 LLM prompt 注入）
        summary = _build_profile_summary(
            pattern=pattern,
            risk_trend=risk_trend,
            skill_trend=skill_trend,
            dominant_flags=dominant_flags,
            data_rounds=data_rounds,
        )

        return BehaviorProfile(
            behavior_pattern=pattern,
            risk_trend=risk_trend,
            skill_trend=skill_trend,
            confidence=round(confidence, 2),
            data_rounds=data_rounds,
            dominant_risk_flags=dominant_flags,
            summary=summary,
        )

    def _compute_risk_trend(self, round_history: List[Dict[str, Any]]) -> str:
        """比较前半段和后半段的高风险轮次比例，判断趋势。"""
        mid = len(round_history) // 2
        if mid == 0:
            return TREND_STABLE

        first_half = round_history[:mid]
        second_half = round_history[mid:]

        first_risk = sum(1 for e in first_half if e.get("risk_flags")) / len(first_half)
        second_risk = sum(1 for e in second_half if e.get("risk_flags")) / len(second_half)

        diff = second_risk - first_risk
        if diff > 0.2:
            return TREND_INCREASING
        if diff < -0.2:
            return TREND_DECREASING
        return TREND_STABLE

    def _compute_skill_trend(self, round_history: List[Dict[str, Any]]) -> Dict[str, str]:
        """通过 k_state_after 的首尾对比判断各技能趋势。"""
        from training.constants import SKILL_CODES

        # 找第一条和最后一条有 k_state_after 的记录
        first_k: Dict[str, float] = {}
        last_k: Dict[str, float] = {}

        for entry in round_history:
            k = entry.get("k_state_after")
            if isinstance(k, dict) and k:
                if not first_k:
                    first_k = dict(k)
                last_k = dict(k)

        if not first_k or not last_k or first_k is last_k:
            return {code: TREND_STABLE for code in SKILL_CODES}

        trend: Dict[str, str] = {}
        for code in SKILL_CODES:
            before = float(first_k.get(code, 0.0))
            after = float(last_k.get(code, 0.0))
            diff = after - before
            if diff > 0.05:
                trend[code] = TREND_INCREASING
            elif diff < -0.05:
                trend[code] = TREND_DECREASING
            else:
                trend[code] = TREND_STABLE

        return trend


# ------------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------------

def _build_profile_summary(
    *,
    pattern: str,
    risk_trend: str,
    skill_trend: Dict[str, str],
    dominant_flags: List[str],
    data_rounds: int,
) -> str:
    """生成一句话摘要，供 LLM prompt 注入。"""
    pattern_labels = {
        BEHAVIOR_PATTERN_AGGRESSIVE_PUBLISHER: "倾向快速发布、忽视核验",
        BEHAVIOR_PATTERN_OVER_CAUTIOUS: "过度谨慎、频繁延迟",
        BEHAVIOR_PATTERN_SOURCE_RISK: "反复触发来源暴露风险",
        BEHAVIOR_PATTERN_PANIC_AMPLIFIER: "反复引发公众恐慌",
        BEHAVIOR_PATTERN_BALANCED: "行为均衡",
    }
    trend_labels = {
        TREND_INCREASING: "上升",
        TREND_DECREASING: "下降",
        TREND_STABLE: "稳定",
    }

    declining_skills = [k for k, v in skill_trend.items() if v == TREND_DECREASING]
    pattern_label = pattern_labels.get(pattern, pattern)
    risk_label = trend_labels.get(risk_trend, risk_trend)

    parts = [f"行为模式：{pattern_label}，风险趋势：{risk_label}"]
    if dominant_flags:
        parts.append(f"主要风险标记：{'/'.join(dominant_flags[:2])}")
    if declining_skills:
        parts.append(f"下滑技能：{'/'.join(declining_skills[:3])}")
    parts.append(f"（基于{data_rounds}轮数据）")

    return "，".join(parts)


def build_round_history_from_store_records(
    round_records: List[Any],
    evaluation_records: List[Any],
) -> List[Dict[str, Any]]:
    """从 store 返回的 record 对象构建 round_history 列表。

    这是 BehaviorProfileAgent.build_profile 的数据准备辅助函数，
    供 TrainingService 或 Director Agent 调用。
    """
    eval_map: Dict[str, Any] = {}
    for ev in evaluation_records or []:
        rid = getattr(ev, "round_id", None)
        if rid:
            eval_map[rid] = ev

    history: List[Dict[str, Any]] = []
    for rr in round_records or []:
        round_id = getattr(rr, "round_id", None)
        ev = eval_map.get(round_id) if round_id else None

        eval_payload = {}
        if ev is not None:
            eval_payload = getattr(ev, "evaluation_payload", None) or getattr(ev, "raw_payload", None) or {}

        history.append({
            "round_no": getattr(rr, "round_no", None),
            "scenario_id": getattr(rr, "scenario_id", None),
            "risk_flags": eval_payload.get("risk_flags", []) if isinstance(eval_payload, dict) else [],
            "skill_delta": eval_payload.get("skill_delta", {}) if isinstance(eval_payload, dict) else {},
            "k_state_after": getattr(rr, "kt_after", None) or {},
        })

    return history
