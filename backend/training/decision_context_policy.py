"""训练回合决策上下文策略。"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from training.constants import TRAINING_RUNTIME_CONFIG
from training.recommendation_policy import RecommendationPolicy
from training.training_mode import TrainingModeCatalog
from training.training_outputs import TrainingDecisionCandidateOutput, TrainingRoundDecisionContextOutput

SELECTION_SOURCE_ORDERED_SEQUENCE = "ordered_sequence"
SELECTION_SOURCE_TOP_RECOMMENDATION = "top_recommendation"
SELECTION_SOURCE_CANDIDATE_POOL = "candidate_pool"
SELECTION_SOURCE_FALLBACK_SEQUENCE = "fallback_sequence"
SELECTION_SOURCE_BRANCH_TRANSITION = "branch_transition"


class TrainingDecisionContextPolicy:
    """负责生成回合决策上下文，降低服务层对推荐与分支细节的耦合。"""

    def __init__(
        self,
        recommendation_policy: RecommendationPolicy | None = None,
        mode_catalog: TrainingModeCatalog | None = None,
        runtime_config: Any = None,
    ):
        self.runtime_config = runtime_config or TRAINING_RUNTIME_CONFIG
        self.recommendation_policy = recommendation_policy or RecommendationPolicy(runtime_config=self.runtime_config)
        self.mode_catalog = mode_catalog or TrainingModeCatalog(runtime_config=self.runtime_config)

    def build_round_decision_context(
        self,
        *,
        training_mode: str,
        submitted_scenario_id: str,
        next_scenario_bundle: Any,
    ) -> TrainingRoundDecisionContextOutput | None:
        """把本回合推荐结果转换成稳定的决策上下文 DTO。"""
        scenario_payloads = self._collect_decision_scenario_payloads(next_scenario_bundle)
        if not scenario_payloads:
            return None

        recommended_payload = self._extract_recommended_scenario_payload(next_scenario_bundle)
        recommended_scenario_id = (
            str(recommended_payload.get("id") or "").strip()
            if isinstance(recommended_payload, dict)
            else None
        ) or None
        selected_payload = self._find_scenario_payload_by_id(scenario_payloads, submitted_scenario_id)
        selection_source = self._resolve_selection_source(
            training_mode=training_mode,
            submitted_scenario_id=submitted_scenario_id,
            recommended_scenario_id=recommended_scenario_id,
            scenario_payloads=scenario_payloads,
            selected_scenario_payload=selected_payload,
        )

        return TrainingRoundDecisionContextOutput.from_payload(
            {
                "mode": training_mode,
                "selection_source": selection_source,
                "selected_scenario_id": submitted_scenario_id,
                "recommended_scenario_id": recommended_scenario_id,
                "candidate_pool": self._build_decision_candidate_payloads(
                    scenario_payloads=scenario_payloads,
                    selected_scenario_id=submitted_scenario_id,
                    recommended_scenario_id=recommended_scenario_id,
                ),
                "selected_recommendation": self._extract_recommendation_payload(selected_payload),
                "recommended_recommendation": self._extract_recommendation_payload(recommended_payload),
                "selected_branch_transition": self._extract_branch_transition_payload(selected_payload),
                "recommended_branch_transition": self._extract_branch_transition_payload(recommended_payload),
            }
        )

    def _collect_decision_scenario_payloads(self, next_scenario_bundle: Any) -> List[Dict[str, Any]]:
        """提取当前回合可见的场景候选集。"""
        candidate_source = getattr(next_scenario_bundle, "scenario_candidates", None)
        if candidate_source is None:
            candidate_source = [getattr(next_scenario_bundle, "scenario", None)]

        scenario_payloads: List[Dict[str, Any]] = []
        for item in candidate_source or []:
            if isinstance(item, dict) and str(item.get("id") or "").strip():
                scenario_payloads.append(dict(item))
        return scenario_payloads

    def _extract_recommended_scenario_payload(self, next_scenario_bundle: Any) -> Dict[str, Any] | None:
        """只有携带 recommendation 元信息的场景，才视为真正推荐结果。"""
        scenario_payload = getattr(next_scenario_bundle, "scenario", None)
        if not isinstance(scenario_payload, dict):
            return None
        if not isinstance(scenario_payload.get("recommendation"), dict):
            return None
        return dict(scenario_payload)

    def _find_scenario_payload_by_id(
        self,
        scenario_payloads: Sequence[Dict[str, Any]],
        scenario_id: str,
    ) -> Dict[str, Any] | None:
        """按场景 ID 在候选集中定位原始场景载荷。"""
        normalized_scenario_id = str(scenario_id or "").strip()
        if not normalized_scenario_id:
            return None

        for payload in scenario_payloads or []:
            if str(payload.get("id") or "").strip() == normalized_scenario_id:
                return dict(payload)
        return None

    def _extract_recommendation_payload(
        self,
        scenario_payload: Dict[str, Any] | None,
    ) -> Dict[str, Any] | None:
        """从场景载荷中抽取推荐元信息。"""
        if not isinstance(scenario_payload, dict):
            return None
        recommendation = scenario_payload.get("recommendation")
        if not isinstance(recommendation, dict):
            return None
        return dict(recommendation)

    def _extract_branch_transition_payload(
        self,
        scenario_payload: Dict[str, Any] | None,
    ) -> Dict[str, Any] | None:
        """提取场景附带的分支跳转上下文。"""
        if not isinstance(scenario_payload, dict):
            return None
        branch_transition = scenario_payload.get("branch_transition")
        if not isinstance(branch_transition, dict):
            return None
        return dict(branch_transition)

    def _build_decision_candidate_payloads(
        self,
        *,
        scenario_payloads: Sequence[Dict[str, Any]],
        selected_scenario_id: str,
        recommended_scenario_id: str | None,
    ) -> List[Dict[str, Any]]:
        """把完整场景载荷收敛成适合回放展示的候选题摘要。"""
        candidate_outputs: List[Dict[str, Any]] = []
        normalized_selected_scenario_id = str(selected_scenario_id or "").strip()
        normalized_recommended_scenario_id = str(recommended_scenario_id or "").strip()

        for scenario_payload in scenario_payloads:
            scenario_id = str(scenario_payload.get("id") or "").strip()
            if not scenario_id:
                continue

            recommendation = self._extract_recommendation_payload(scenario_payload) or {}
            candidate_output = TrainingDecisionCandidateOutput.from_payload(
                {
                    "scenario_id": scenario_id,
                    "title": str(scenario_payload.get("title") or scenario_id),
                    "rank": recommendation.get("rank"),
                    "rank_score": recommendation.get("rank_score", 0.0),
                    "is_selected": scenario_id == normalized_selected_scenario_id,
                    "is_recommended": scenario_id == normalized_recommended_scenario_id,
                }
            )
            if candidate_output is not None:
                candidate_outputs.append(candidate_output.to_dict())
        return candidate_outputs

    def _resolve_selection_source(
        self,
        *,
        training_mode: str,
        submitted_scenario_id: str,
        recommended_scenario_id: str | None,
        scenario_payloads: Sequence[Dict[str, Any]],
        selected_scenario_payload: Dict[str, Any] | None = None,
    ) -> str:
        """标记本回合场景来自固定顺序、推荐首选、候选池还是分支跳转。"""
        normalized_mode = self.mode_catalog.normalize(
            training_mode,
            default="guided",
            raise_on_unknown=False,
        ) or "guided"
        normalized_submitted_scenario_id = str(submitted_scenario_id or "").strip()

        # 分支跳转是独立来源，不能继续被记成普通主线顺序提交。
        if isinstance(selected_scenario_payload, dict) and isinstance(selected_scenario_payload.get("branch_transition"), dict):
            return SELECTION_SOURCE_BRANCH_TRANSITION

        if recommended_scenario_id:
            normalized_recommended_scenario_id = str(recommended_scenario_id or "").strip()
            if normalized_submitted_scenario_id == normalized_recommended_scenario_id:
                return SELECTION_SOURCE_TOP_RECOMMENDATION

            candidate_ids = {
                str(payload.get("id") or "").strip()
                for payload in scenario_payloads
                if isinstance(payload, dict)
            }
            if normalized_submitted_scenario_id in candidate_ids:
                return SELECTION_SOURCE_CANDIDATE_POOL
            return SELECTION_SOURCE_FALLBACK_SEQUENCE

        if self.recommendation_policy.supports_mode(normalized_mode):
            return SELECTION_SOURCE_FALLBACK_SEQUENCE
        return SELECTION_SOURCE_ORDERED_SEQUENCE
