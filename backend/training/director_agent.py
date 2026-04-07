"""训练回合执行计划生成器（Director Agent）。

当前版本为纯规则实现，预留 use_llm=True 接口供后续 LLM 决策接入。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionPlan:
    """单回合执行计划，由 TrainingDirectorAgent 在 submit_round 开头生成。"""

    needs_script_refresh: bool = False
    force_low_risk_scenario: bool = False
    eval_retry_budget: int = 1
    branch_hint: Optional[str] = None


class TrainingDirectorAgent:
    """训练回合执行计划生成器（当前版本：纯规则）。"""

    def __init__(self, *, use_llm: bool = False, runtime_config: Any = None):
        self.use_llm = use_llm
        self.runtime_config = runtime_config

    def plan(
        self,
        session: Any,
        round_no: int,
        k_state: Dict[str, float],
        s_state: Dict[str, float],
        recent_risk_rounds: Sequence[Sequence[str]] | None = None,
        runtime_flags: Dict[str, Any] | None = None,
        behavior_profile: Any | None = None,  # Phase 2: BehaviorProfile，当前版本忽略
    ) -> ExecutionPlan:
        """生成本轮执行计划。use_llm=False 时使用纯规则逻辑。"""
        if self.use_llm:
            # 预留接口，当前版本回退到规则
            logger.debug("TrainingDirectorAgent: use_llm=True not implemented, falling back to rules")

        return self._plan_by_rules(
            round_no=round_no,
            k_state=k_state,
            s_state=s_state,
            recent_risk_rounds=list(recent_risk_rounds or []),
            runtime_flags=runtime_flags or {},
        )

    def _plan_by_rules(
        self,
        round_no: int,
        k_state: Dict[str, float],
        s_state: Dict[str, float],
        recent_risk_rounds: List[Sequence[str]],
        runtime_flags: Dict[str, Any],
    ) -> ExecutionPlan:
        # 连续 2 轮高风险 -> 强制低风险场景
        recent = recent_risk_rounds[-2:]
        force_low_risk = len(recent) >= 2 and all(r for r in recent)

        # 某项技能极低（< 0.25）-> 建议刷新剧本
        needs_refresh = any(v < 0.25 for v in k_state.values())

        # eval_retry_budget：公众恐慌过高时增加重试预算
        eval_retry_budget = 2 if s_state.get("public_panic", 0.0) > 0.65 else 1

        return ExecutionPlan(
            needs_script_refresh=needs_refresh,
            force_low_risk_scenario=force_low_risk,
            eval_retry_budget=eval_retry_budget,
            branch_hint=None,
        )
