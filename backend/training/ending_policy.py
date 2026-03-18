"""训练结局判定策略。"""

from __future__ import annotations

from typing import Any, Dict, Iterable

from training.constants import DEFAULT_K_STATE, SKILL_CODES, SKILL_WEIGHTS, TRAINING_RUNTIME_CONFIG


class EndingPolicy:
    """根据最终 K/S 状态和风险历史生成结局。"""

    def __init__(
        self,
        runtime_config: Any = None,
        skill_weights: Dict[str, float] | None = None,
        default_k_state: Dict[str, float] | None = None,
    ):
        self.runtime_config = runtime_config or TRAINING_RUNTIME_CONFIG
        self.skill_weights = dict(skill_weights or SKILL_WEIGHTS)
        self.default_k_state = dict(default_k_state or DEFAULT_K_STATE)
        self.ending_config = self.runtime_config.ending

    def resolve(self, k_state: Dict[str, float], s_state: Dict[str, float], evaluation_rows: Iterable[Any]) -> Dict[str, Any]:
        """根据状态与历史风险标记生成结局结果。"""
        score = self._weighted_k_score(k_state)
        severe_flag = self._has_severe_flag(evaluation_rows)
        thresholds = self.ending_config.thresholds
        types = self.ending_config.types

        # 先判断硬风险，再判断成长型结局，避免高风险被高分覆盖。
        if severe_flag or s_state["source_safety"] < thresholds.fail_source_safety or s_state["public_panic"] > thresholds.fail_public_panic:
            ending_type = types.costly
        elif (
            score >= thresholds.excellent_score
            and s_state["accuracy"] >= thresholds.excellent_accuracy
            and s_state["source_safety"] >= thresholds.excellent_source_safety
        ):
            ending_type = types.excellent
        elif score >= thresholds.recovery_score and (score - self._weighted_k_score(self.default_k_state)) >= thresholds.recovery_improvement:
            ending_type = types.recovery
        elif score >= thresholds.steady_score:
            ending_type = types.steady
        else:
            ending_type = types.fail

        return {
            "type": ending_type,
            "score": round(score, 4),
            "explanation": f"综合能力评分 {round(score, 4)}，结合风险与剧情状态判定为：{ending_type}",
            "k_state": k_state,
            "s_state": s_state,
        }

    def _weighted_k_score(self, k_state: Dict[str, float]) -> float:
        """按权重计算综合 K 分数。"""
        return sum(self.skill_weights.get(code, 0.0) * float(k_state.get(code, 0.0)) for code in SKILL_CODES)

    def _has_severe_flag(self, evaluation_rows: Iterable[Any]) -> bool:
        """检查历史评估中是否出现严重风险标记。"""
        severe_flags = set(self.ending_config.severe_flags)
        for row in evaluation_rows:
            flags = getattr(row, "risk_flags", None) or []
            if any(flag in severe_flags for flag in flags):
                return True
        return False
