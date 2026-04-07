"""推荐 Agent：继承 RecommendationPolicy，在规则排序基础上可选接入 LLM 覆盖 top-1。

设计原则：
- 继承而非组合：可直接替换所有 recommendation_policy 注入点，TrainingRoundFlowPolicy 零改动
- rank_candidates 重写：规则排序先跑，满足触发条件时 LLM 覆盖 top-1
- LLM 失败时静默降级，返回规则 top-1，不抛出异常
- 触发条件从 runtime_config.recommendation.llm_override 读取，不硬编码
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from training.phase_policy import TrainingPhasePolicy
from training.recommendation_policy import RecommendationPolicy
from utils.logger import get_logger

logger = get_logger(__name__)


class RecommendationAgent(RecommendationPolicy):
    """在规则推荐结果之上，可选接入 LLM 做语义覆盖决策。"""

    def __init__(
        self,
        *,
        llm_service: Any = None,
        use_llm: bool = True,
        runtime_config: Any = None,
        phase_policy: TrainingPhasePolicy | None = None,
    ):
        super().__init__(runtime_config=runtime_config, phase_policy=phase_policy)
        self.use_llm = use_llm
        self._llm_service = llm_service

        if use_llm and llm_service is None:
            self._try_init_llm()

    def _try_init_llm(self) -> None:
        """懒加载 LLM，失败时静默设置 _llm_service = None。"""
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
    # 核心重写：rank_candidates
    # ------------------------------------------------------------------

    def rank_candidates(
        self,
        training_mode: str,
        scenario_payload_sequence: Sequence[Dict[str, Any]],
        completed_scenario_ids: Iterable[str],
        k_state: Dict[str, float] | None = None,
        s_state: Dict[str, float] | None = None,
        recent_risk_rounds: Sequence[Sequence[str]] | None = None,
        current_round_no: int = 0,
        total_rounds: int | None = None,
    ) -> List[Dict[str, Any]]:
        """规则排序先跑，满足触发条件时 LLM 覆盖 top-1。"""
        # 1. 规则排序始终先跑，保证兜底
        ranked = super().rank_candidates(
            training_mode=training_mode,
            scenario_payload_sequence=scenario_payload_sequence,
            completed_scenario_ids=completed_scenario_ids,
            k_state=k_state,
            s_state=s_state,
            recent_risk_rounds=recent_risk_rounds,
            current_round_no=current_round_no,
            total_rounds=total_rounds,
        )
        if not ranked:
            return ranked

        # 2. 为所有候选标记 override_source=rules（默认）
        for item in ranked:
            rec = item.setdefault("recommendation", {})
            rec["override_source"] = "rules"

        # 3. 判断是否触发 LLM 覆盖
        if not self.use_llm or self._llm_service is None:
            return ranked

        if not self._should_llm_override(
            k_state=k_state or {},
            s_state=s_state or {},
            recent_risk_rounds=list(recent_risk_rounds or []),
        ):
            return ranked

        # 4. LLM 覆盖 top-1，失败时静默降级
        try:
            override = self._llm_select_top1(
                ranked=ranked,
                k_state=k_state or {},
                s_state=s_state or {},
                recent_risk_rounds=list(recent_risk_rounds or []),
                current_round_no=current_round_no,
            )
            if override is not None:
                override["recommendation"]["override_source"] = "llm"
                # 仅替换 top-1，其余顺序不变
                rest = [c for c in ranked if c.get("id") != override.get("id")]
                logger.info(
                    "RecommendationAgent LLM override applied: selected=%s round=%s",
                    override.get("id"),
                    current_round_no,
                )
                return [override] + rest
        except Exception as exc:
            logger.warning(
                "RecommendationAgent LLM override failed, using rules top-1: %s", exc
            )

        return ranked

    # ------------------------------------------------------------------
    # 触发条件判断
    # ------------------------------------------------------------------

    def _should_llm_override(
        self,
        k_state: Dict[str, float],
        s_state: Dict[str, float],
        recent_risk_rounds: List[Sequence[str]],
    ) -> bool:
        """从 runtime_config.recommendation.llm_override 读取触发条件。"""
        cfg = getattr(self.recommendation_config, "llm_override", None)
        if cfg is None:
            return False
        if not getattr(cfg, "enabled", False):
            return False

        # 连续高风险轮次
        min_rounds = int(getattr(cfg, "min_consecutive_risk_rounds", 2))
        window = recent_risk_rounds[-min_rounds:]
        if len(window) >= min_rounds and all(r for r in window):
            return True

        # 某项技能极低
        threshold = float(getattr(cfg, "min_weak_skill_threshold", 0.3))
        if any(v < threshold for v in k_state.values()):
            return True

        # 公众恐慌过高
        max_panic = float(getattr(cfg, "max_public_panic", 0.7))
        if s_state.get("public_panic", 0.0) > max_panic:
            return True

        # 编辑信任极低
        min_trust = float(getattr(cfg, "min_editor_trust", 0.25))
        if s_state.get("editor_trust", 0.0) < min_trust:
            return True

        return False

    # ------------------------------------------------------------------
    # LLM 覆盖逻辑
    # ------------------------------------------------------------------

    def _llm_select_top1(
        self,
        ranked: List[Dict[str, Any]],
        k_state: Dict[str, float],
        s_state: Dict[str, float],
        recent_risk_rounds: List[Sequence[str]],
        current_round_no: int,
    ) -> Optional[Dict[str, Any]]:
        """让 LLM 从候选列表中选出最合适的场景 ID，仅覆盖 top-1。"""
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
            for c in ranked[:5]
        ]
        weak_skills = [k for k, v in k_state.items() if v < 0.4]
        recent_flags = list({f for r in recent_risk_rounds[-3:] for f in r})

        system_prompt = (
            "你是一个新闻训练系统的场景推荐决策器。"
            "根据学员当前状态，从候选场景中选出最合适的一个。"
            "只输出 JSON，不要 markdown，不要解释："
            '{"selected_id": "场景ID", "reason": "一句话理由"}'
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

        for candidate in ranked:
            if str(candidate.get("id") or "") == selected_id:
                return dict(candidate)

        logger.warning(
            "RecommendationAgent LLM selected unknown id=%s, ignoring override", selected_id
        )
        return None
