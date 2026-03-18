"""训练下一题推荐策略。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from training.constants import DEFAULT_K_STATE, DEFAULT_S_STATE, TRAINING_RUNTIME_CONFIG
from training.phase_policy import TrainingPhasePolicy
from training.training_mode import TrainingModeCatalog


class RecommendationPolicy:
    """根据当前短板能力和剧情状态推荐下一训练场景。"""

    def __init__(self, runtime_config: Any = None, phase_policy: TrainingPhasePolicy | None = None):
        self.runtime_config = runtime_config or TRAINING_RUNTIME_CONFIG
        self.recommendation_config = self.runtime_config.recommendation
        self.mode_catalog = TrainingModeCatalog(runtime_config=self.runtime_config)
        # 阶段解析从推荐策略中抽离成独立 policy，便于审计和后续看板复用。
        self.phase_policy = phase_policy or TrainingPhasePolicy(runtime_config=self.runtime_config)

    def supports_mode(self, training_mode: str) -> bool:
        """判断当前训练模式是否启用推荐策略。"""
        return self.mode_catalog.is_recommendation_mode(training_mode)

    def is_strict_mode(self, training_mode: str) -> bool:
        """判断当前训练模式是否要求严格命中推荐场景。"""
        return self.mode_catalog.is_strict_mode(training_mode)

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
        """对剩余候选场景进行排序，并返回带推荐元信息的列表。"""
        canonical_mode = self.mode_catalog.normalize(training_mode, raise_on_unknown=False)
        if canonical_mode is None or not self.supports_mode(canonical_mode):
            return []

        completed_ids = {str(item) for item in completed_scenario_ids if item}
        scenario_order_map = self._build_scenario_order_map(scenario_payload_sequence)
        candidates = [
            dict(item)
            for item in scenario_payload_sequence or []
            if isinstance(item, dict) and str(item.get("id") or "") and str(item.get("id")) not in completed_ids
        ]
        if not candidates:
            return []

        normalized_k = self._normalize_state(k_state or {}, DEFAULT_K_STATE)
        normalized_s = self._normalize_state(s_state or {}, DEFAULT_S_STATE)
        normalized_recent_risk_rounds = self._normalize_recent_risk_rounds(recent_risk_rounds)
        total_rounds = max(len(scenario_payload_sequence or []), int(total_rounds or 0))
        active_phase_tags = self.phase_policy.resolve_next_round_phase(
            training_mode=canonical_mode,
            current_round_no=current_round_no,
            total_rounds=total_rounds,
        ).phase_tags
        scored_candidates: List[tuple[float, int, Dict[str, Any], Dict[str, Any]]] = []

        for index, scenario in enumerate(candidates):
            scenario_id = str(scenario.get("id") or "")
            weakness_score = self._calculate_weakness_score(scenario, normalized_k)
            state_boost, boost_reasons = self._calculate_state_boost(scenario, normalized_s)
            risk_boost, risk_reasons = self._calculate_recent_risk_boost(scenario, normalized_recent_risk_rounds)
            phase_boost, phase_reasons = self._calculate_phase_boost(
                scenario=scenario,
                sequence_index=scenario_order_map.get(scenario_id, index),
                current_round_no=current_round_no,
                total_rounds=total_rounds,
                active_phase_tags=active_phase_tags,
            )
            total_score = round(
                weakness_score * self.recommendation_config.weights.weakness
                + state_boost * self.recommendation_config.weights.state_boost,
                4,
            )
            total_score = round(
                total_score
                + risk_boost * self.recommendation_config.weights.recent_risk
                + phase_boost * self.recommendation_config.weights.phase_alignment,
                4,
            )
            recommendation_meta = {
                "mode": canonical_mode,
                "rank_score": total_score,
                "weakness_score": round(weakness_score, 4),
                "state_boost_score": round(state_boost, 4),
                "risk_boost_score": round(risk_boost, 4),
                "phase_boost_score": round(phase_boost, 4),
                "reasons": boost_reasons + risk_reasons + phase_reasons,
            }
            scored_candidates.append((total_score, -index, scenario, recommendation_meta))

        scored_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)

        ranked_candidates: List[Dict[str, Any]] = []
        for rank_index, (_, _, scenario, recommendation_meta) in enumerate(scored_candidates, start=1):
            scenario_payload = dict(scenario)
            scenario_payload["recommendation"] = {
                **recommendation_meta,
                "rank": rank_index,
            }
            ranked_candidates.append(scenario_payload)
        return ranked_candidates

    def recommend_next(
        self,
        training_mode: str,
        scenario_payload_sequence: Sequence[Dict[str, Any]],
        completed_scenario_ids: Iterable[str],
        k_state: Dict[str, float] | None = None,
        s_state: Dict[str, float] | None = None,
        recent_risk_rounds: Sequence[Sequence[str]] | None = None,
        current_round_no: int = 0,
        total_rounds: int | None = None,
    ) -> Optional[Dict[str, Any]]:
        """在推荐模式下，根据当前状态选择下一题。"""
        ranked_candidates = self.rank_candidates(
            training_mode=training_mode,
            scenario_payload_sequence=scenario_payload_sequence,
            completed_scenario_ids=completed_scenario_ids,
            k_state=k_state,
            s_state=s_state,
            recent_risk_rounds=recent_risk_rounds,
            current_round_no=current_round_no,
            total_rounds=total_rounds,
        )
        if not ranked_candidates:
            return None
        return ranked_candidates[0]

    def _calculate_weakness_score(self, scenario: Dict[str, Any], k_state: Dict[str, float]) -> float:
        """根据场景目标能力计算短板覆盖价值。"""
        target_skills = [str(code) for code in scenario.get("target_skills", []) if str(code)]
        if not target_skills:
            return 0.0

        weaknesses = [max(0.0, 1.0 - float(k_state.get(skill_code, 0.0))) for skill_code in target_skills]
        return sum(weaknesses) / max(len(weaknesses), 1)

    def _calculate_state_boost(self, scenario: Dict[str, Any], s_state: Dict[str, float]) -> tuple[float, List[str]]:
        """根据当前剧情状态给相关场景追加推荐权重。"""
        target_skills = {str(code) for code in scenario.get("target_skills", []) if str(code)}
        total_boost = 0.0
        reasons: List[str] = []

        for boost_config in self.recommendation_config.state_boosts:
            if not target_skills.intersection(set(boost_config.boost_skills)):
                continue

            current_value = float(s_state.get(boost_config.state_key, 0.0))
            matched = False
            if boost_config.trigger == "lt":
                matched = current_value < float(boost_config.threshold)
            elif boost_config.trigger == "gt":
                matched = current_value > float(boost_config.threshold)

            if matched:
                total_boost += float(boost_config.boost)
                if boost_config.reason:
                    reasons.append(str(boost_config.reason))

        return total_boost, reasons

    def _build_scenario_order_map(self, scenario_payload_sequence: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        """记录场景在原始序列中的位置，供阶段对齐打分使用。"""
        order_map: Dict[str, int] = {}
        for index, scenario in enumerate(scenario_payload_sequence or []):
            if not isinstance(scenario, dict):
                continue
            scenario_id = str(scenario.get("id") or "").strip()
            if not scenario_id or scenario_id in order_map:
                continue
            order_map[scenario_id] = index
        return order_map

    def _calculate_recent_risk_boost(
        self,
        scenario: Dict[str, Any],
        recent_risk_rounds: Sequence[Sequence[str]],
    ) -> tuple[float, List[str]]:
        """根据最近几轮反复出现的风险，优先推荐补救性训练题。"""
        target_skills = {str(code) for code in scenario.get("target_skills", []) if str(code)}
        if not target_skills or not recent_risk_rounds:
            return 0.0, []

        total_boost = 0.0
        reasons: List[str] = []
        for boost_config in self.recommendation_config.risk_boosts:
            if not target_skills.intersection(set(boost_config.boost_skills)):
                continue

            window_rounds = recent_risk_rounds[-max(int(self.recommendation_config.recent_risk_window), 1):]
            hit_rounds = [round_flags for round_flags in window_rounds if boost_config.risk_flag in round_flags]
            if not hit_rounds:
                continue

            total_boost += float(boost_config.boost)
            streak = self._count_consecutive_risk_rounds(window_rounds, boost_config.risk_flag)
            if streak > 1:
                total_boost += float(boost_config.consecutive_bonus) * float(streak - 1)

            if boost_config.reason:
                reasons.append(str(boost_config.reason))

        return total_boost, reasons

    def _calculate_phase_boost(
        self,
        scenario: Dict[str, Any],
        sequence_index: int,
        current_round_no: int,
        total_rounds: int,
        active_phase_tags: Sequence[str] | None = None,
    ) -> tuple[float, List[str]]:
        """根据当前训练阶段计算剧情节奏加权。

        优先级规则：
        1. 如果当前轮次命中了阶段窗口，且场景本身带有阶段标签，则优先使用“阶段标签匹配”加权。
        2. 如果没有阶段窗口，或场景没有阶段标签，则回退到旧的“按序列距离加权”逻辑。
        """
        scenario_phase_tags = self._extract_scenario_phase_tags(scenario)
        normalized_active_phase_tags = self._normalize_text_list(active_phase_tags)
        if self._should_use_stage_phase_alignment(
            active_phase_tags=normalized_active_phase_tags,
            scenario_phase_tags=scenario_phase_tags,
        ):
            stage_boost, stage_reasons = self._calculate_stage_phase_boost(
                active_phase_tags=normalized_active_phase_tags,
                scenario_phase_tags=scenario_phase_tags,
            )
            if stage_boost <= 0:
                return stage_boost, stage_reasons

            # 当多个场景同时命中同一阶段标签时，再用旧的距离加权做细粒度排序，
            # 这样既保留阶段节奏，又不会丢掉“相邻场景更自然”的原有体验。
            distance_boost, distance_reasons = self._calculate_distance_phase_boost(
                sequence_index=sequence_index,
                current_round_no=current_round_no,
                total_rounds=total_rounds,
            )
            return stage_boost + distance_boost, stage_reasons + distance_reasons

        return self._calculate_distance_phase_boost(
            sequence_index=sequence_index,
            current_round_no=current_round_no,
            total_rounds=total_rounds,
        )

    def _calculate_stage_phase_boost(
        self,
        active_phase_tags: Sequence[str],
        scenario_phase_tags: Sequence[str],
    ) -> tuple[float, List[str]]:
        """使用“当前阶段标签 -> 场景阶段标签”规则做阶段推荐。"""
        active_phase_tag_set = set(active_phase_tags)
        scenario_phase_tag_set = set(scenario_phase_tags)
        total_boost = 0.0
        reasons: List[str] = []

        for boost_config in self.recommendation_config.phase_boosts:
            current_phase_tags = self._normalize_text_list(getattr(boost_config, "current_phase_tags", []))
            target_phase_tags = self._normalize_text_list(getattr(boost_config, "scenario_phase_tags", []))
            if not current_phase_tags or not target_phase_tags:
                continue
            if not active_phase_tag_set.intersection(current_phase_tags):
                continue
            if not scenario_phase_tag_set.intersection(target_phase_tags):
                continue

            total_boost += float(boost_config.boost)
            if boost_config.reason:
                reasons.append(str(boost_config.reason))

        return total_boost, reasons

    def _calculate_distance_phase_boost(
        self,
        sequence_index: int,
        current_round_no: int,
        total_rounds: int,
    ) -> tuple[float, List[str]]:
        """兼容旧配置的距离加权逻辑，供未配置阶段标签时兜底。"""
        if total_rounds <= 0:
            return 0.0, []

        target_index = min(max(int(current_round_no), 0), max(total_rounds - 1, 0))
        distance = abs(int(sequence_index) - target_index)
        total_boost = 0.0
        reasons: List[str] = []

        for boost_config in self.recommendation_config.phase_boosts:
            configured_distance = getattr(boost_config, "distance", None)
            if configured_distance is None:
                continue
            if distance != int(configured_distance):
                continue
            total_boost += float(boost_config.boost)
            if boost_config.reason:
                reasons.append(str(boost_config.reason))

        return total_boost, reasons

    def _should_use_stage_phase_alignment(
        self,
        active_phase_tags: Sequence[str],
        scenario_phase_tags: Sequence[str],
    ) -> bool:
        """只有在双方都带阶段标签且配置中存在阶段匹配规则时，才启用新阶段算法。"""
        if not active_phase_tags or not scenario_phase_tags:
            return False
        return any(
            self._is_stage_phase_boost_config(boost_config)
            for boost_config in self.recommendation_config.phase_boosts
        )

    def _is_stage_phase_boost_config(self, boost_config: Any) -> bool:
        """判断当前阶段加权配置是否属于“阶段标签匹配”规则。"""
        return bool(
            self._normalize_text_list(getattr(boost_config, "current_phase_tags", []))
            and self._normalize_text_list(getattr(boost_config, "scenario_phase_tags", []))
        )

    def _extract_scenario_phase_tags(self, scenario: Dict[str, Any]) -> List[str]:
        """从场景定义中提取并归一化阶段标签。"""
        return self._normalize_text_list(scenario.get("phase_tags", []))

    def _normalize_text_list(self, values: Sequence[Any] | None) -> List[str]:
        """把标签列表规整成去重后的字符串数组，避免配置脏数据影响匹配。"""
        normalized_values: List[str] = []
        for value in values or []:
            text = str(value or "").strip()
            if not text or text in normalized_values:
                continue
            normalized_values.append(text)
        return normalized_values

    def _normalize_recent_risk_rounds(
        self,
        recent_risk_rounds: Sequence[Sequence[str]] | None,
    ) -> List[List[str]]:
        """把最近风险历史归一成按回合分组的稳定结构。"""
        normalized: List[List[str]] = []
        for round_flags in recent_risk_rounds or []:
            if not isinstance(round_flags, (list, tuple, set)):
                continue

            normalized_round_flags: List[str] = []
            for flag in round_flags:
                flag_text = str(flag or "").strip()
                if not flag_text or flag_text in normalized_round_flags:
                    continue
                normalized_round_flags.append(flag_text)
            normalized.append(normalized_round_flags)
        return normalized

    def _count_consecutive_risk_rounds(
        self,
        recent_risk_rounds: Sequence[Sequence[str]],
        risk_flag: str,
    ) -> int:
        """统计某个风险在最近几轮末尾连续出现了多少轮。"""
        consecutive_rounds = 0
        for round_flags in reversed(list(recent_risk_rounds or [])):
            if risk_flag not in round_flags:
                break
            consecutive_rounds += 1
        return consecutive_rounds

    def _normalize_state(self, source: Dict[str, float], defaults: Dict[str, float]) -> Dict[str, float]:
        """把状态字典补齐成稳定结构。"""
        normalized = dict(defaults)
        for key in defaults.keys():
            if key in source:
                normalized[key] = float(source.get(key, defaults[key]))
        return normalized
