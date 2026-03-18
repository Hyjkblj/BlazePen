"""训练报告与诊断聚合策略。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from training.constants import DEFAULT_S_STATE, SKILL_CODES, SKILL_WEIGHTS, TRAINING_RUNTIME_CONFIG
from training.training_outputs import (
    TrainingAuditEventOutput,
    TrainingDiagnosticsCountItemOutput,
    TrainingDiagnosticsSummaryOutput,
    TrainingKtObservationOutput,
    TrainingRecommendationLogOutput,
    TrainingReportCurvePointOutput,
    TrainingReportMetricOutput,
    TrainingReportSummaryOutput,
)
from training.runtime_events import (
    EVENT_EDITOR_LOCKED,
    EVENT_HIGH_RISK_PATH,
    EVENT_PUBLIC_PANIC_TRIGGERED,
    EVENT_SOURCE_EXPOSED,
)


@dataclass(slots=True)
class TrainingReportArtifacts:
    """训练报告聚合结果。"""

    summary: TrainingReportSummaryOutput
    ability_radar: List[TrainingReportMetricOutput]
    state_radar: List[TrainingReportMetricOutput]
    growth_curve: List[TrainingReportCurvePointOutput]


class TrainingReportingPolicy:
    """训练报告与诊断聚合策略。

    目标：
    1. 让 `TrainingService` 继续只负责编排和存储交互
    2. 把统计、计数、图表摘要、复盘建议等聚合逻辑下沉
    """

    def __init__(self, runtime_config: Any = None):
        self.runtime_config = runtime_config or TRAINING_RUNTIME_CONFIG
        self.skill_codes: Sequence[str] = tuple(self.runtime_config.skill_codes or SKILL_CODES)
        self.s_state_codes: Sequence[str] = tuple(self.runtime_config.s_state_codes or DEFAULT_S_STATE.keys())
        self.skill_weights: Dict[str, float] = {
            str(code): float(self.runtime_config.skill_weights.get(code, SKILL_WEIGHTS.get(code, 0.0)))
            for code in self.skill_codes
        }
        reporting_config = self.runtime_config.reporting
        self.max_review_suggestions = max(int(reporting_config.max_review_suggestions), 1)
        self.high_risk_round_preview_limit = max(int(reporting_config.high_risk_round_preview_limit), 1)
        self.weak_skill_threshold = float(reporting_config.thresholds.weak_skill_threshold)
        self.strong_improvement_threshold = float(reporting_config.thresholds.strong_improvement_threshold)
        self.limited_improvement_threshold = float(reporting_config.thresholds.limited_improvement_threshold)

    def build_diagnostics_summary(
        self,
        recommendation_logs: List[TrainingRecommendationLogOutput],
        audit_events: List[TrainingAuditEventOutput],
        kt_observations: List[TrainingKtObservationOutput],
    ) -> TrainingDiagnosticsSummaryOutput:
        """聚合训练诊断摘要。"""
        selection_source_counter: Counter[str] = Counter()
        event_type_counter: Counter[str] = Counter()
        risk_flag_counter: Counter[str] = Counter()
        primary_skill_counter: Counter[str] = Counter()
        weak_skill_counter: Counter[str] = Counter()
        phase_tag_counter: Counter[str] = Counter()
        mismatch_rounds: set[int] = set()
        high_risk_round_nos: set[int] = set()
        phase_transition_rounds: set[int] = set()
        panic_trigger_rounds: set[int] = set()
        source_exposed_rounds: set[int] = set()
        editor_locked_rounds: set[int] = set()
        high_risk_path_rounds: set[int] = set()
        last_primary_skill_code: str | None = None
        last_primary_risk_flag: str | None = None
        last_event_type: str | None = None
        last_phase_tags: List[str] = []

        for item in recommendation_logs:
            if item.selection_source:
                selection_source_counter[item.selection_source] += 1
            if (
                item.round_no is not None
                and item.recommended_scenario_id
                and item.selected_scenario_id
                and item.recommended_scenario_id != item.selected_scenario_id
            ):
                mismatch_rounds.add(int(item.round_no))

        for item in audit_events:
            if not item.event_type:
                continue
            event_type_counter[item.event_type] += 1
            last_event_type = item.event_type

            phase_tags = self._extract_phase_tags_from_audit_event(item)
            if phase_tags:
                last_phase_tags = phase_tags
                # 这里只统计真实提交轮次的阶段分布，避免初始化事件把首轮阶段重复算一次。
                if item.event_type == "round_submitted":
                    for phase_tag in phase_tags:
                        phase_tag_counter[phase_tag] += 1

            if item.event_type == "phase_transition" and item.round_no is not None:
                phase_transition_rounds.add(int(item.round_no))
            if item.event_type == EVENT_PUBLIC_PANIC_TRIGGERED and item.round_no is not None:
                panic_trigger_rounds.add(int(item.round_no))
            if item.event_type == EVENT_SOURCE_EXPOSED and item.round_no is not None:
                source_exposed_rounds.add(int(item.round_no))
            if item.event_type == EVENT_EDITOR_LOCKED and item.round_no is not None:
                editor_locked_rounds.add(int(item.round_no))
            if item.event_type == EVENT_HIGH_RISK_PATH and item.round_no is not None:
                high_risk_path_rounds.add(int(item.round_no))

        for item in kt_observations:
            if item.is_high_risk and item.round_no is not None:
                high_risk_round_nos.add(int(item.round_no))
            if item.primary_skill_code:
                primary_skill_counter[item.primary_skill_code] += 1
                last_primary_skill_code = item.primary_skill_code
            if item.primary_risk_flag:
                last_primary_risk_flag = item.primary_risk_flag

            for risk_flag in item.risk_flags:
                risk_flag_text = str(risk_flag or "").strip()
                if risk_flag_text:
                    risk_flag_counter[risk_flag_text] += 1

            for skill_code in item.weak_skills_before:
                skill_code_text = str(skill_code or "").strip()
                if skill_code_text:
                    weak_skill_counter[skill_code_text] += 1

        return TrainingDiagnosticsSummaryOutput(
            total_recommendation_logs=len(recommendation_logs),
            total_audit_events=len(audit_events),
            total_kt_observations=len(kt_observations),
            high_risk_round_count=len(high_risk_round_nos),
            high_risk_round_nos=sorted(high_risk_round_nos),
            recommended_vs_selected_mismatch_count=len(mismatch_rounds),
            recommended_vs_selected_mismatch_rounds=sorted(mismatch_rounds),
            risk_flag_counts=self._build_count_items(risk_flag_counter),
            primary_skill_focus_counts=self._build_count_items(primary_skill_counter),
            top_weak_skills=self._build_count_items(weak_skill_counter, limit=3),
            selection_source_counts=self._build_count_items(selection_source_counter),
            event_type_counts=self._build_count_items(event_type_counter),
            phase_tag_counts=self._build_count_items(phase_tag_counter),
            phase_transition_count=len(phase_transition_rounds),
            phase_transition_rounds=sorted(phase_transition_rounds),
            panic_trigger_round_count=len(panic_trigger_rounds),
            panic_trigger_rounds=sorted(panic_trigger_rounds),
            source_exposed_round_count=len(source_exposed_rounds),
            source_exposed_rounds=sorted(source_exposed_rounds),
            editor_locked_round_count=len(editor_locked_rounds),
            editor_locked_rounds=sorted(editor_locked_rounds),
            high_risk_path_round_count=len(high_risk_path_rounds),
            high_risk_path_rounds=sorted(high_risk_path_rounds),
            last_primary_skill_code=last_primary_skill_code,
            last_primary_risk_flag=last_primary_risk_flag,
            last_event_type=last_event_type,
            last_phase_tags=last_phase_tags,
        )

    def build_report_artifacts(
        self,
        initial_k_state: Dict[str, float],
        initial_s_state: Dict[str, float],
        final_k_state: Dict[str, float],
        final_s_state: Dict[str, float],
        round_snapshots: List[Dict[str, Any]],
    ) -> TrainingReportArtifacts:
        """聚合训练报告的图表与摘要数据。"""
        ability_radar = self.build_report_metric_outputs(
            initial_state=initial_k_state,
            final_state=final_k_state,
            ordered_codes=self.skill_codes,
            weight_map=self.skill_weights,
        )
        state_radar = self.build_report_metric_outputs(
            initial_state=initial_s_state,
            final_state=final_s_state,
            ordered_codes=self.s_state_codes,
        )
        growth_curve = self.build_report_growth_curve(
            initial_k_state=initial_k_state,
            initial_s_state=initial_s_state,
            round_snapshots=round_snapshots,
        )
        summary = self.build_report_summary(
            initial_k_state=initial_k_state,
            final_k_state=final_k_state,
            round_snapshots=round_snapshots,
            ability_radar=ability_radar,
        )
        return TrainingReportArtifacts(
            summary=summary,
            ability_radar=ability_radar,
            state_radar=state_radar,
            growth_curve=growth_curve,
        )

    def build_report_metric_outputs(
        self,
        initial_state: Dict[str, float],
        final_state: Dict[str, float],
        ordered_codes: Sequence[str],
        weight_map: Dict[str, float] | None = None,
    ) -> List[TrainingReportMetricOutput]:
        """把初始值和最终值转换成雷达图指标摘要。"""
        metrics: List[TrainingReportMetricOutput] = []
        codes = [str(code) for code in ordered_codes if str(code or "").strip()]
        if not codes:
            return metrics

        order_index = {code: index for index, code in enumerate(codes)}
        strongest_improved_code = max(
            codes,
            key=lambda code: (round(float(final_state.get(code, 0.0)) - float(initial_state.get(code, 0.0)), 4), -order_index[code]),
        )
        weakest_final_code = min(
            codes,
            key=lambda code: (float(final_state.get(code, 0.0)), order_index[code]),
        )

        for code in codes:
            initial_value = round(float(initial_state.get(code, 0.0)), 4)
            final_value = round(float(final_state.get(code, 0.0)), 4)
            metrics.append(
                TrainingReportMetricOutput(
                    code=code,
                    initial=initial_value,
                    final=final_value,
                    delta=round(final_value - initial_value, 4),
                    weight=(round(float(weight_map.get(code, 0.0)), 4) if weight_map and code in weight_map else None),
                    is_lowest_final=code == weakest_final_code,
                    is_highest_gain=code == strongest_improved_code,
                )
            )
        return metrics

    def build_report_growth_curve(
        self,
        initial_k_state: Dict[str, float],
        initial_s_state: Dict[str, float],
        round_snapshots: List[Dict[str, Any]],
    ) -> List[TrainingReportCurvePointOutput]:
        """构建训练成长曲线。

        这里固定补一个 `round=0` 起点，让前端不需要自己猜初始值。
        """
        curve: List[TrainingReportCurvePointOutput] = [
            TrainingReportCurvePointOutput(
                round_no=0,
                scenario_title="初始状态",
                k_state=dict(initial_k_state or {}),
                s_state=dict(initial_s_state or {}),
                weighted_k_score=round(self._weighted_k_score(initial_k_state), 4),
                risk_flags=[],
            )
        ]

        ordered_snapshots = sorted(
            (dict(item) for item in round_snapshots or [] if isinstance(item, dict)),
            key=lambda item: int(item.get("round_no", 0) or 0),
        )
        for snapshot in ordered_snapshots:
            curve.append(
                TrainingReportCurvePointOutput(
                    round_no=int(snapshot.get("round_no", 0) or 0),
                    scenario_id=snapshot.get("scenario_id"),
                    scenario_title=str(snapshot.get("scenario_title") or ""),
                    k_state=dict(snapshot.get("k_state", {}) or {}),
                    s_state=dict(snapshot.get("s_state", {}) or {}),
                    weighted_k_score=round(
                        float(snapshot.get("weighted_k_score", self._weighted_k_score(snapshot.get("k_state", {})))) or 0.0,
                        4,
                    ),
                    is_high_risk=bool(snapshot.get("is_high_risk", False)),
                    risk_flags=[str(item) for item in snapshot.get("risk_flags", []) if str(item or "").strip()],
                    primary_skill_code=snapshot.get("primary_skill_code"),
                    timestamp=snapshot.get("timestamp"),
                )
            )
        return curve

    def build_report_summary(
        self,
        initial_k_state: Dict[str, float],
        final_k_state: Dict[str, float],
        round_snapshots: List[Dict[str, Any]],
        ability_radar: List[TrainingReportMetricOutput],
    ) -> TrainingReportSummaryOutput:
        """聚合训练报告摘要。"""
        risk_flag_counter: Counter[str] = Counter()
        high_risk_round_nos: set[int] = set()
        completed_scenario_ids: List[str] = []
        panic_trigger_rounds: set[int] = set()
        source_exposed_rounds: set[int] = set()
        editor_locked_rounds: set[int] = set()
        high_risk_path_rounds: set[int] = set()

        for snapshot in round_snapshots or []:
            if not isinstance(snapshot, dict):
                continue
            round_no = int(snapshot.get("round_no", 0) or 0)
            scenario_id = str(snapshot.get("scenario_id") or "").strip()
            if scenario_id:
                completed_scenario_ids.append(scenario_id)

            risk_flags = [str(item) for item in snapshot.get("risk_flags", []) if str(item or "").strip()]
            if bool(snapshot.get("is_high_risk", False)) or risk_flags:
                high_risk_round_nos.add(round_no)
            for risk_flag in risk_flags:
                risk_flag_counter[risk_flag] += 1

            runtime_flags = dict(snapshot.get("runtime_flags", {}) or {})
            if bool(runtime_flags.get("panic_triggered", False)):
                panic_trigger_rounds.add(round_no)
            if bool(runtime_flags.get("source_exposed", False)):
                source_exposed_rounds.add(round_no)
            if bool(runtime_flags.get("editor_locked", False)):
                editor_locked_rounds.add(round_no)
            if bool(runtime_flags.get("high_risk_path", False)):
                high_risk_path_rounds.add(round_no)

        strongest_metric = max(
            ability_radar,
            key=lambda item: (item.delta, -list(self.skill_codes).index(item.code)),
        ) if ability_radar else None
        weakest_metric = min(
            ability_radar,
            key=lambda item: (item.final, list(self.skill_codes).index(item.code)),
        ) if ability_radar else None
        dominant_risk_flag = None
        if risk_flag_counter:
            dominant_risk_flag = sorted(
                risk_flag_counter.items(),
                key=lambda item: (-int(item[1]), str(item[0])),
            )[0][0]

        weighted_score_initial = round(self._weighted_k_score(initial_k_state), 4)
        weighted_score_final = round(self._weighted_k_score(final_k_state), 4)
        weighted_score_delta = round(weighted_score_final - weighted_score_initial, 4)
        return TrainingReportSummaryOutput(
            weighted_score_initial=weighted_score_initial,
            weighted_score_final=weighted_score_final,
            weighted_score_delta=weighted_score_delta,
            strongest_improved_skill_code=strongest_metric.code if strongest_metric is not None else None,
            strongest_improved_skill_delta=strongest_metric.delta if strongest_metric is not None else 0.0,
            weakest_skill_code=weakest_metric.code if weakest_metric is not None else None,
            weakest_skill_score=weakest_metric.final if weakest_metric is not None else 0.0,
            dominant_risk_flag=dominant_risk_flag,
            high_risk_round_count=len(high_risk_round_nos),
            high_risk_round_nos=sorted(high_risk_round_nos),
            panic_trigger_round_count=len(panic_trigger_rounds),
            source_exposed_round_count=len(source_exposed_rounds),
            editor_locked_round_count=len(editor_locked_rounds),
            high_risk_path_round_count=len(high_risk_path_rounds),
            risk_flag_counts=self._build_count_items(risk_flag_counter),
            completed_scenario_ids=completed_scenario_ids,
            review_suggestions=self._build_review_suggestions(
                weighted_score_delta=weighted_score_delta,
                weakest_metric=weakest_metric,
                dominant_risk_flag=dominant_risk_flag,
                high_risk_round_nos=sorted(high_risk_round_nos),
            ),
        )

    def _build_review_suggestions(
        self,
        weighted_score_delta: float,
        weakest_metric: TrainingReportMetricOutput | None,
        dominant_risk_flag: str | None,
        high_risk_round_nos: List[int],
    ) -> List[str]:
        """生成训练报告中的复盘建议。"""
        suggestions: List[str] = []

        if weakest_metric is not None and weakest_metric.final < self.weak_skill_threshold:
            suggestions.append(
                f"建议优先补练 {weakest_metric.code}，当前最终得分 {weakest_metric.final:.2f}，仍是本次训练最薄弱的能力项。"
            )

        if dominant_risk_flag:
            suggestions.append(
                f"本次训练最常见的风险标记是 {dominant_risk_flag}，建议围绕对应规则做专项复盘与重复练习。"
            )

        if high_risk_round_nos:
            round_labels = "、".join(str(item) for item in high_risk_round_nos[: self.high_risk_round_preview_limit])
            suggestions.append(
                f"共有 {len(high_risk_round_nos)} 轮触发高风险，建议优先回放第 {round_labels} 轮的决策过程。"
            )

        if weighted_score_delta >= self.strong_improvement_threshold:
            suggestions.append("综合能力已有明显提升，可以继续进入更高难度或更高压的训练场景。")
        elif weighted_score_delta <= self.limited_improvement_threshold:
            suggestions.append("本次综合提升有限，建议下一轮先聚焦单一短板能力，减少同时处理过多目标。")

        return suggestions[: self.max_review_suggestions]

    def _build_count_items(
        self,
        counter: Counter[str],
        limit: int | None = None,
    ) -> List[TrainingDiagnosticsCountItemOutput]:
        """把 Counter 结果转换成稳定 DTO。"""
        ordered_items = sorted(
            counter.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )
        if limit is not None:
            ordered_items = ordered_items[: max(int(limit), 0)]

        outputs: List[TrainingDiagnosticsCountItemOutput] = []
        for code, count in ordered_items:
            code_text = str(code or "").strip()
            if not code_text:
                continue
            outputs.append(
                TrainingDiagnosticsCountItemOutput(
                    code=code_text,
                    count=max(int(count), 0),
                )
            )
        return outputs

    def _extract_phase_tags_from_audit_event(
        self,
        audit_event: TrainingAuditEventOutput,
    ) -> List[str]:
        """从审计事件里提取当前阶段标签，供诊断摘要做轻量聚合。"""
        payload = dict(audit_event.payload or {})
        if audit_event.event_type == "phase_transition":
            phase_payload = payload.get("to_phase")
        else:
            phase_payload = payload.get("phase")

        if not isinstance(phase_payload, dict):
            return []
        return self._normalize_text_list(phase_payload.get("phase_tags"))

    def _normalize_text_list(self, values: Sequence[Any] | None) -> List[str]:
        """把标签列表整理成去重后的稳定字符串数组。"""
        normalized_values: List[str] = []
        for value in values or []:
            text = str(value or "").strip()
            if not text or text in normalized_values:
                continue
            normalized_values.append(text)
        return normalized_values

    def _weighted_k_score(self, k_state: Dict[str, float] | None) -> float:
        """按统一技能权重计算综合能力分。"""
        source = k_state or {}
        return sum(self.skill_weights.get(code, 0.0) * float(source.get(code, 0.0)) for code in self.skill_codes)
