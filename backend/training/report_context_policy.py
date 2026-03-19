"""训练报告上下文策略。

这一层负责把训练回放所需的上下文从原始行对象整理成稳定结构，
包括：
1. 报告起点状态
2. 场景标题索引
3. 报告 history
4. 报告 round_snapshots

这样可以继续缩小 TrainingService 的职责边界，
让 service 只负责取数与编排。
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from training.constants import DEFAULT_K_STATE, DEFAULT_S_STATE, SKILL_CODES
from training.contracts import RoundEvaluationPayload
from training.output_assembler_policy import TrainingOutputAssemblerPolicy
from training.runtime_artifact_policy import TrainingRuntimeArtifactPolicy
from training.training_outputs import (
    TrainingBranchTransitionOutput,
    TrainingConsequenceEventOutput,
    TrainingKtObservationOutput,
    TrainingReportHistoryItemOutput,
)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """统一裁剪状态值范围，避免历史脏数据把报告拉出边界。"""
    return max(lower, min(upper, float(value)))


def _safe_float(value: Any, default_value: float) -> float:
    """把任意脏值安全转换成 float。

    历史数据里可能出现：
    1. 非数字字符串
    2. None
    3. NaN / inf

    报告链路不应因为单个脏字段直接 500，所以统一回退到默认值。
    """
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return float(default_value)

    if math.isnan(normalized) or math.isinf(normalized):
        return float(default_value)
    return normalized


class TrainingReportContextPolicy:
    """训练报告上下文装配策略。"""

    def __init__(
        self,
        runtime_artifact_policy: TrainingRuntimeArtifactPolicy | None = None,
        output_assembler_policy: TrainingOutputAssemblerPolicy | None = None,
    ):
        self.runtime_artifact_policy = runtime_artifact_policy or TrainingRuntimeArtifactPolicy()
        self.output_assembler_policy = output_assembler_policy or TrainingOutputAssemblerPolicy()

    def resolve_report_initial_states(
        self,
        *,
        session: Any,
        rounds: List[Any],
    ) -> tuple[Dict[str, float], Dict[str, float]]:
        """解析报告 round=0 的起点状态。"""
        if rounds:
            first_round = rounds[0]
            return (
                self._normalize_k_state(getattr(first_round, "kt_before", None)),
                self._normalize_s_state(getattr(first_round, "state_before", None)),
            )
        return (
            self._normalize_k_state(getattr(session, "k_state", None)),
            self._normalize_s_state(getattr(session, "s_state", None)),
        )

    def build_report_scenario_title_map(
        self,
        scenario_payload_sequence: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """把冻结场景快照整理成标题索引，供报告时间线复用。"""
        title_map: Dict[str, str] = {}
        for payload in scenario_payload_sequence or []:
            scenario_id = str(payload.get("id") or "").strip()
            if not scenario_id:
                continue
            title_map[scenario_id] = str(payload.get("title") or scenario_id)
        return title_map

    def build_report_history(
        self,
        *,
        rounds: List[Any],
        eval_map: Dict[str, Any],
        kt_observation_map: Dict[int, Any],
    ) -> List[TrainingReportHistoryItemOutput]:
        """批量构建训练报告回放历史。"""
        history: List[TrainingReportHistoryItemOutput] = []
        for row in rounds:
            evaluation_row = eval_map.get(getattr(row, "round_id", ""))
            evaluation_output = None
            if evaluation_row is not None:
                # 报告回放统一走稳定评估 DTO，避免历史数据和实时接口各走一套契约。
                evaluation_output = self.output_assembler_policy.build_evaluation_output(
                    getattr(evaluation_row, "raw_payload", None)
                )

            history.append(
                TrainingReportHistoryItemOutput(
                    round_no=int(getattr(row, "round_no", 0) or 0),
                    scenario_id=str(getattr(row, "scenario_id", "") or ""),
                    user_input=str(getattr(row, "user_input_raw", "") or ""),
                    selected_option=getattr(row, "selected_option", None),
                    evaluation=evaluation_output,
                    k_state_before=self._normalize_k_state(getattr(row, "kt_before", None)),
                    k_state_after=self._normalize_k_state(getattr(row, "kt_after", None)),
                    s_state_before=self._normalize_s_state(getattr(row, "state_before", None)),
                    s_state_after=self._normalize_s_state(getattr(row, "state_after", None)),
                    timestamp=getattr(row, "created_at", None).isoformat() if getattr(row, "created_at", None) else None,
                    decision_context=self.runtime_artifact_policy.extract_round_decision_context(
                        getattr(row, "user_action", None)
                    ),
                    kt_observation=self._build_training_kt_observation_output(
                        kt_observation_map.get(int(getattr(row, "round_no", 0) or 0))
                    ),
                    runtime_state=self.runtime_artifact_policy.extract_round_runtime_state(
                        getattr(row, "user_action", None)
                    ),
                    consequence_events=self.runtime_artifact_policy.extract_round_consequence_events(
                        getattr(row, "user_action", None)
                    ),
                )
            )
        return history

    def build_report_round_snapshots(
        self,
        *,
        rounds: List[Any],
        eval_map: Dict[str, Any],
        kt_observation_map: Dict[int, Any],
        scenario_title_map: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """把回合行数据整理成报告聚合策略可直接消费的标准快照。"""
        snapshots: List[Dict[str, Any]] = []
        for row in rounds:
            round_no = int(getattr(row, "round_no", 0) or 0)
            scenario_id = str(getattr(row, "scenario_id", "") or "")
            evaluation_row = eval_map.get(getattr(row, "round_id", ""))
            evaluation_payload = RoundEvaluationPayload.from_raw(
                getattr(evaluation_row, "raw_payload", None)
            ).to_dict()
            kt_observation_output = self._build_training_kt_observation_output(
                kt_observation_map.get(round_no)
            )
            risk_flags = (
                list(kt_observation_output.risk_flags)
                if kt_observation_output is not None and kt_observation_output.risk_flags
                else [
                    str(flag)
                    for flag in evaluation_payload.get("risk_flags", [])
                    if str(flag or "").strip()
                ]
            )

            consequence_events = self.runtime_artifact_policy.extract_round_consequence_events(
                getattr(row, "user_action", None)
            )
            snapshots.append(
                {
                    "round_no": round_no,
                    "scenario_id": scenario_id,
                    "scenario_title": (
                        kt_observation_output.scenario_title
                        if kt_observation_output is not None and kt_observation_output.scenario_title
                        else scenario_title_map.get(scenario_id, scenario_id)
                    ),
                    "k_state": self._normalize_k_state(getattr(row, "kt_after", None)),
                    "s_state": self._normalize_s_state(getattr(row, "state_after", None)),
                    "is_high_risk": (
                        bool(kt_observation_output.is_high_risk)
                        if kt_observation_output is not None
                        else bool(risk_flags)
                    ),
                    "risk_flags": risk_flags,
                    "primary_skill_code": (
                        kt_observation_output.primary_skill_code
                        if kt_observation_output is not None
                        else None
                    ),
                    "runtime_flags": self.runtime_artifact_policy.extract_round_runtime_flags(
                        getattr(row, "user_action", None)
                    ),
                    "consequence_events": [
                        item.to_dict() if isinstance(item, TrainingConsequenceEventOutput) else item
                        for item in consequence_events
                    ],
                    "branch_transition": self._extract_round_branch_transition(
                        getattr(row, "user_action", None)
                    ),
                    "timestamp": (
                        getattr(row, "created_at", None).isoformat()
                        if getattr(row, "created_at", None)
                        else None
                    ),
                }
            )
        return snapshots

    def _extract_round_branch_transition(
        self,
        user_action: Dict[str, Any] | None,
    ) -> Dict[str, Any] | None:
        """从回合决策上下文中提取已选分支跳转。"""
        decision_context = self.runtime_artifact_policy.extract_round_decision_context(user_action)
        if decision_context is None:
            return None
        branch_transition = getattr(decision_context, "selected_branch_transition", None)
        if isinstance(branch_transition, TrainingBranchTransitionOutput):
            return branch_transition.to_dict()
        normalized_output = TrainingBranchTransitionOutput.from_payload(branch_transition)
        return normalized_output.to_dict() if normalized_output is not None else None

    def _build_training_kt_observation_output(self, row: Any) -> TrainingKtObservationOutput | None:
        """把 KT 观测行对象转换成稳定 DTO。"""
        return self.output_assembler_policy.build_kt_observation_output(row)

    def _normalize_state_value(
        self,
        source: Dict[str, Any] | None,
        key: str,
        default_value: float,
    ) -> float:
        """逐字段安全归一化状态值，避免脏历史把整条报告链路打挂。"""
        source_payload = source if isinstance(source, dict) else {}
        raw_value = source_payload.get(key, default_value)
        return round(_clamp(_safe_float(raw_value, default_value)), 4)

    def _normalize_k_state(self, k_state: Dict[str, float] | None) -> Dict[str, float]:
        """统一归一化 K 状态，避免报告链路各自兜底。"""
        return {
            code: self._normalize_state_value(k_state, code, DEFAULT_K_STATE[code])
            for code in SKILL_CODES
        }

    def _normalize_s_state(self, s_state: Dict[str, float] | None) -> Dict[str, float]:
        """统一归一化 S 状态，避免报告链路各自兜底。"""
        return {
            key: self._normalize_state_value(s_state, key, DEFAULT_S_STATE[key])
            for key in DEFAULT_S_STATE.keys()
        }
