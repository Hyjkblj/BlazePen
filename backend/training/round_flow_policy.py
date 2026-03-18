"""训练回合流转策略。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from training.constants import TRAINING_RUNTIME_CONFIG
from training.recommendation_policy import RecommendationPolicy
from training.scenario_policy import ScenarioPolicy
from training.training_mode import TrainingModeCatalog


def _copy_payload(payload: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """对原始场景字典做浅拷贝，避免策略层输出被上游意外修改。"""
    if not isinstance(payload, dict):
        return None
    return dict(payload)


@dataclass(slots=True)
class TrainingScenarioFlowBundle:
    """下一题解析结果。"""

    scenario: Optional[Dict[str, Any]]
    scenario_candidates: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定字典结构，供服务层直接拼接输出 DTO。"""
        payload = {
            "scenario": _copy_payload(self.scenario),
        }
        if self.scenario_candidates is not None:
            payload["scenario_candidates"] = [dict(item) for item in self.scenario_candidates]
        return payload


class TrainingRoundFlowPolicy:
    """负责“下一题选择、允许提交、完成判定”的统一流转策略。"""

    def __init__(
        self,
        scenario_policy: ScenarioPolicy | None = None,
        recommendation_policy: RecommendationPolicy | None = None,
        runtime_config: Any = None,
    ):
        self.runtime_config = runtime_config or TRAINING_RUNTIME_CONFIG
        self.scenario_policy = scenario_policy or ScenarioPolicy(runtime_config=self.runtime_config)
        self.recommendation_policy = recommendation_policy or RecommendationPolicy(runtime_config=self.runtime_config)
        self.mode_catalog = TrainingModeCatalog(runtime_config=self.runtime_config)

    def build_next_scenario_bundle(
        self,
        training_mode: str | None,
        current_round_no: int,
        session_sequence: Sequence[Dict[str, Any]] | None,
        scenario_payload_sequence: Sequence[Dict[str, Any]] | None,
        completed_scenario_ids: Iterable[str],
        k_state: Dict[str, float] | None = None,
        s_state: Dict[str, float] | None = None,
        recent_risk_rounds: Sequence[Sequence[str]] | None = None,
    ) -> TrainingScenarioFlowBundle:
        """统一解析当前会话下一题及候选列表。"""
        effective_payload_sequence = self._build_effective_payload_sequence(
            session_sequence=session_sequence,
            scenario_payload_sequence=scenario_payload_sequence,
        )
        if not effective_payload_sequence:
            return TrainingScenarioFlowBundle(scenario=None)

        next_round_no = int(current_round_no) + 1
        forced_round_payload = self._resolve_forced_round_payload(
            training_mode=training_mode,
            next_round_no=next_round_no,
            effective_payload_sequence=effective_payload_sequence,
        )
        if forced_round_payload is not None:
            return TrainingScenarioFlowBundle(
                scenario=forced_round_payload,
            )

        if self.recommendation_policy.supports_mode(training_mode or ""):
            recommendation_payload_sequence = self._filter_reserved_future_forced_payloads(
                training_mode=training_mode,
                current_round_no=current_round_no,
                effective_payload_sequence=effective_payload_sequence,
            )
            ranked_candidates = self._rank_recommendation_candidates(
                training_mode=training_mode,
                effective_payload_sequence=recommendation_payload_sequence,
                completed_scenario_ids=completed_scenario_ids,
                k_state=k_state,
                s_state=s_state,
                recent_risk_rounds=recent_risk_rounds,
                current_round_no=current_round_no,
                total_rounds=len(list(session_sequence or effective_payload_sequence)),
            )
            if ranked_candidates:
                scenario_candidates = self._build_scenario_candidates(training_mode, ranked_candidates)
                return TrainingScenarioFlowBundle(
                    scenario=dict(ranked_candidates[0]),
                    scenario_candidates=scenario_candidates if scenario_candidates else None,
                )

            fallback_payload = self._resolve_ordered_fallback_payload(
                training_mode=training_mode,
                current_round_no=current_round_no,
                effective_payload_sequence=effective_payload_sequence,
                completed_scenario_ids=completed_scenario_ids,
            )
            return TrainingScenarioFlowBundle(
                scenario=dict(fallback_payload) if fallback_payload is not None else None,
            )

        index = min(current_round_no, len(effective_payload_sequence) - 1)
        return TrainingScenarioFlowBundle(
            scenario=dict(effective_payload_sequence[index]),
        )

    def validate_submission(
        self,
        training_mode: str | None,
        current_round_no: int,
        submitted_scenario_id: str,
        session_sequence: Sequence[Dict[str, Any]] | None,
        scenario_payload_sequence: Sequence[Dict[str, Any]] | None,
        completed_scenario_ids: Iterable[str],
        k_state: Dict[str, float] | None = None,
        s_state: Dict[str, float] | None = None,
        recent_risk_rounds: Sequence[Sequence[str]] | None = None,
    ) -> None:
        """统一校验本回合允许提交的场景范围。"""
        effective_payload_sequence = self._build_effective_payload_sequence(
            session_sequence=session_sequence,
            scenario_payload_sequence=scenario_payload_sequence,
        )
        next_round_no = int(current_round_no) + 1

        forced_round_payload = self._resolve_forced_round_payload(
            training_mode=training_mode,
            next_round_no=next_round_no,
            effective_payload_sequence=effective_payload_sequence,
        )
        if forced_round_payload is not None:
            expected_id = str(forced_round_payload["id"])
            if str(submitted_scenario_id) != expected_id:
                raise ValueError(
                    f"scenario mismatch: expected={expected_id}, submitted={submitted_scenario_id}, round={next_round_no}"
                )
            return

        if self.recommendation_policy.supports_mode(training_mode or ""):
            recommendation_payload_sequence = self._filter_reserved_future_forced_payloads(
                training_mode=training_mode,
                current_round_no=current_round_no,
                effective_payload_sequence=effective_payload_sequence,
            )
            ranked_candidates = self._rank_recommendation_candidates(
                training_mode=training_mode,
                effective_payload_sequence=recommendation_payload_sequence,
                completed_scenario_ids=completed_scenario_ids,
                k_state=k_state,
                s_state=s_state,
                recent_risk_rounds=recent_risk_rounds,
                current_round_no=current_round_no,
                total_rounds=len(list(session_sequence or effective_payload_sequence)),
            )
            if ranked_candidates:
                if self.recommendation_policy.is_strict_mode(training_mode or ""):
                    expected_id = str(ranked_candidates[0]["id"])
                    if str(submitted_scenario_id) != expected_id:
                        raise ValueError(
                            f"scenario mismatch: expected={expected_id}, submitted={submitted_scenario_id}, round={current_round_no + 1}"
                        )
                    return

                allowed_candidates = self._build_scenario_candidates(training_mode, ranked_candidates)
                allowed_ids = [str(item["id"]) for item in allowed_candidates if item.get("id")]
                if allowed_ids and str(submitted_scenario_id) not in allowed_ids:
                    raise ValueError(
                        f"scenario mismatch: allowed={','.join(allowed_ids)}, submitted={submitted_scenario_id}, round={current_round_no + 1}"
                    )
                return

            # 推荐候选为空时，回退到“按顺序挑第一个未完成场景”的兜底逻辑，
            # 避免在脏数据或异常状态下把已完成场景再次返回出来。
            fallback_payload = self._resolve_ordered_fallback_payload(
                training_mode=training_mode,
                current_round_no=current_round_no,
                effective_payload_sequence=effective_payload_sequence,
                completed_scenario_ids=completed_scenario_ids,
            )
            if fallback_payload is None:
                raise ValueError(
                    f"scenario mismatch: no available fallback scenario, submitted={submitted_scenario_id}, round={current_round_no + 1}"
                )

            expected_id = str(fallback_payload.get("id") or "").strip()
            if str(submitted_scenario_id) != expected_id:
                raise ValueError(
                    f"scenario mismatch: expected={expected_id}, submitted={submitted_scenario_id}, round={current_round_no + 1}"
                )
            return

        self.scenario_policy.validate_submission(
            current_round_no=current_round_no,
            submitted_scenario_id=submitted_scenario_id,
            session_sequence=list(session_sequence or []),
        )

    def is_session_completed(
        self,
        round_no: int,
        session_sequence: Sequence[Dict[str, Any]] | None,
    ) -> bool:
        """判断提交到当前回合后，会话是否应视为完成。"""
        total_rounds = len(list(session_sequence or []))
        if total_rounds <= 0:
            return False
        return int(round_no) >= total_rounds

    def is_terminal_state(
        self,
        round_no: int,
        session_sequence: Sequence[Dict[str, Any]] | None,
        session_status: str | None = None,
        has_ending: bool = False,
    ) -> bool:
        """统一判断幂等回包或查询结果是否应视为完成态。"""
        if has_ending:
            return True
        if str(session_status or "").strip().lower() == "completed":
            return True
        return self.is_session_completed(round_no=round_no, session_sequence=session_sequence)

    def _build_effective_payload_sequence(
        self,
        session_sequence: Sequence[Dict[str, Any]] | None,
        scenario_payload_sequence: Sequence[Dict[str, Any]] | None,
    ) -> List[Dict[str, Any]]:
        """优先使用完整场景快照，缺失时退回到会话摘要序列。"""
        if scenario_payload_sequence:
            return [dict(item) for item in scenario_payload_sequence if isinstance(item, dict)]
        return [dict(item) for item in session_sequence or [] if isinstance(item, dict)]

    def _resolve_ordered_fallback_payload(
        self,
        training_mode: str | None,
        current_round_no: int,
        effective_payload_sequence: Sequence[Dict[str, Any]],
        completed_scenario_ids: Iterable[str],
    ) -> Dict[str, Any] | None:
        """在推荐结果不可用时，按冻结顺序挑选第一个未完成场景。

        设计原则：
        1. 兜底路径不能返回已完成场景，否则会导致重复训练或回放错乱。
        2. 推荐模式下优先跳过未来强制节点，避免提前消费保留剧情。
        3. 如果只剩保留节点，则再退回到“未完成即可返回”，避免会话完全卡死。
        """
        unresolved_payloads = self._filter_completed_payloads(
            effective_payload_sequence=effective_payload_sequence,
            completed_scenario_ids=completed_scenario_ids,
        )
        if not unresolved_payloads:
            return None

        if self.recommendation_policy.supports_mode(training_mode or ""):
            non_reserved_payloads = self._filter_reserved_future_forced_payloads(
                training_mode=training_mode,
                current_round_no=current_round_no,
                effective_payload_sequence=unresolved_payloads,
            )
            if non_reserved_payloads:
                return dict(non_reserved_payloads[0])

        return dict(unresolved_payloads[0])

    def _filter_completed_payloads(
        self,
        effective_payload_sequence: Sequence[Dict[str, Any]],
        completed_scenario_ids: Iterable[str],
    ) -> List[Dict[str, Any]]:
        """过滤已经完成的场景，保证兜底路径不会重复返回历史题目。"""
        completed_ids = {
            str(scenario_id or "").strip()
            for scenario_id in completed_scenario_ids or []
            if str(scenario_id or "").strip()
        }
        if not completed_ids:
            return [dict(item) for item in effective_payload_sequence]

        return [
            dict(item)
            for item in effective_payload_sequence
            if str(item.get("id") or "").strip() not in completed_ids
        ]

    def _rank_recommendation_candidates(
        self,
        training_mode: str | None,
        effective_payload_sequence: Sequence[Dict[str, Any]],
        completed_scenario_ids: Iterable[str],
        k_state: Dict[str, float] | None = None,
        s_state: Dict[str, float] | None = None,
        recent_risk_rounds: Sequence[Sequence[str]] | None = None,
        current_round_no: int = 0,
        total_rounds: int | None = None,
    ) -> List[Dict[str, Any]]:
        """统一计算当前剩余候选场景的推荐顺序。"""
        return self.recommendation_policy.rank_candidates(
            training_mode=training_mode or "",
            scenario_payload_sequence=effective_payload_sequence,
            completed_scenario_ids=completed_scenario_ids,
            k_state=k_state,
            s_state=s_state,
            recent_risk_rounds=recent_risk_rounds,
            current_round_no=current_round_no,
            total_rounds=total_rounds,
        )

    def _build_scenario_candidates(
        self,
        training_mode: str | None,
        ranked_candidates: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """只给非严格推荐模式返回候选列表，避免破坏 adaptive 的既有交互。"""
        if self.recommendation_policy.is_strict_mode(training_mode or ""):
            return []

        candidate_limit = self._get_candidate_limit()
        return [dict(item) for item in ranked_candidates[:candidate_limit]]

    def _get_candidate_limit(self) -> int:
        """对候选数量做兜底，防止错误配置把 self-paced 变成不可选状态。"""
        try:
            configured_limit = int(self.runtime_config.recommendation.candidate_limit)
        except (TypeError, ValueError):
            return 1
        return max(1, configured_limit)

    def _resolve_forced_round_payload(
        self,
        training_mode: str | None,
        next_round_no: int,
        effective_payload_sequence: Sequence[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """解析当前轮次是否命中关键节点强制触发规则。"""
        forced_rule = self._match_forced_round_rule(
            training_mode=training_mode,
            next_round_no=next_round_no,
        )
        if forced_rule is None:
            return None

        forced_scenario_id = str(forced_rule.scenario_id).strip()
        for item in effective_payload_sequence:
            if str(item.get("id") or "").strip() == forced_scenario_id:
                return dict(item)

        raise ValueError(
            f"forced round scenario not found in session sequence: scenario_id={forced_scenario_id}, round={next_round_no}"
        )

    def _filter_reserved_future_forced_payloads(
        self,
        training_mode: str | None,
        current_round_no: int,
        effective_payload_sequence: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """过滤未来关键节点，避免推荐模式把保留节点提前消费掉。"""
        next_round_no = int(current_round_no) + 1
        reserved_scenario_ids = self._collect_future_forced_scenario_ids(
            training_mode=training_mode,
            next_round_no=next_round_no,
        )
        if not reserved_scenario_ids:
            return [dict(item) for item in effective_payload_sequence]

        return [
            dict(item)
            for item in effective_payload_sequence
            if str(item.get("id") or "").strip() not in reserved_scenario_ids
        ]

    def _collect_future_forced_scenario_ids(
        self,
        training_mode: str | None,
        next_round_no: int,
    ) -> set[str]:
        """收集当前轮次之后才允许出现的保留场景 ID。"""
        reserved_ids: set[str] = set()
        for rule in getattr(self.runtime_config.flow, "forced_rounds", []) or []:
            if not self._forced_round_rule_applies_to_mode(rule, training_mode):
                continue
            try:
                rule_round_no = int(rule.round_no)
            except (TypeError, ValueError):
                continue
            if rule_round_no > int(next_round_no):
                scenario_id = str(rule.scenario_id or "").strip()
                if scenario_id:
                    reserved_ids.add(scenario_id)
        return reserved_ids

    def _match_forced_round_rule(
        self,
        training_mode: str | None,
        next_round_no: int,
    ) -> Any | None:
        """按轮次和模式查找唯一生效的强制节点规则。"""
        matched_rules: List[Any] = []
        for rule in getattr(self.runtime_config.flow, "forced_rounds", []) or []:
            try:
                rule_round_no = int(rule.round_no)
            except (TypeError, ValueError):
                continue
            if rule_round_no != int(next_round_no):
                continue
            if not self._forced_round_rule_applies_to_mode(rule, training_mode):
                continue
            matched_rules.append(rule)

        if len(matched_rules) > 1:
            raise ValueError(
                f"multiple forced round rules matched: mode={training_mode}, round={next_round_no}"
            )
        return matched_rules[0] if matched_rules else None

    def _forced_round_rule_applies_to_mode(
        self,
        rule: Any,
        training_mode: str | None,
    ) -> bool:
        """判断强制节点规则是否适用于当前训练模式。"""
        configured_modes = list(getattr(rule, "modes", []) or [])
        if not configured_modes:
            return True

        normalized_training_mode = self.mode_catalog.normalize(
            training_mode,
            default="guided",
            raise_on_unknown=False,
        ) or "guided"
        normalized_modes = {
            normalized_mode
            for item in configured_modes
            for normalized_mode in [self.mode_catalog.normalize(item, raise_on_unknown=False)]
            if normalized_mode
        }
        return normalized_training_mode in normalized_modes
