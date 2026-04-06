"""推荐 Agent：在规则排序基础上，用 LLM 做语义层决策覆盖。

设计原则：
- 规则排序始终先跑（保证兜底，eval_mode 可审计）
- LLM 只在明确触发条件下介入，做"是否覆盖 top-1"的二元决策
- LLM 失败时静默降级到规则结果，不影响主流程
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence

from training.recommendation_policy import RecommendationPolicy
from utils.logger import get_logger

logger = get_logger(__name__)


class RecommendationAgent:
    """在规则推荐结果之上，用 LLM 做一次语义覆盖决策。"""

    def __init__(
        self,
        *,
        recommendation_policy: RecommendationPolicy | None = None,
        llm_service: Any = None,
        use_llm: bool = True,
        runtime_config: Any = None,
    ):
        self.recommendation_policy = recommendation_policy or RecommendationPolicy(
            runtime_config=runtime_config
        )
        self.use_llm = use_llm
        self._llm_service = llm_service

        if use_llm and llm_service is None:
            try:
                from llm import LLMService
                self._llm_service = LLMService(provider="auto")
                logger.info(
                    "RecommendationAgent LLM enabled: provider=%s model=%s",
                    self._llm_service.get_provider(),
                    self._llm_service.get_model(),
                )
            except Exception as exc:
                logger.warning(
                    "RecommendationAgent LLM init failed, fallback to rules only: %s", exc
                )
                self._llm_service = None

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def rank_candidates(
        self,
        training_mode: str,
        scenario_payload_sequence: Sequence[Dict[str, Any]],
        completed_scenario_ids: Sequence[str],
        k_state: Dict[str, float] | None = None,
        s_state: Dict[str, float] | None = None,
        recent_risk_rounds: Sequence[Sequence[str]] | None = None,
        current_round_no: int = 0,
        total_rounds: int | None = None,
    ) -> List[Dict[str, Any]]:
        """透传规则排序，保持与 RecommendationPolicy 接口兼容。"""
        return self.recommendation_policy.rank_candidates(
            training_mode=training_mode,
            scenario_payload_sequence=scenario_payload_sequence,
            completed_scenario_ids=completed_scenario_ids,
            k_state=k_state,
            s_state=s_state,
            recent_risk_rounds=recent_risk_rounds,
            current_round_no=current_round_no,
            total_rounds=total_rounds,
        )

    def supports_mode(self, training_mode: str) -> bool:
        return self.recommendation_policy.supports_mode(training_mode)

    def is_strict_mode(self, training_mode: str) -> bool:
        return self.recommendation_policy.is_strict_mode(training_mode)

    def recommend_with_override(
        self,
        *,
        training_mode: str,
        ranked_candidates: List[Dict[str, Any]],
        k_state: Dict[str, float],
        s_state: Dict[str, float],
        recent_risk_rounds: Sequence[Sequence[str]] | None = None,
        current_round_no: int = 0,
        player_profile: Dict[str, Any] | None = None,
    ) -> Dict[str, Any] | None:
        """在已排序候选列表上，按需用 LLM 做语义覆盖。

        Args:
            ranked_candidates: 规则排序后的候选列表（已含 recommendation 元信息）
            其余参数: 当前会话状态，用于触发条件判断和 LLM prompt 构建

        Returns:
            最终推荐场景（含 recommendation.override_source 标记）
        """
        if not ranked_candidates:
            return None

        if not self.use_llm or self._llm_service is None:
            return ranked_candidates[0]

        if not self._should_llm_override(
            k_state=k_state,
            s_state=s_state,
            recent_risk_rounds=list(recent_risk_rounds or []),
            current_round_no=current_round_no,
        ):
            return ranked_candidates[0]

        try:
            override = self._llm_override(
                ranked_candidates=ranked_candidates,
                k_state=k_state,
                s_state=s_state,
                recent_risk_rounds=list(recent_risk_rounds or []),
                player_profile=player_profile or {},
                current_round_no=current_round_no,
            )
            if override is not None:
                result = dict(override)
                result["recommendation"] = {
                    **(result.get("recommendation") or {}),
                    "override_source": "llm",
                }
                logger.info(
                    "RecommendationAgent LLM override applied: selected=%s round=%s",
                    result.get("id"),
                    current_round_no,
                )
                return result
        except Exception as exc:
            logger.warning(
                "RecommendationAgent LLM override failed, using rules top-1: %s", exc
            )

        return ranked_candidates[0]

    # ------------------------------------------------------------------
    # 内部逻辑
    # ------------------------------------------------------------------

    def _should_llm_override(
        self,
        k_state: Dict[str, float],
        s_state: Dict[str, float],
        recent_risk_rounds: List[Sequence[str]],
        current_round_no: int,
    ) -> bool:
        """只在以下情况触发 LLM 介入，避免每轮消耗 token。"""
        # 连续 2 轮高风险
        recent = recent_risk_rounds[-2:]
        if len(recent) >= 2 and all(r for r in recent):
            return True
        # 某项技能极低（< 0.3）
        if any(v < 0.3 for v in k_state.values()):
            return True
        # 公众恐慌过高
        if s_state.get("public_panic", 0.0) > 0.7:
            return True
        # 编辑信任极低
        if s_state.get("editor_trust", 0.0) < 0.25:
            return True
        return False

    def _llm_override(
        self,
        ranked_candidates: List[Dict[str, Any]],
        k_state: Dict[str, float],
        s_state: Dict[str, float],
        recent_risk_rounds: List[Sequence[str]],
        player_profile: Dict[str, Any],
        current_round_no: int,
    ) -> Optional[Dict[str, Any]]:
        """让 LLM 从候选列表中选出最合适的场景 ID。"""
        candidates_summary = [
            {
                "id": c.get("id"),
                "title": c.get("title", ""),
                "target_skills": c.get("target_skills", []),
                "difficulty": c.get("difficulty", "medium"),
                "rank_score": round(
                    float((c.get("recommendation") or {}).get("rank_score", 0)), 4
                ),
            }
            for c in ranked_candidates[:5]
        ]
        weak_skills = [k for k, v in k_state.items() if v < 0.4]
        recent_flags = list({f for r in recent_risk_rounds[-3:] for f in r})

        system_prompt = (
            "你是一个新闻训练系统的场景推荐决策器。"
            "根据学员当前状态，从候选场景中选出最合适的一个。"
            "只输出 JSON，不要 markdown，不要解释：{\"selected_id\": \"场景ID\", \"reason\": \"一句话理由\"}"
        )
        user_prompt = (
            f"当前轮次：{current_round_no}\n"
            f"薄弱技能（值<0.4）：{weak_skills}\n"
            f"近期风险标记：{recent_flags}\n"
            f"公众恐慌：{s_state.get('public_panic', 0):.2f}，"
            f"编辑信任：{s_state.get('editor_trust', 0):.2f}，"
            f"来源安全：{s_state.get('source_safety', 0):.2f}\n"
            f"候选场景（按规则排序）：{json.dumps(candidates_summary, ensure_ascii=False)}\n"
            "请选出最适合当前学员状态的场景ID。"
        )

        response = self._llm_service.call(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.2,
        )

        match = re.search(r"\{.*\}", response.text, re.DOTALL)
        if not match:
            return None

        data = json.loads(match.group(0))
        selected_id = str(data.get("selected_id") or "").strip()
        if not selected_id:
            return None

        for candidate in ranked_candidates:
            if str(candidate.get("id") or "") == selected_id:
                return dict(candidate)

        logger.warning(
            "RecommendationAgent LLM selected unknown id=%s, ignoring override", selected_id
        )
        return None
