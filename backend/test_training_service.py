"""训练服务编排层单元测试（不依赖真实数据库）。"""

from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from api.services.training_service import TrainingService
from database.db_manager import DatabaseManager
from training.constants import DEFAULT_EVAL_MODEL, DEFAULT_K_STATE, DEFAULT_S_STATE, S_STATE_CODES, SKILL_CODES
from training.config_loader import FlowForcedRoundConfig, ScenarioItemConfig, load_training_runtime_config, model_copy
from training.exceptions import (
    DuplicateRoundSubmissionError,
    TrainingModeUnsupportedError,
    TrainingScenarioMismatchError,
    TrainingSessionRecoveryStateError,
)
from training.output_assembler_policy import TrainingOutputAssemblerPolicy
from training.report_context_policy import TrainingReportContextPolicy
from training.round_transition_policy import TrainingRoundTransitionPolicy
from training.scenario_policy import ScenarioPolicy
from training.scenario_repository import ScenarioRepository
from training.session_snapshot_policy import SessionScenarioSnapshotPolicy
from training.runtime_artifact_policy import TrainingRuntimeArtifactPolicy
from training.training_outputs import (
    TrainingConsequenceEventOutput,
    TrainingRoundDecisionContextOutput,
    TrainingRuntimeStateOutput,
)
from training.training_store import DatabaseTrainingStore


class _FakeEvaluator:
    """稳定评估器桩：用于校验服务编排，不引入随机性。"""

    def evaluate_round(self, **kwargs):
        skill_delta = {code: 0.01 for code in SKILL_CODES}
        s_delta = {code: 0.0 for code in S_STATE_CODES}
        preview = {code: min(1.0, DEFAULT_K_STATE[code] + skill_delta[code]) for code in SKILL_CODES}
        return {
            "llm_model": DEFAULT_EVAL_MODEL,
            "confidence": 0.8,
            "risk_flags": [],
            "skill_delta": skill_delta,
            "s_delta": s_delta,
            "evidence": ["ok"],
            "skill_scores_preview": preview,
            "eval_mode": "rules_only",
        }


class _MalformedEvaluator:
    """异常评估器桩：故意返回不完整字段，验证契约归一化能力。"""

    def evaluate_round(self, **kwargs):
        return {
            "confidence": "not-a-number",
            "risk_flags": "bad-type",
            "skill_delta": {"K1": "0.2"},
            "evidence": None,
        }


class _RiskFlagEvaluator:
    """风险标签评估器桩：验证契约会统一标签格式。"""

    def evaluate_round(self, **kwargs):
        return {
            "llm_model": DEFAULT_EVAL_MODEL,
            "confidence": 0.9,
            "risk_flags": ["Source Exposure Risk", "Source Exposure Risk"],
            "skill_delta": {"K1": 0.01},
            "s_delta": {},
            "evidence": ["存在来源暴露风险"],
        }


class _PublicPanicEvaluator:
    """公众恐慌评估器桩：验证后果引擎会触发公众稳定度后果。"""

    def evaluate_round(self, **kwargs):
        return {
            "llm_model": DEFAULT_EVAL_MODEL,
            "confidence": 0.88,
            "risk_flags": ["high_risk_unverified_publish"],
            "skill_delta": {"K1": -0.02},
            "s_delta": {"public_panic": 0.5},
            "evidence": ["存在未经核实即发布风险"],
        }


class _PanicRecoveryEvaluator:
    """恐慌恢复评估器桩：用于验证补救分支会清除恐慌状态。"""

    def evaluate_round(self, **kwargs):
        return {
            "llm_model": DEFAULT_EVAL_MODEL,
            "confidence": 0.86,
            "risk_flags": [],
            "skill_delta": {"K4": 0.02, "K8": 0.03},
            "s_delta": {"public_panic": -0.5, "editor_trust": 0.1},
            "evidence": ["通过澄清与行动指引修复了群众稳定度。"],
        }


class _RecentSourceRiskEvaluator:
    """最近风险评估器桩：验证推荐链路会读取历史风险而不只看静态 K/S。"""

    def evaluate_round(self, **kwargs):
        return {
            "llm_model": DEFAULT_EVAL_MODEL,
            "confidence": 0.85,
            "risk_flags": ["source_exposure_risk"],
            "skill_delta": {},
            "s_delta": {},
            "evidence": ["出现来源暴露风险，需要优先补练来源保护相关题目"],
        }


class _ChangedScenarioRepository:
    """模拟场景库发版后的新版本仓储，用于验证会话冻结快照优先级。"""

    version = "scenario_bank_changed_v1"

    def freeze_sequence(self, scenario_sequence):
        frozen = []
        for item in scenario_sequence or []:
            frozen.append(
                {
                    "id": item["id"],
                    "title": item.get("title") or item["id"],
                    "briefing": "这是变更后的最新场景正文",
                    "mission": "这是变更后的任务目标",
                    "target_skills": ["K8"],
                    "risk_tags": ["changed"],
                    "options": [],
                }
            )
        return frozen

    def build_summary_sequence(self, scenario_payload_sequence):
        return [
            {
                "id": item["id"],
                "title": item.get("title") or item["id"],
            }
            for item in scenario_payload_sequence
        ]

    def freeze_related_catalog(self, scenario_sequence):
        """保持与正式仓储一致的接口，便于训练服务统一冻结场景目录。"""
        return self.freeze_sequence(scenario_sequence)

    def get_scenario(self, scenario_id):
        """模拟新版仓储读取单场景定义。"""
        return {
            "id": str(scenario_id),
            "title": str(scenario_id),
            "briefing": "这是变更后的最新场景正文",
            "mission": "这是变更后的任务目标",
            "target_skills": ["K8"],
            "risk_tags": ["changed"],
            "options": [],
            "next_rules": [],
        }


class _FailOnScenarioReadRepository:
    """用于验证老会话分支解析不会回退读取实时仓储。"""

    def get_scenario(self, scenario_id):
        raise AssertionError(f"unexpected repository fallback: {scenario_id}")


class _SpySessionSnapshotPolicy:
    """会话快照策略桩：验证服务层确实通过可注入策略管理场景快照。"""

    def __init__(self, delegate):
        self.delegate = delegate
        self.freeze_call_count = 0
        self.require_call_count = 0
        self.resolve_call_count = 0

    def freeze_session_snapshots(self, session_sequence):
        self.freeze_call_count += 1
        return self.delegate.freeze_session_snapshots(session_sequence)

    def ensure_session_snapshots(self, *, session, training_store):
        return self.delegate.ensure_session_snapshots(session=session, training_store=training_store)

    def require_session_snapshots(self, *, session_id, session):
        self.require_call_count += 1
        return self.delegate.require_session_snapshots(session_id=session_id, session=session)

    def resolve_scenario_payload_by_id(self, *, scenario_id, scenario_payload_sequence, scenario_payload_catalog=None):
        self.resolve_call_count += 1
        return self.delegate.resolve_scenario_payload_by_id(
            scenario_id=scenario_id,
            scenario_payload_sequence=scenario_payload_sequence,
            scenario_payload_catalog=scenario_payload_catalog,
        )


class _SpyDecisionContextPolicy:
    """决策上下文策略桩：验证服务层确实把上下文组装委托给独立策略。"""

    def __init__(self):
        self.calls = []

    def build_round_decision_context(self, *, training_mode, submitted_scenario_id, next_scenario_bundle):
        # 这里返回稳定 DTO，确保 submit_round 全链路都走到策略输出，而不是再回退到服务层旧逻辑。
        self.calls.append(
            {
                "training_mode": training_mode,
                "submitted_scenario_id": submitted_scenario_id,
                "next_scenario_bundle": next_scenario_bundle,
            }
        )
        return TrainingRoundDecisionContextOutput.from_payload(
            {
                "mode": training_mode,
                "selection_source": "spy_policy",
                "selected_scenario_id": submitted_scenario_id,
                "recommended_scenario_id": submitted_scenario_id,
                "candidate_pool": [
                    {
                        "scenario_id": submitted_scenario_id,
                        "title": "Spy Scenario",
                        "rank": 1,
                        "rank_score": 0.99,
                        "is_selected": True,
                        "is_recommended": True,
                    }
                ],
            }
        )


class _SpyRuntimeArtifactPolicy:
    """运行时工件策略桩：验证服务层确实把运行时状态和 user_action 契约委托给独立策略。"""

    def __init__(self, delegate):
        self.delegate = delegate
        self.build_default_flags_call_count = 0
        self.resolve_flags_call_count = 0
        self.merge_flags_call_count = 0
        self.build_runtime_state_call_count = 0
        self.build_round_user_action_call_count = 0
        self.attach_runtime_artifacts_call_count = 0
        self.extract_runtime_state_call_count = 0
        self.extract_runtime_flags_call_count = 0
        self.extract_consequence_events_call_count = 0
        self.extract_decision_context_call_count = 0

    def build_default_runtime_flags(self):
        self.build_default_flags_call_count += 1
        return self.delegate.build_default_runtime_flags()

    def resolve_session_runtime_flags(self, session):
        self.resolve_flags_call_count += 1
        return self.delegate.resolve_session_runtime_flags(session)

    def merge_session_meta_runtime_flags(self, *, session_meta, runtime_flags):
        self.merge_flags_call_count += 1
        return self.delegate.merge_session_meta_runtime_flags(
            session_meta=session_meta,
            runtime_flags=runtime_flags,
        )

    def build_runtime_state(
        self,
        *,
        session,
        player_profile=None,
        current_round_no=None,
        current_scene_id=None,
        k_state=None,
        s_state=None,
        runtime_flags=None,
    ):
        self.build_runtime_state_call_count += 1
        return self.delegate.build_runtime_state(
            session=session,
            player_profile=player_profile,
            current_round_no=current_round_no,
            current_scene_id=current_scene_id,
            k_state=k_state,
            s_state=s_state,
            runtime_flags=runtime_flags,
        )

    def build_round_user_action(self, *, user_input, selected_option, decision_context):
        self.build_round_user_action_call_count += 1
        return self.delegate.build_round_user_action(
            user_input=user_input,
            selected_option=selected_option,
            decision_context=decision_context,
        )

    def attach_runtime_artifacts_to_user_action(
        self,
        *,
        user_action,
        runtime_state,
        consequence_events,
        branch_hints=None,
    ):
        self.attach_runtime_artifacts_call_count += 1
        return self.delegate.attach_runtime_artifacts_to_user_action(
            user_action=user_action,
            runtime_state=runtime_state,
            consequence_events=consequence_events,
            branch_hints=branch_hints,
        )

    def extract_round_runtime_state(self, user_action):
        self.extract_runtime_state_call_count += 1
        return self.delegate.extract_round_runtime_state(user_action)

    def extract_round_runtime_flags(self, user_action):
        self.extract_runtime_flags_call_count += 1
        return self.delegate.extract_round_runtime_flags(user_action)

    def extract_round_consequence_events(self, user_action):
        self.extract_consequence_events_call_count += 1
        return self.delegate.extract_round_consequence_events(user_action)

    def extract_round_decision_context(self, user_action):
        self.extract_decision_context_call_count += 1
        return self.delegate.extract_round_decision_context(user_action)


class _CustomContractRuntimeArtifactPolicy(TrainingRuntimeArtifactPolicy):
    """Use custom storage keys so replay/report must reuse the same runtime contract."""

    _DECISION_CONTEXT_KEY = "custom_decision_context"
    _RUNTIME_STATE_KEY = "custom_runtime_state"
    _CONSEQUENCE_EVENTS_KEY = "custom_consequence_events"

    def build_round_user_action(self, *, user_input, selected_option, decision_context):
        payload = {
            "text": user_input,
            "selected_option": selected_option,
        }
        if decision_context is not None:
            payload[self._DECISION_CONTEXT_KEY] = decision_context.to_dict()
        return payload

    def attach_runtime_artifacts_to_user_action(
        self,
        *,
        user_action,
        runtime_state,
        consequence_events,
        branch_hints=None,
    ):
        payload = dict(user_action or {})
        payload[self._RUNTIME_STATE_KEY] = runtime_state.to_dict()
        payload[self._CONSEQUENCE_EVENTS_KEY] = [item.to_dict() for item in consequence_events or []]
        if branch_hints:
            payload["custom_branch_hints"] = [
                str(item) for item in branch_hints if str(item or "").strip()
            ]
        return payload

    def extract_round_decision_context(self, user_action):
        if not isinstance(user_action, dict):
            return None
        return TrainingRoundDecisionContextOutput.from_payload(user_action.get(self._DECISION_CONTEXT_KEY))

    def extract_round_runtime_state(self, user_action):
        if not isinstance(user_action, dict):
            return None
        return TrainingRuntimeStateOutput.from_payload(user_action.get(self._RUNTIME_STATE_KEY))

    def extract_round_consequence_events(self, user_action):
        if not isinstance(user_action, dict):
            return []

        outputs = []
        for item in user_action.get(self._CONSEQUENCE_EVENTS_KEY) or []:
            output = TrainingConsequenceEventOutput.from_payload(item)
            if output is not None:
                outputs.append(output)
        return outputs


class _SpyOutputAssemblerPolicy:
    """输出装配策略桩：验证服务层确实把 DTO 转换委托给独立策略。"""

    def __init__(self, delegate):
        self.delegate = delegate
        self.build_scenario_output_call_count = 0
        self.build_scenario_output_list_call_count = 0
        self.build_player_profile_output_call_count = 0
        self.build_evaluation_output_call_count = 0
        self.build_runtime_state_output_call_count = 0
        self.build_consequence_event_outputs_call_count = 0
        self.build_kt_observation_output_call_count = 0
        self.build_kt_observation_outputs_call_count = 0
        self.build_recommendation_log_outputs_call_count = 0
        self.build_audit_event_outputs_call_count = 0

    def build_scenario_output(self, payload):
        self.build_scenario_output_call_count += 1
        return self.delegate.build_scenario_output(payload)

    def build_scenario_output_list(self, payloads):
        self.build_scenario_output_list_call_count += 1
        outputs = []
        for item in payloads or []:
            output = self.build_scenario_output(item)
            if output is not None:
                outputs.append(output)
        return outputs if payloads is not None else None

    def build_player_profile_output(self, payload):
        self.build_player_profile_output_call_count += 1
        return self.delegate.build_player_profile_output(payload)

    def build_evaluation_output(self, payload):
        self.build_evaluation_output_call_count += 1
        return self.delegate.build_evaluation_output(payload)

    def build_runtime_state_output(self, runtime_state):
        self.build_runtime_state_output_call_count += 1
        return self.delegate.build_runtime_state_output(runtime_state)

    def build_consequence_event_output(self, payload):
        return self.delegate.build_consequence_event_output(payload)

    def build_consequence_event_outputs(self, payloads):
        self.build_consequence_event_outputs_call_count += 1
        return self.delegate.build_consequence_event_outputs(payloads)

    def build_kt_observation_output(self, row):
        self.build_kt_observation_output_call_count += 1
        return self.delegate.build_kt_observation_output(row)

    def build_kt_observation_outputs(self, rows):
        self.build_kt_observation_outputs_call_count += 1
        outputs = []
        for row in rows:
            output = self.build_kt_observation_output(row)
            if output is not None:
                outputs.append(output)
        return outputs

    def build_recommendation_log_output(self, row):
        return self.delegate.build_recommendation_log_output(row)

    def build_recommendation_log_outputs(self, rows):
        self.build_recommendation_log_outputs_call_count += 1
        return self.delegate.build_recommendation_log_outputs(rows)

    def build_audit_event_output(self, row):
        return self.delegate.build_audit_event_output(row)

    def build_audit_event_outputs(self, rows):
        self.build_audit_event_outputs_call_count += 1
        return self.delegate.build_audit_event_outputs(rows)


class _SpyRoundTransitionPolicy:
    """回合推进策略桩：验证服务层确实把状态推进委托给独立策略。"""

    def __init__(self, delegate):
        self.delegate = delegate
        self.runtime_artifact_policy = delegate.runtime_artifact_policy
        self.calls = []

    def build_round_transition_artifacts(
        self,
        *,
        session,
        evaluator,
        consequence_engine,
        round_no,
        scenario_id,
        user_input,
        selected_option,
        decision_context,
        k_before,
        s_before,
        recent_risk_rounds,
        scenario_payload,
    ):
        self.calls.append(
            {
                "round_no": round_no,
                "scenario_id": scenario_id,
                "user_input": user_input,
                "selected_option": selected_option,
                "decision_context": decision_context,
            }
        )
        return self.delegate.build_round_transition_artifacts(
            session=session,
            evaluator=evaluator,
            consequence_engine=consequence_engine,
            round_no=round_no,
            scenario_id=scenario_id,
            user_input=user_input,
            selected_option=selected_option,
            decision_context=decision_context,
            k_before=k_before,
            s_before=s_before,
            recent_risk_rounds=recent_risk_rounds,
            scenario_payload=scenario_payload,
        )


class _SpyReportContextPolicy:
    """报告上下文策略桩：验证服务层确实把报告 history/snapshot 装配委托给独立策略。"""

    def __init__(self, delegate):
        self.delegate = delegate
        self.runtime_artifact_policy = delegate.runtime_artifact_policy
        self.output_assembler_policy = delegate.output_assembler_policy
        self.resolve_initial_states_call_count = 0
        self.build_title_map_call_count = 0
        self.build_history_call_count = 0
        self.build_round_snapshots_call_count = 0

    def resolve_report_initial_states(self, *, session, rounds):
        self.resolve_initial_states_call_count += 1
        return self.delegate.resolve_report_initial_states(session=session, rounds=rounds)

    def build_report_scenario_title_map(self, scenario_payload_sequence):
        self.build_title_map_call_count += 1
        return self.delegate.build_report_scenario_title_map(scenario_payload_sequence)

    def build_report_history(self, *, rounds, eval_map, kt_observation_map):
        self.build_history_call_count += 1
        return self.delegate.build_report_history(
            rounds=rounds,
            eval_map=eval_map,
            kt_observation_map=kt_observation_map,
        )

    def build_report_round_snapshots(self, *, rounds, eval_map, kt_observation_map, scenario_title_map):
        self.build_round_snapshots_call_count += 1
        return self.delegate.build_report_round_snapshots(
            rounds=rounds,
            eval_map=eval_map,
            kt_observation_map=kt_observation_map,
            scenario_title_map=scenario_title_map,
        )


class _SpyReportingPolicy:
    """报告策略桩：验证服务层确实通过可注入 policy 生成报告与诊断。"""

    def __init__(self):
        self.report_inputs = None
        self.diagnostics_inputs = None

    def build_report_artifacts(
        self,
        initial_k_state,
        initial_s_state,
        final_k_state,
        final_s_state,
        round_snapshots,
    ):
        self.report_inputs = {
            "initial_k_state": dict(initial_k_state),
            "initial_s_state": dict(initial_s_state),
            "final_k_state": dict(final_k_state),
            "final_s_state": dict(final_s_state),
            "round_snapshots": [dict(item) for item in round_snapshots],
        }
        return SimpleNamespace(
            summary={
                "weighted_score_initial": 0.1,
                "weighted_score_final": 0.2,
                "weighted_score_delta": 0.1,
                "strongest_improved_skill_code": "K1",
                "strongest_improved_skill_delta": 0.1,
                "weakest_skill_code": "K2",
                "weakest_skill_score": 0.3,
                "dominant_risk_flag": None,
                "high_risk_round_count": 0,
                "high_risk_round_nos": [],
                "risk_flag_counts": [],
                "completed_scenario_ids": [
                    item["scenario_id"]
                    for item in round_snapshots
                    if str(item.get("scenario_id") or "").strip()
                ],
                "review_suggestions": ["spy_report"],
            },
            ability_radar=[
                {
                    "code": "K1",
                    "initial": 0.1,
                    "final": 0.2,
                    "delta": 0.1,
                    "weight": 0.2,
                    "is_lowest_final": False,
                    "is_highest_gain": True,
                }
            ],
            state_radar=[
                {
                    "code": "credibility",
                    "initial": 0.6,
                    "final": 0.7,
                    "delta": 0.1,
                    "weight": None,
                    "is_lowest_final": False,
                    "is_highest_gain": True,
                }
            ],
            growth_curve=[
                {
                    "round_no": 0,
                    "scenario_title": "初始状态",
                    "k_state": dict(initial_k_state),
                    "s_state": dict(initial_s_state),
                    "weighted_k_score": 0.1,
                    "risk_flags": [],
                }
            ],
        )

    def build_diagnostics_summary(self, recommendation_logs, audit_events, kt_observations):
        self.diagnostics_inputs = {
            "recommendation_logs": list(recommendation_logs),
            "audit_events": list(audit_events),
            "kt_observations": list(kt_observations),
        }
        return {
            "total_recommendation_logs": len(recommendation_logs),
            "total_audit_events": len(audit_events),
            "total_kt_observations": len(kt_observations),
            "high_risk_round_count": 0,
            "high_risk_round_nos": [],
            "recommended_vs_selected_mismatch_count": 0,
            "recommended_vs_selected_mismatch_rounds": [],
            "risk_flag_counts": [],
            "primary_skill_focus_counts": [],
            "top_weak_skills": [],
            "selection_source_counts": [],
            "event_type_counts": [],
            "last_primary_skill_code": None,
            "last_primary_risk_flag": None,
            "last_event_type": "spy_event",
        }


class _FakeDbManager:
    """内存版 DBManager 桩，隔离服务层流程测试。"""

    def __init__(self):
        self.sessions = {}
        self.rounds = {}
        self.round_evaluations = {}
        self.endings = {}
        self.recommendation_logs = {}
        self.audit_events = []
        self.kt_observations = {}

    def create_training_session_artifacts(
        self,
        user_id,
        character_id=None,
        training_mode="guided",
        k_state=None,
        s_state=None,
        session_meta=None,
        audit_event_payload=None,
    ):
        """模拟原子初始化入口。"""
        row = self.create_training_session(
            user_id=user_id,
            character_id=character_id,
            training_mode=training_mode,
            k_state=k_state,
            s_state=s_state,
            session_meta=session_meta,
        )
        self.create_kt_snapshot(row.session_id, 0, k_state or {})
        self.create_narrative_snapshot(row.session_id, 0, s_state or {})
        if audit_event_payload:
            self.create_training_audit_event(
                session_id=row.session_id,
                event_type=audit_event_payload.get("event_type", "session_initialized"),
                round_no=audit_event_payload.get("round_no"),
                payload=audit_event_payload.get("payload"),
            )
        return row

    def create_training_session(
        self,
        user_id,
        character_id=None,
        training_mode="guided",
        k_state=None,
        s_state=None,
        session_meta=None,
    ):
        session_id = f"s-{len(self.sessions) + 1}"
        row = SimpleNamespace(
            session_id=session_id,
            user_id=user_id,
            character_id=character_id,
            training_mode=training_mode,
            status="in_progress",
            current_round_no=0,
            current_scenario_id=None,
            k_state=dict(k_state or {}),
            s_state=dict(s_state or {}),
            session_meta=dict(session_meta or {}),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            end_time=None,
        )
        self.sessions[session_id] = row
        return row

    def create_kt_snapshot(self, session_id, round_no, k_state):
        return SimpleNamespace(session_id=session_id, round_no=round_no, payload=dict(k_state))

    def create_narrative_snapshot(self, session_id, round_no, s_state):
        return SimpleNamespace(session_id=session_id, round_no=round_no, payload=dict(s_state))

    def get_training_session(self, session_id):
        return self.sessions.get(session_id)

    def save_training_round_artifacts(
        self,
        session_id,
        round_no,
        scenario_id,
        user_input_raw,
        selected_option,
        user_action,
        state_before,
        state_after,
        kt_before,
        kt_after,
        feedback_text,
        evaluation_payload,
        ending_payload,
        status,
        end_time,
        session_meta=None,
        recommendation_log_payload=None,
        audit_event_payloads=None,
        kt_observation_payload=None,
    ):
        # 与生产路径保持一致：一次调用写入回合/评估/快照/会话更新。
        round_row = self.create_training_round(
            session_id=session_id,
            round_no=round_no,
            scenario_id=scenario_id,
            user_input_raw=user_input_raw,
            selected_option=selected_option,
            user_action=user_action,
            state_before=state_before,
            state_after=state_after,
            kt_before=kt_before,
            kt_after=kt_after,
            feedback_text=feedback_text,
        )
        self.create_round_evaluation(round_row.round_id, evaluation_payload, llm_model=evaluation_payload.get("llm_model"))
        self.create_kt_snapshot(session_id, round_no, kt_after)
        self.create_narrative_snapshot(session_id, round_no, state_after)
        if ending_payload is not None:
            self.upsert_ending_result(session_id, ending_payload)
        if recommendation_log_payload is not None:
            self.upsert_scenario_recommendation_log(session_id, round_no, recommendation_log_payload)
        for event_payload in audit_event_payloads or []:
            self.create_training_audit_event(
                session_id=session_id,
                event_type=event_payload.get("event_type", "unknown_event"),
                round_no=event_payload.get("round_no"),
                payload=event_payload.get("payload"),
            )
        if kt_observation_payload is not None:
            self.create_kt_observation(session_id, round_no, kt_observation_payload)
        self.update_training_session(
            session_id,
            {
                "current_round_no": round_no,
                "current_scenario_id": scenario_id,
                "k_state": kt_after,
                "s_state": state_after,
                "session_meta": dict(session_meta or self.sessions[session_id].session_meta or {}),
                "status": status,
                "end_time": end_time,
                "updated_at": datetime.utcnow(),
            },
        )
        return round_row

    def update_training_session(self, session_id, updates):
        row = self.sessions.get(session_id)
        if row is None:
            return None
        for key, value in updates.items():
            setattr(row, key, value)
        return row

    def create_training_round(
        self,
        session_id,
        round_no,
        scenario_id,
        user_input_raw,
        selected_option=None,
        user_action=None,
        state_before=None,
        state_after=None,
        kt_before=None,
        kt_after=None,
        feedback_text=None,
        node_code=None,
    ):
        round_id = f"r-{len(self.rounds) + 1}"
        row = SimpleNamespace(
            round_id=round_id,
            session_id=session_id,
            round_no=round_no,
            scenario_id=scenario_id,
            user_input_raw=user_input_raw,
            selected_option=selected_option,
            user_action=user_action or {},
            state_before=state_before or {},
            state_after=state_after or {},
            kt_before=kt_before or {},
            kt_after=kt_after or {},
            feedback_text=feedback_text,
            created_at=datetime.utcnow(),
        )
        self.rounds[round_id] = row
        return row

    def create_round_evaluation(self, round_id, payload, llm_model=None):
        row = SimpleNamespace(
            round_id=round_id,
            llm_model=llm_model or payload.get("llm_model", DEFAULT_EVAL_MODEL),
            raw_payload=payload,
            risk_flags=payload.get("risk_flags", []),
        )
        self.round_evaluations[round_id] = row
        return row

    def get_round_evaluations_by_session(self, session_id):
        rows = []
        for round_row in self.get_training_rounds(session_id):
            evaluation = self.round_evaluations.get(round_row.round_id)
            if evaluation:
                rows.append(evaluation)
        return rows

    def get_training_rounds(self, session_id):
        rows = [row for row in self.rounds.values() if row.session_id == session_id]
        rows.sort(key=lambda item: item.round_no)
        return rows

    def get_training_round_by_session_round(self, session_id, round_no):
        for row in self.rounds.values():
            if row.session_id == session_id and row.round_no == round_no:
                return row
        return None

    def get_round_evaluation_by_round_id(self, round_id):
        return self.round_evaluations.get(round_id)

    def upsert_ending_result(self, session_id, ending):
        row = SimpleNamespace(session_id=session_id, report_payload=ending, risk_flags=[])
        self.endings[session_id] = row
        return row

    def get_ending_result(self, session_id):
        return self.endings.get(session_id)

    def upsert_scenario_recommendation_log(self, session_id, round_no, payload):
        row = SimpleNamespace(
            recommendation_log_id=f"rec-{session_id}-{round_no}",
            session_id=session_id,
            round_no=round_no,
            training_mode=payload.get("training_mode", "guided"),
            selection_source=payload.get("selection_source"),
            recommended_scenario_id=payload.get("recommended_scenario_id"),
            selected_scenario_id=payload.get("selected_scenario_id"),
            candidate_pool=payload.get("candidate_pool", []),
            recommended_recommendation=payload.get("recommended_recommendation", {}),
            selected_recommendation=payload.get("selected_recommendation", {}),
            decision_context=payload.get("decision_context", {}),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.recommendation_logs[(session_id, round_no)] = row
        return row

    def get_scenario_recommendation_logs(self, session_id):
        rows = [row for (stored_session_id, _), row in self.recommendation_logs.items() if stored_session_id == session_id]
        rows.sort(key=lambda item: item.round_no)
        return rows

    def create_training_audit_event(self, session_id, event_type, round_no=None, payload=None):
        row = SimpleNamespace(
            event_id=f"audit-{len(self.audit_events) + 1}",
            session_id=session_id,
            event_type=event_type,
            round_no=round_no,
            payload=payload or {},
            created_at=datetime.utcnow(),
        )
        self.audit_events.append(row)
        return row

    def get_training_audit_events(self, session_id):
        return [row for row in self.audit_events if row.session_id == session_id]

    def create_kt_observation(self, session_id, round_no, payload):
        row = SimpleNamespace(
            observation_id=f"obs-{session_id}-{round_no}",
            session_id=session_id,
            round_no=round_no,
            scenario_id=payload.get("scenario_id"),
            scenario_title=payload.get("scenario_title", ""),
            training_mode=payload.get("training_mode", "guided"),
            primary_skill_code=payload.get("primary_skill_code"),
            primary_risk_flag=payload.get("primary_risk_flag"),
            is_high_risk=payload.get("is_high_risk", False),
            target_skills=payload.get("target_skills", []),
            weak_skills_before=payload.get("weak_skills_before", []),
            risk_flags=payload.get("risk_flags", []),
            focus_tags=payload.get("focus_tags", []),
            evidence=payload.get("evidence", []),
            skill_observations=payload.get("skill_observations", []),
            state_observations=payload.get("state_observations", []),
            observation_summary=payload.get("observation_summary", ""),
            raw_payload=payload,
            created_at=datetime.utcnow(),
        )
        self.kt_observations[(session_id, round_no)] = row
        return row

    def get_kt_observations(self, session_id):
        rows = [row for (stored_session_id, _), row in self.kt_observations.items() if stored_session_id == session_id]
        rows.sort(key=lambda item: item.round_no)
        return rows


class _DuplicateRoundDbManager(_FakeDbManager):
    """模拟 DB 层已翻译的重复提交领域异常。"""

    def save_training_round_artifacts(self, **kwargs):
        raise DuplicateRoundSubmissionError(kwargs["session_id"], kwargs["round_no"])


class _IdempotentDuplicateDbManager(_FakeDbManager):
    """模拟并发重试：第一次成功，第二次抛重复并走幂等回包。"""

    def save_training_round_artifacts(self, **kwargs):
        existing = self.get_training_round_by_session_round(kwargs["session_id"], kwargs["round_no"])
        if existing is not None:
            raise DuplicateRoundSubmissionError(kwargs["session_id"], kwargs["round_no"])

        row = super().save_training_round_artifacts(**kwargs)
        # 模拟并发场景：重试请求仍认为是同一 round_no。
        self.sessions[kwargs["session_id"]].current_round_no = 0
        return row


class TrainingServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.db = _FakeDbManager()
        self.evaluator = _FakeEvaluator()
        self.service = TrainingService(db_manager=self.db, evaluator=self.evaluator)

    def test_init_training_should_return_full_next_scenario_payload(self):
        """初始化训练时，应直接返回完整场景快照，而不是只有 ID 与标题。"""
        result = self.service.init_training(user_id="u0")

        self.assertIn("mission", result["next_scenario"])
        self.assertIn("options", result["next_scenario"])
        self.assertTrue(len(result["next_scenario"]["target_skills"]) >= 1)

    def test_init_training_should_canonicalize_training_mode_alias(self):
        """训练模式别名入库时应统一成 canonical 值。"""
        result = self.service.init_training(user_id="u0-alias", training_mode="self_paced")
        session_id = result["session_id"]

        self.assertEqual(self.db.sessions[session_id].training_mode, "self-paced")

    def test_init_training_should_apply_forced_round_rule_from_runtime_config(self):
        """运行时配置命中关键节点规则时，初始化返回的下一题应优先使用固定场景。"""
        runtime_config = model_copy(load_training_runtime_config())
        runtime_config.flow.forced_rounds = [
            FlowForcedRoundConfig(
                round_no=1,
                scenario_id="S1",
                modes=["self-paced"],
                reason="固定开场节点",
            )
        ]
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            runtime_config=runtime_config,
        )

        result = service.init_training(user_id="u0-forced", training_mode="self-paced")

        self.assertEqual(result["next_scenario"]["id"], "S1")

    def test_init_training_should_reject_unknown_training_mode(self):
        """未知训练模式应尽早报错，避免脏数据写入会话表。"""
        with self.assertRaises(TrainingModeUnsupportedError) as cm:
            self.service.init_training(user_id="u0-invalid", training_mode="sandbox")

        self.assertIn("unsupported training mode", str(cm.exception))
        self.assertEqual(cm.exception.raw_mode, "sandbox")
        self.assertEqual(cm.exception.supported_modes, ["guided", "self-paced", "adaptive"])

    def test_init_training_should_use_runtime_config_default_sequence(self):
        """注入自定义运行时配置时，服务应优先使用配置里的默认场景序列。"""
        custom_config = model_copy(self.service.runtime_config)
        custom_config.scenario.default_sequence = [ScenarioItemConfig(id="S_CUSTOM", title="自定义场景")]

        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            runtime_config=custom_config,
        )
        result = service.init_training(user_id="u0-custom")

        self.assertEqual(result["next_scenario"]["id"], "S_CUSTOM")
        self.assertEqual(service.scenario_policy.get_default_sequence()[0]["id"], "S_CUSTOM")

    def test_init_training_should_write_session_initialized_audit_event(self):
        """初始化训练应写入首条审计事件，便于后续排查会话来源。"""
        result = self.service.init_training(user_id="u0-audit", training_mode="adaptive")
        session_id = result["session_id"]

        audit_events = self.db.get_training_audit_events(session_id)
        self.assertEqual(audit_events[0].event_type, "session_initialized")
        self.assertEqual(audit_events[0].payload["training_mode"], "adaptive")
        self.assertEqual(audit_events[0].payload["phase"]["phase_tags"], ["opening"])

    def test_init_training_should_store_player_profile_in_session_meta_and_outputs(self):
        """初始化训练时应冻结玩家档案，并在初始化响应中直接回显。"""
        player_profile = {
            "name": "李敏",
            "gender": "女",
            "identity": "战地记者",
            "age": 24,
        }

        result = self.service.init_training(user_id="u0-profile", player_profile=player_profile)
        session_id = result["session_id"]

        self.assertEqual(result["player_profile"]["name"], "李敏")
        self.assertEqual(result["player_profile"]["identity"], "战地记者")
        self.assertEqual(self.db.sessions[session_id].session_meta["player_profile"]["age"], 24)

    def test_followup_queries_should_echo_player_profile(self):
        """后续查询链路应持续回显同一份玩家档案，便于前后端做稳定展示。"""
        init_result = self.service.init_training(
            user_id="u0-followup-profile",
            training_mode="self-paced",
            player_profile={
                "name": "李敏",
                "gender": "女",
                "identity": "战地记者",
            },
        )
        session_id = init_result["session_id"]

        next_result = self.service.get_next_scenario(session_id)
        submit_result = self.service.submit_round(
            session_id=session_id,
            scenario_id=next_result["scenario_candidates"][0]["id"],
            user_input="我先核验来源，再决定是否发稿",
        )
        progress_result = self.service.get_progress(session_id)
        report_result = self.service.get_report(session_id)
        diagnostics_result = self.service.get_diagnostics(session_id)

        self.assertEqual(next_result["player_profile"]["name"], "李敏")
        self.assertEqual(submit_result["player_profile"]["identity"], "战地记者")
        self.assertEqual(progress_result["player_profile"]["gender"], "女")
        self.assertEqual(report_result["player_profile"]["name"], "李敏")
        self.assertEqual(diagnostics_result["player_profile"]["identity"], "战地记者")

    def test_submit_round_scenario_mismatch_should_fail(self):
        init_result = self.service.init_training(user_id="u1")
        session_id = init_result["session_id"]

        with self.assertRaises(TrainingScenarioMismatchError) as cm:
            self.service.submit_round(
                session_id=session_id,
                scenario_id="S999",
                user_input="test input",
            )
        self.assertEqual(cm.exception.expected_scenario_id, "S1")
        self.assertEqual(cm.exception.round_no, 1)

    def test_submit_round_scenario_mismatch_can_be_disabled(self):
        # 显式注入关闭顺序校验的策略，替代旧的全局常量 monkeypatch。
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_policy=ScenarioPolicy(default_sequence=TrainingService._SCENARIO_SEQUENCE, enforce_order=False),
        )
        init_result = service.init_training(user_id="u2")
        session_id = init_result["session_id"]

        result = service.submit_round(
            session_id=session_id,
            scenario_id="S999",
            user_input="test input",
        )
        self.assertEqual(result["round_no"], 1)
        self.assertEqual(result["evaluation"]["eval_mode"], "rules_only")

    def test_report_contains_round_history(self):
        init_result = self.service.init_training(user_id="u3")
        session_id = init_result["session_id"]

        self.service.submit_round(session_id=session_id, scenario_id="S1", user_input="hello")
        report = self.service.get_report(session_id=session_id)

        self.assertEqual(report["session_id"], session_id)
        self.assertEqual(report["rounds"], 1)
        self.assertEqual(len(report["history"]), 1)
        self.assertIn("improvement", report)
        self.assertEqual(set(report["k_state_final"].keys()), set(DEFAULT_K_STATE.keys()))
        self.assertEqual(set(report["s_state_final"].keys()), set(DEFAULT_S_STATE.keys()))
        self.assertEqual(report["history"][0]["decision_context"]["selection_source"], "ordered_sequence")
        self.assertEqual(report["history"][0]["kt_observation"]["scenario_id"], "S1")
        self.assertEqual(report["growth_curve"][0]["round_no"], 0)
        self.assertEqual(report["growth_curve"][1]["scenario_id"], "S1")
        self.assertEqual(report["ability_radar"][0]["code"], "K1")
        self.assertEqual(report["state_radar"][0]["code"], "credibility")
        self.assertIsNotNone(report["summary"]["strongest_improved_skill_code"])
        self.assertEqual(report["summary"]["completed_scenario_ids"], ["S1"])
        self.assertTrue(len(report["summary"]["review_suggestions"]) >= 1)

    def test_service_should_delegate_report_and_diagnostics_to_injected_reporting_policy(self):
        """注入自定义 reporting policy 后，服务层应通过 policy 生成报告与诊断。"""
        spy_policy = _SpyReportingPolicy()
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            reporting_policy=spy_policy,
        )
        init_result = service.init_training(user_id="u3-spy")
        session_id = init_result["session_id"]

        service.submit_round(session_id=session_id, scenario_id="S1", user_input="hello")
        report = service.get_report(session_id=session_id)
        diagnostics = service.get_diagnostics(session_id=session_id)

        self.assertIsNotNone(spy_policy.report_inputs)
        self.assertIsNotNone(spy_policy.diagnostics_inputs)
        self.assertEqual(spy_policy.report_inputs["round_snapshots"][0]["scenario_id"], "S1")
        self.assertEqual(report["summary"]["review_suggestions"], ["spy_report"])
        self.assertEqual(report["ability_radar"][0]["code"], "K1")
        self.assertEqual(diagnostics["summary"]["last_event_type"], "spy_event")

    def test_service_should_delegate_report_context_to_injected_policy(self):
        """获取报告时，history 和 round_snapshots 的装配应委托给独立策略。"""
        spy_policy = _SpyReportContextPolicy(TrainingReportContextPolicy())
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            report_context_policy=spy_policy,
        )
        init_result = service.init_training(user_id="u3-report-context-spy")
        session_id = init_result["session_id"]

        service.submit_round(session_id=session_id, scenario_id="S1", user_input="hello")
        report = service.get_report(session_id=session_id)

        self.assertEqual(spy_policy.resolve_initial_states_call_count, 1)
        self.assertEqual(spy_policy.build_title_map_call_count, 1)
        self.assertEqual(spy_policy.build_history_call_count, 1)
        self.assertEqual(spy_policy.build_round_snapshots_call_count, 1)
        self.assertEqual(report["history"][0]["scenario_id"], "S1")
        self.assertEqual(report["growth_curve"][1]["scenario_id"], "S1")

    def test_service_should_delegate_session_snapshot_lifecycle_to_injected_policy(self):
        """注入自定义快照策略后，服务层应通过策略完成冻结、快照校验与场景解析。"""
        repository = ScenarioRepository()
        scenario_policy = ScenarioPolicy(default_sequence=TrainingService._SCENARIO_SEQUENCE)
        spy_snapshot_policy = _SpySessionSnapshotPolicy(
            SessionScenarioSnapshotPolicy(
                scenario_policy=scenario_policy,
                scenario_repository=repository,
            )
        )
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_policy=scenario_policy,
            scenario_repository=repository,
            session_snapshot_policy=spy_snapshot_policy,
        )

        init_result = service.init_training(user_id="u3-snapshot-spy")
        session_id = init_result["session_id"]
        service.get_next_scenario(session_id)
        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )

        self.assertGreaterEqual(spy_snapshot_policy.freeze_call_count, 1)
        self.assertGreaterEqual(spy_snapshot_policy.require_call_count, 2)
        self.assertGreaterEqual(spy_snapshot_policy.resolve_call_count, 1)

    def test_service_should_delegate_round_decision_context_to_injected_policy(self):
        """提交回合时，决策上下文应完全由注入策略生成，而不是服务层自行拼装。"""
        spy_policy = _SpyDecisionContextPolicy()
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            decision_context_policy=spy_policy,
        )
        init_result = service.init_training(user_id="u3-decision-spy")
        session_id = init_result["session_id"]

        result = service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )

        self.assertEqual(len(spy_policy.calls), 1)
        self.assertEqual(spy_policy.calls[0]["training_mode"], "guided")
        self.assertEqual(spy_policy.calls[0]["submitted_scenario_id"], "S1")
        self.assertEqual(result["decision_context"]["selection_source"], "spy_policy")
        recommendation_logs = service.db_manager.get_scenario_recommendation_logs(session_id)
        self.assertEqual(recommendation_logs[0].selection_source, "spy_policy")

    def test_service_should_delegate_runtime_artifacts_to_injected_policy(self):
        """运行时状态、user_action 工件和回放恢复应通过注入策略统一处理。"""
        spy_policy = _SpyRuntimeArtifactPolicy(TrainingRuntimeArtifactPolicy())
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=_RiskFlagEvaluator(),
            runtime_artifact_policy=spy_policy,
        )
        init_result = service.init_training(user_id="u3-runtime-spy")
        session_id = init_result["session_id"]

        submit_result = service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )
        diagnostics = service.get_diagnostics(session_id)
        report = service.get_report(session_id)

        self.assertGreaterEqual(spy_policy.build_default_flags_call_count, 1)
        self.assertGreaterEqual(spy_policy.merge_flags_call_count, 2)
        self.assertGreaterEqual(spy_policy.resolve_flags_call_count, 2)
        self.assertGreaterEqual(spy_policy.build_runtime_state_call_count, 4)
        self.assertGreaterEqual(spy_policy.build_round_user_action_call_count, 1)
        self.assertGreaterEqual(spy_policy.attach_runtime_artifacts_call_count, 1)
        self.assertGreaterEqual(spy_policy.extract_runtime_state_call_count, 1)
        self.assertGreaterEqual(spy_policy.extract_runtime_flags_call_count, 1)
        self.assertGreaterEqual(spy_policy.extract_consequence_events_call_count, 1)
        self.assertGreaterEqual(spy_policy.extract_decision_context_call_count, 1)
        self.assertTrue(submit_result["runtime_state"]["runtime_flags"]["source_exposed"])
        self.assertEqual(diagnostics["runtime_state"]["runtime_flags"]["source_exposed"], True)
        self.assertEqual(report["history"][0]["consequence_events"][0]["event_type"], "source_exposed")

    def test_service_should_delegate_output_assembly_to_injected_policy(self):
        """对外 DTO 转换应统一委托给注入的输出装配策略。"""
        spy_policy = _SpyOutputAssemblerPolicy(TrainingOutputAssemblerPolicy())
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=_RiskFlagEvaluator(),
            output_assembler_policy=spy_policy,
        )
        init_result = service.init_training(user_id="u3-output-spy")
        session_id = init_result["session_id"]

        service.get_next_scenario(session_id)
        submit_result = service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )
        diagnostics = service.get_diagnostics(session_id)
        report = service.get_report(session_id)

        self.assertGreaterEqual(spy_policy.build_scenario_output_call_count, 2)
        self.assertGreaterEqual(spy_policy.build_scenario_output_list_call_count, 2)
        self.assertGreaterEqual(spy_policy.build_player_profile_output_call_count, 1)
        self.assertGreaterEqual(spy_policy.build_evaluation_output_call_count, 1)
        self.assertGreaterEqual(spy_policy.build_runtime_state_output_call_count, 1)
        self.assertGreaterEqual(spy_policy.build_consequence_event_outputs_call_count, 1)
        self.assertGreaterEqual(spy_policy.build_recommendation_log_outputs_call_count, 1)
        self.assertGreaterEqual(spy_policy.build_audit_event_outputs_call_count, 1)
        self.assertGreaterEqual(spy_policy.build_kt_observation_outputs_call_count, 1)
        self.assertGreaterEqual(spy_policy.build_kt_observation_output_call_count, 1)
        self.assertEqual(submit_result["evaluation"]["risk_flags"], ["source_exposure_risk"])
        self.assertEqual(diagnostics["kt_observations"][0]["scenario_id"], "S1")
        self.assertEqual(report["history"][0]["evaluation"]["risk_flags"], ["source_exposure_risk"])

    def test_service_should_delegate_round_transition_to_injected_policy(self):
        """提交回合时，状态推进链路应委托给独立回合推进策略。"""
        spy_policy = _SpyRoundTransitionPolicy(
            TrainingRoundTransitionPolicy(
                runtime_artifact_policy=TrainingRuntimeArtifactPolicy(),
            )
        )
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=_RiskFlagEvaluator(),
            round_transition_policy=spy_policy,
        )
        init_result = service.init_training(user_id="u3-transition-spy")
        session_id = init_result["session_id"]

        result = service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
            selected_option="A",
        )

        self.assertEqual(len(spy_policy.calls), 1)
        self.assertEqual(spy_policy.calls[0]["round_no"], 1)
        self.assertEqual(spy_policy.calls[0]["scenario_id"], "S1")
        self.assertEqual(spy_policy.calls[0]["selected_option"], "A")
        self.assertTrue(result["runtime_state"]["runtime_flags"]["source_exposed"])
        self.assertEqual(result["consequence_events"][0]["event_type"], "source_exposed")

    def test_service_should_reuse_round_transition_runtime_contract_for_report_and_duplicate_replay(self):
        custom_runtime_artifact_policy = _CustomContractRuntimeArtifactPolicy()
        service = TrainingService(
            db_manager=_IdempotentDuplicateDbManager(),
            evaluator=_RiskFlagEvaluator(),
            round_transition_policy=TrainingRoundTransitionPolicy(
                runtime_artifact_policy=custom_runtime_artifact_policy,
            ),
        )
        init_result = service.init_training(user_id="u3-transition-contract")
        session_id = init_result["session_id"]

        first = service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )
        second = service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )
        report = service.get_report(session_id)

        self.assertIs(service.runtime_artifact_policy, custom_runtime_artifact_policy)
        self.assertIs(service.round_transition_policy.runtime_artifact_policy, custom_runtime_artifact_policy)
        self.assertIs(service.report_context_policy.runtime_artifact_policy, custom_runtime_artifact_policy)
        self.assertEqual(first["decision_context"]["selected_scenario_id"], "S1")
        self.assertEqual(second["decision_context"]["selected_scenario_id"], "S1")
        self.assertEqual(report["history"][0]["decision_context"]["selected_scenario_id"], "S1")
        self.assertEqual(second["runtime_state"], first["runtime_state"])
        self.assertEqual(report["history"][0]["runtime_state"], first["runtime_state"])
        self.assertEqual(report["history"][0]["consequence_events"], first["consequence_events"])

    def test_service_should_reject_conflicting_runtime_artifact_policy_injections(self):
        with self.assertRaises(ValueError) as cm:
            TrainingService(
                db_manager=_FakeDbManager(),
                evaluator=self.evaluator,
                round_transition_policy=TrainingRoundTransitionPolicy(
                    runtime_artifact_policy=_CustomContractRuntimeArtifactPolicy(),
                ),
                report_context_policy=TrainingReportContextPolicy(
                    runtime_artifact_policy=TrainingRuntimeArtifactPolicy(),
                    output_assembler_policy=TrainingOutputAssemblerPolicy(),
                ),
            )

        self.assertIn("inconsistent runtime_artifact_policy injection", str(cm.exception))

    def test_service_should_reject_conflicting_output_assembler_policy_injections(self):
        with self.assertRaises(ValueError) as cm:
            TrainingService(
                db_manager=_FakeDbManager(),
                evaluator=self.evaluator,
                output_assembler_policy=TrainingOutputAssemblerPolicy(),
                report_context_policy=TrainingReportContextPolicy(
                    runtime_artifact_policy=TrainingRuntimeArtifactPolicy(),
                    output_assembler_policy=TrainingOutputAssemblerPolicy(),
                ),
            )

        self.assertIn("inconsistent output_assembler_policy injection", str(cm.exception))

    def test_report_round_snapshots_should_fallback_to_evaluation_risk_flags_when_observation_missing(self):
        """历史数据缺少 KT 观测时，报告快照仍应从评估结果兜底补齐风险字段。"""
        spy_policy = _SpyReportingPolicy()
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=_RiskFlagEvaluator(),
            reporting_policy=spy_policy,
        )
        init_result = service.init_training(user_id="u3-fallback-risk")
        session_id = init_result["session_id"]

        service.submit_round(session_id=session_id, scenario_id="S1", user_input="hello")
        del service.db_manager.kt_observations[(session_id, 1)]

        service.get_report(session_id=session_id)

        snapshot = spy_policy.report_inputs["round_snapshots"][0]
        self.assertEqual(snapshot["scenario_id"], "S1")
        self.assertTrue(snapshot["is_high_risk"])
        self.assertEqual(snapshot["risk_flags"], ["source_exposure_risk"])

    def test_report_without_rounds_should_still_expose_initial_growth_curve(self):
        """即使还没开始作答，报告也应返回 round=0 起点，便于前端直接画初始曲线。"""
        init_result = self.service.init_training(user_id="u3-empty")
        session_id = init_result["session_id"]

        report = self.service.get_report(session_id=session_id)

        self.assertEqual(report["history"], [])
        self.assertEqual(len(report["growth_curve"]), 1)
        self.assertEqual(report["growth_curve"][0]["round_no"], 0)
        self.assertEqual(report["growth_curve"][0]["scenario_title"], "初始状态")
        self.assertEqual(report["summary"]["completed_scenario_ids"], [])

    def test_duplicate_round_submission_should_raise_typed_domain_error(self):
        duplicate_service = TrainingService(db_manager=_DuplicateRoundDbManager(), evaluator=self.evaluator)
        init_result = duplicate_service.init_training(user_id="u4")
        session_id = init_result["session_id"]

        with self.assertRaises(DuplicateRoundSubmissionError) as cm:
            duplicate_service.submit_round(
                session_id=session_id,
                scenario_id="S1",
                user_input="hello",
            )
        self.assertIn("duplicate round submission", str(cm.exception))

    def test_session_should_use_frozen_scenario_sequence(self):
        repository = ScenarioRepository()
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_sequence=[{"id": "S_A", "title": "A"}],
            scenario_repository=repository,
        )
        init_result = service.init_training(user_id="u5")
        session_id = init_result["session_id"]

        # 模拟发版后代码默认序列变化，但会话应继续使用初始化时冻结的序列。
        service._scenario_sequence = [{"id": "S_B", "title": "B"}]
        service.scenario_repository = ScenarioRepository()

        result = service.submit_round(
            session_id=session_id,
            scenario_id="S_A",
            user_input="hello",
        )
        self.assertEqual(result["round_no"], 1)
        self.assertEqual(result["is_completed"], True)

    def test_get_next_scenario_should_prefer_frozen_scenario_payload(self):
        """获取下一场景时，应优先读取会话冻结快照，而不是重新查最新场景库。"""
        init_result = self.service.init_training(user_id="u10")
        session_id = init_result["session_id"]

        # 模拟运行时替换场景仓储，但老会话仍应使用冻结快照。
        self.service.scenario_repository = _ChangedScenarioRepository()
        result = self.service.get_next_scenario(session_id)

        self.assertEqual(result["scenario"]["id"], init_result["next_scenario"]["id"])
        self.assertEqual(result["scenario"]["brief"], init_result["next_scenario"]["brief"])
        self.assertNotIn("briefing", result["scenario"])
        self.assertNotEqual(result["scenario"]["brief"], "这是变更后的最新场景正文")

    def test_get_next_scenario_should_raise_typed_error_when_snapshot_catalog_is_missing(self):
        """主链路遇到缺快照会话时，应返回 typed recovery error，而不是静默回填。"""
        init_result = self.service.init_training(user_id="u10-backfill-catalog")
        session_id = init_result["session_id"]
        session_row = self.service.db_manager.sessions[session_id]
        session_row.session_meta.pop("scenario_payload_catalog", None)

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            self.service.get_next_scenario(session_id)

        self.assertEqual(cm.exception.reason, "scenario_snapshots_missing")
        self.assertEqual(cm.exception.details["missing_fields"], ["scenario_payload_catalog"])
        self.assertNotIn("scenario_payload_catalog", session_row.session_meta)

    def test_get_next_scenario_should_raise_typed_error_when_payload_sequence_and_catalog_are_missing(self):
        """更老的历史会话缺少快照事实时，不应在运行时偷偷补写。"""
        init_result = self.service.init_training(user_id="u10-backfill-all")
        session_id = init_result["session_id"]
        session_row = self.service.db_manager.sessions[session_id]
        session_row.session_meta.pop("scenario_payload_sequence", None)
        session_row.session_meta.pop("scenario_payload_catalog", None)

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            self.service.get_next_scenario(session_id)

        self.assertEqual(cm.exception.reason, "scenario_snapshots_missing")
        self.assertEqual(
            cm.exception.details["missing_fields"],
            ["scenario_payload_sequence", "scenario_payload_catalog"],
        )
        self.assertNotIn("scenario_payload_sequence", session_row.session_meta)
        self.assertNotIn("scenario_payload_catalog", session_row.session_meta)

    def test_get_next_scenario_should_return_normalized_state_shape(self):
        """读取下一场景时，应补齐老会话可能缺失的状态字段。"""
        init_result = self.service.init_training(user_id="u10-shape")
        session_id = init_result["session_id"]

        self.service.db_manager.sessions[session_id].k_state = {"K1": 0.9}
        self.service.db_manager.sessions[session_id].s_state = {"credibility": 0.7}

        result = self.service.get_next_scenario(session_id)

        self.assertEqual(set(result["k_state"].keys()), set(DEFAULT_K_STATE.keys()))
        self.assertEqual(set(result["s_state"].keys()), set(DEFAULT_S_STATE.keys()))

    def test_adaptive_mode_should_recommend_weak_skill_scenario(self):
        """自适应模式应优先推荐能够覆盖当前短板的场景。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=self.evaluator)
        init_result = service.init_training(user_id="u11", training_mode="adaptive")
        session_id = init_result["session_id"]

        # 人为制造 K5 短板，验证推荐会偏向来源保护类场景。
        service.db_manager.sessions[session_id].k_state = {
            "K1": 0.9,
            "K2": 0.9,
            "K3": 0.9,
            "K4": 0.9,
            "K5": 0.1,
            "K6": 0.9,
            "K7": 0.9,
            "K8": 0.9,
        }

        result = service.get_next_scenario(session_id)
        self.assertEqual(result["scenario"]["id"], "S3")
        self.assertEqual(result["scenario"]["recommendation"]["mode"], "adaptive")
        self.assertNotIn("scenario_candidates", result)

    def test_adaptive_mode_should_validate_recommended_scenario(self):
        """自适应模式下，提交非推荐场景应被拒绝。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=self.evaluator)
        init_result = service.init_training(user_id="u12", training_mode="adaptive")
        session_id = init_result["session_id"]

        service.db_manager.sessions[session_id].k_state = {
            "K1": 0.9,
            "K2": 0.9,
            "K3": 0.9,
            "K4": 0.9,
            "K5": 0.1,
            "K6": 0.9,
            "K7": 0.9,
            "K8": 0.9,
        }

        with self.assertRaises(TrainingScenarioMismatchError) as cm:
            service.submit_round(
                session_id=session_id,
                scenario_id="S1",
                user_input="hello",
            )

        self.assertIn("expected=S3", str(cm.exception))

    def test_self_paced_mode_should_return_ranked_scenario_candidates(self):
        """自选模式应返回推荐题和候选列表，供前端自由展示与选择。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=self.evaluator)
        result = service.init_training(user_id="u13", training_mode="self-paced")

        self.assertIn("scenario_candidates", result)
        self.assertEqual(result["next_scenario"]["id"], result["scenario_candidates"][0]["id"])
        self.assertEqual(len(result["scenario_candidates"]), 3)
        self.assertEqual(result["scenario_candidates"][0]["recommendation"]["rank"], 1)

    def test_self_paced_mode_should_allow_submitting_non_first_candidate(self):
        """自选模式允许提交候选列表中的非第一推荐题。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=self.evaluator)
        init_result = service.init_training(user_id="u14", training_mode="self-paced")
        session_id = init_result["session_id"]

        # 人为制造 K5 短板，让候选列表出现稳定排序，便于验证“可选但不强制第一题”。
        service.db_manager.sessions[session_id].k_state = {
            "K1": 0.9,
            "K2": 0.9,
            "K3": 0.9,
            "K4": 0.9,
            "K5": 0.1,
            "K6": 0.9,
            "K7": 0.9,
            "K8": 0.9,
        }

        next_result = service.get_next_scenario(session_id)
        self.assertEqual([item["id"] for item in next_result["scenario_candidates"]], ["S3", "S1", "S2"])

        result = service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )

        self.assertEqual(result["round_no"], 1)
        self.assertEqual(result["decision_context"]["selection_source"], "candidate_pool")
        self.assertEqual(result["decision_context"]["recommended_scenario_id"], "S3")
        self.assertEqual(service.db_manager.get_training_rounds(session_id)[0].scenario_id, "S1")
        self.assertEqual(
            service.db_manager.get_training_rounds(session_id)[0].user_action["decision_context"]["selection_source"],
            "candidate_pool",
        )
        recommendation_logs = service.db_manager.get_scenario_recommendation_logs(session_id)
        self.assertEqual(recommendation_logs[0].selected_scenario_id, "S1")
        self.assertEqual(recommendation_logs[0].recommended_scenario_id, "S3")
        audit_events = service.db_manager.get_training_audit_events(session_id)
        self.assertTrue(any(event.event_type == "round_submitted" for event in audit_events))

    def test_self_paced_mode_should_reject_completed_candidate_resubmission(self):
        """自选模式下，已完成题目应从候选集中移除，重复提交必须被拒绝。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=self.evaluator)
        init_result = service.init_training(user_id="u15", training_mode="self-paced")
        session_id = init_result["session_id"]

        service.submit_round(
            session_id=session_id,
            scenario_id=init_result["scenario_candidates"][1]["id"],
            user_input="hello",
        )

        with self.assertRaises(TrainingScenarioMismatchError) as cm:
            service.submit_round(
                session_id=session_id,
                scenario_id=init_result["scenario_candidates"][1]["id"],
                user_input="hello again",
            )

        self.assertIn("scenario mismatch: allowed=", str(cm.exception))
        self.assertTrue(cm.exception.allowed_scenario_ids)
        self.assertEqual(cm.exception.round_no, 2)

    def test_submit_round_should_persist_structured_kt_observation(self):
        """提交回合后，应同步落一份结构化 KT 观测，便于后续分析和报表复用。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=self.evaluator)
        init_result = service.init_training(user_id="u15-observation", training_mode="self-paced")
        session_id = init_result["session_id"]

        service.db_manager.sessions[session_id].k_state = {
            "K1": 0.9,
            "K2": 0.9,
            "K3": 0.9,
            "K4": 0.9,
            "K5": 0.1,
            "K6": 0.9,
            "K7": 0.9,
            "K8": 0.9,
        }

        service.submit_round(
            session_id=session_id,
            scenario_id="S3",
            user_input="hello",
        )

        observations = service.db_manager.get_kt_observations(session_id)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].scenario_id, "S3")
        self.assertEqual(observations[0].primary_skill_code, "K5")
        self.assertIn("K5", observations[0].focus_tags)
        self.assertTrue(observations[0].observation_summary)

    def test_recent_risk_history_should_change_recommendation_order(self):
        """最近风险历史应穿透 service 和 flow policy，改写下一题推荐顺序。"""
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=_RecentSourceRiskEvaluator(),
            scenario_sequence=[
                {"id": "S1", "title": "Start"},
                {"id": "S4", "title": "Middle"},
                {"id": "S3", "title": "Remediation"},
            ],
        )
        init_result = service.init_training(user_id="u15-risk", training_mode="self-paced")
        session_id = init_result["session_id"]

        # 首轮阶段对齐会先推 S1，提交后再验证最近风险会把补救题 S3 顶上来。
        self.assertEqual(init_result["next_scenario"]["id"], "S1")
        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )

        next_result = service.get_next_scenario(session_id)
        self.assertEqual(next_result["scenario"]["id"], "S3")
        self.assertGreater(next_result["scenario"]["recommendation"]["risk_boost_score"], 0.0)

    def test_single_round_completion_should_persist_ending(self):
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_sequence=[{"id": "S1", "title": "Only"}],
        )
        init_result = service.init_training(user_id="u6")
        session_id = init_result["session_id"]

        result = service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )
        self.assertTrue(result["is_completed"])
        self.assertIsNotNone(result["ending"])
        self.assertIsNotNone(service.db_manager.get_ending_result(session_id))
        audit_events = service.db_manager.get_training_audit_events(session_id)
        self.assertTrue(any(event.event_type == "session_completed" for event in audit_events))

    def test_round_submit_should_append_phase_transition_audit_event(self):
        """跨阶段提交时，应额外落一条阶段切换审计事件。"""
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_sequence=[
                {"id": "S1", "title": "Round1"},
                {"id": "S2", "title": "Round2"},
                {"id": "S3", "title": "Round3"},
            ],
        )
        init_result = service.init_training(user_id="u16-phase")
        session_id = init_result["session_id"]

        service.submit_round(session_id=session_id, scenario_id="S1", user_input="hello-1")
        service.submit_round(session_id=session_id, scenario_id="S2", user_input="hello-2")
        service.submit_round(session_id=session_id, scenario_id="S3", user_input="hello-3")

        audit_events = service.db_manager.get_training_audit_events(session_id)
        phase_transition_events = [event for event in audit_events if event.event_type == "phase_transition"]

        self.assertEqual(len(phase_transition_events), 1)
        self.assertEqual(phase_transition_events[0].round_no, 3)
        self.assertEqual(phase_transition_events[0].payload["from_phase"]["phase_tags"], ["opening"])
        self.assertEqual(phase_transition_events[0].payload["to_phase"]["phase_tags"], ["middle"])

    def test_get_next_scenario_after_completion_should_return_stable_completed_payload(self):
        """训练已完成时，下一场景接口仍应返回稳定字段结构。"""
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_sequence=[{"id": "S1", "title": "Only"}],
        )
        init_result = service.init_training(user_id="u16")
        session_id = init_result["session_id"]

        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )
        result = service.get_next_scenario(session_id)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["round_no"], 1)
        self.assertIsNone(result["scenario"])
        self.assertEqual(result["scenario_candidates"], [])
        self.assertEqual(set(result["k_state"].keys()), set(DEFAULT_K_STATE.keys()))
        self.assertEqual(set(result["s_state"].keys()), set(DEFAULT_S_STATE.keys()))
        self.assertIsNotNone(result["ending"])

    def test_get_session_summary_should_return_recovery_anchor_and_resumable_scenario(self):
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_sequence=[
                {"id": "S1", "title": "Intro"},
                {"id": "S2", "title": "Follow Up"},
            ],
        )
        init_result = service.init_training(user_id="u17-summary", training_mode="self-paced")
        session_id = init_result["session_id"]

        summary = service.get_session_summary(session_id)

        self.assertEqual(summary["session_id"], session_id)
        self.assertEqual(summary["training_mode"], "self-paced")
        self.assertEqual(summary["current_round_no"], 0)
        self.assertEqual(summary["progress_anchor"]["next_round_no"], 1)
        self.assertEqual(summary["progress_anchor"]["remaining_rounds"], 2)
        self.assertEqual(summary["progress_anchor"]["progress_percent"], 0.0)
        self.assertEqual(summary["resumable_scenario"]["id"], init_result["next_scenario"]["id"])
        self.assertEqual(summary["scenario_candidates"][0]["id"], init_result["scenario_candidates"][0]["id"])
        self.assertTrue(summary["can_resume"])
        self.assertFalse(summary["is_completed"])
        self.assertEqual(summary["runtime_state"]["current_scene_id"], init_result["next_scenario"]["id"])

    def test_get_session_summary_should_return_completed_session_without_resumable_scenario(self):
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_sequence=[{"id": "S1", "title": "Only"}],
        )
        init_result = service.init_training(user_id="u17-summary-completed")
        session_id = init_result["session_id"]

        service.submit_round(session_id=session_id, scenario_id="S1", user_input="done")
        summary = service.get_session_summary(session_id)

        self.assertEqual(summary["status"], "completed")
        self.assertTrue(summary["is_completed"])
        self.assertFalse(summary["can_resume"])
        self.assertIsNone(summary["resumable_scenario"])
        self.assertEqual(summary["scenario_candidates"], [])
        self.assertEqual(summary["progress_anchor"]["progress_percent"], 100.0)
        self.assertNotIn("next_round_no", summary["progress_anchor"])
        self.assertIsNotNone(summary["end_time"])

    def test_get_session_summary_should_surface_branch_resumable_scenario(self):
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_PublicPanicEvaluator())
        init_result = service.init_training(user_id="u17-branch-summary")
        session_id = init_result["session_id"]

        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="trigger-branch",
        )

        summary = service.get_session_summary(session_id)

        self.assertEqual(summary["resumable_scenario"]["id"], "S2B")
        self.assertEqual(summary["runtime_state"]["current_scene_id"], "S2B")
        self.assertTrue(summary["runtime_state"]["runtime_flags"]["panic_triggered"])
        self.assertEqual(summary["progress_anchor"]["progress_percent"], 16.67)
        self.assertEqual(summary["progress_anchor"]["next_round_no"], 2)

    def test_get_session_summary_should_raise_typed_error_when_recovery_state_is_corrupted(self):
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=self.evaluator)
        init_result = service.init_training(user_id="u17-corrupted-summary")
        session_id = init_result["session_id"]

        service.scenario_policy._default_sequence = []
        service.db_manager.sessions[session_id].session_meta["scenario_sequence"] = []

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            service.get_session_summary(session_id)

        self.assertEqual(cm.exception.reason, "scenario_sequence_empty")
        self.assertEqual(cm.exception.session_id, session_id)

    def test_get_next_scenario_should_raise_typed_error_when_persisted_sequence_is_missing(self):
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=self.evaluator)
        init_result = service.init_training(user_id="u17-corrupted-next")
        session_id = init_result["session_id"]
        session_row = service.db_manager.sessions[session_id]
        session_row.session_meta["scenario_sequence"] = []

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            service.get_next_scenario(session_id)

        self.assertEqual(cm.exception.reason, "scenario_sequence_empty")
        self.assertEqual(cm.exception.session_id, session_id)

    def test_get_history_should_return_canonical_history_read_model(self):
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_sequence=[
                {"id": "S1", "title": "Intro"},
                {"id": "S2", "title": "Follow Up"},
            ],
        )
        init_result = service.init_training(user_id="u17-history", training_mode="self-paced")
        session_id = init_result["session_id"]

        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )
        history = service.get_history(session_id)

        self.assertEqual(history["session_id"], session_id)
        self.assertEqual(history["training_mode"], "self-paced")
        self.assertEqual(history["progress_anchor"]["next_round_no"], 2)
        self.assertEqual(history["progress_anchor"]["progress_percent"], 50.0)
        self.assertEqual(history["history"][0]["scenario_id"], "S1")
        self.assertEqual(history["history"][0]["round_no"], 1)
        self.assertFalse(history["is_completed"])

    def test_submit_round_should_raise_typed_error_when_session_snapshots_are_missing(self):
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_sequence=[
                {"id": "S1", "title": "Intro"},
                {"id": "S2", "title": "Follow Up"},
            ],
        )
        init_result = service.init_training(user_id="u17-submit-missing-snapshots", training_mode="self-paced")
        session_id = init_result["session_id"]
        session_row = service.db_manager.sessions[session_id]
        session_row.session_meta.pop("scenario_payload_sequence", None)
        session_row.session_meta.pop("scenario_payload_catalog", None)

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            service.submit_round(
                session_id=session_id,
                scenario_id="S1",
                user_input="hello",
            )

        self.assertEqual(cm.exception.reason, "scenario_snapshots_missing")
        self.assertEqual(
            cm.exception.details["missing_fields"],
            ["scenario_payload_sequence", "scenario_payload_catalog"],
        )
        self.assertEqual(service.db_manager.sessions[session_id].current_round_no, 0)
        self.assertEqual(service.training_store.get_training_rounds(session_id), [])

    def test_submit_round_should_raise_typed_error_when_persisted_sequence_is_missing(self):
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            scenario_sequence=[
                {"id": "S1", "title": "Intro"},
                {"id": "S2", "title": "Follow Up"},
            ],
        )
        init_result = service.init_training(user_id="u17-submit-missing-sequence", training_mode="self-paced")
        session_id = init_result["session_id"]
        service.db_manager.sessions[session_id].session_meta["scenario_sequence"] = []

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            service.submit_round(
                session_id=session_id,
                scenario_id="S1",
                user_input="hello",
            )

        self.assertEqual(cm.exception.reason, "scenario_sequence_empty")
        self.assertEqual(service.db_manager.sessions[session_id].current_round_no, 0)
        self.assertEqual(service.training_store.get_training_rounds(session_id), [])

    def test_service_should_delegate_all_read_models_to_injected_query_service(self):
        class _SpyQueryService:
            def __init__(self):
                self.calls = []

            def get_session_summary(self, session_id):
                self.calls.append(("summary", session_id))
                return {"source": "query", "kind": "summary", "session_id": session_id}

            def get_progress(self, session_id):
                self.calls.append(("progress", session_id))
                return {"source": "query", "kind": "progress", "session_id": session_id}

            def get_history(self, session_id):
                self.calls.append(("history", session_id))
                return {"source": "query", "kind": "history", "session_id": session_id}

            def get_report(self, session_id):
                self.calls.append(("report", session_id))
                return {"source": "query", "kind": "report", "session_id": session_id}

            def get_diagnostics(self, session_id):
                self.calls.append(("diagnostics", session_id))
                return {"source": "query", "kind": "diagnostics", "session_id": session_id}

        spy_query_service = _SpyQueryService()
        service = TrainingService(
            db_manager=_FakeDbManager(),
            evaluator=self.evaluator,
            query_service=spy_query_service,
        )

        self.assertEqual(service.get_session_summary("s-summary")["kind"], "summary")
        self.assertEqual(service.get_progress("s-progress")["kind"], "progress")
        self.assertEqual(service.get_history("s-history")["kind"], "history")
        self.assertEqual(service.get_report("s-report")["kind"], "report")
        self.assertEqual(service.get_diagnostics("s-diagnostics")["kind"], "diagnostics")
        self.assertEqual(
            spy_query_service.calls,
            [
                ("summary", "s-summary"),
                ("progress", "s-progress"),
                ("history", "s-history"),
                ("report", "s-report"),
                ("diagnostics", "s-diagnostics"),
            ],
        )

    def test_service_should_support_training_store_adapter_injection(self):
        """服务层应依赖训练存储接口，而不是硬绑具体 DBManager。"""
        store = DatabaseTrainingStore(_FakeDbManager())
        service = TrainingService(
            evaluator=self.evaluator,
            training_store=store,
        )

        result = service.init_training(user_id="u17", training_mode="self_paced")
        session_id = result["session_id"]

        self.assertEqual(store.db_manager.sessions[session_id].training_mode, "self-paced")
        self.assertEqual(result["session_id"], session_id)

    def test_duplicate_retry_should_return_idempotent_success(self):
        service = TrainingService(
            db_manager=_IdempotentDuplicateDbManager(),
            evaluator=self.evaluator,
        )
        init_result = service.init_training(user_id="u7")
        session_id = init_result["session_id"]

        first = service.submit_round(session_id=session_id, scenario_id="S1", user_input="hello")
        second = service.submit_round(session_id=session_id, scenario_id="S1", user_input="hello")

        self.assertEqual(first["round_no"], 1)
        self.assertEqual(second["round_no"], 1)
        self.assertEqual(second["evaluation"], first["evaluation"])
        self.assertEqual(second["k_state"], first["k_state"])
        self.assertEqual(second["s_state"], first["s_state"])
        self.assertEqual(second["runtime_state"], first["runtime_state"])
        self.assertEqual(second["consequence_events"], first["consequence_events"])
        self.assertEqual(second["decision_context"], first["decision_context"])

    def test_duplicate_detection_should_prefer_sqlstate_and_constraint(self):
        # 直接验证 DB 层冲突识别函数，避免服务层耦合 SQL 异常细节。
        orig = SimpleNamespace(
            pgcode="23505",
            diag=SimpleNamespace(constraint_name="uq_training_rounds_session_round"),
        )
        err = IntegrityError("insert", {"id": "x"}, orig)
        self.assertTrue(DatabaseManager._is_duplicate_round_conflict(err))

    def test_evaluation_payload_should_be_normalized_by_contract(self):
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_MalformedEvaluator())
        init_result = service.init_training(user_id="u8")
        result = service.submit_round(
            session_id=init_result["session_id"],
            scenario_id="S1",
            user_input="hello",
        )

        evaluation = result["evaluation"]
        self.assertEqual(evaluation["llm_model"], DEFAULT_EVAL_MODEL)
        self.assertEqual(evaluation["confidence"], 0.5)
        self.assertEqual(set(evaluation["skill_delta"].keys()), set(SKILL_CODES))
        self.assertEqual(set(evaluation["s_delta"].keys()), set(S_STATE_CODES))
        self.assertTrue(len(evaluation["evidence"]) >= 1)

    def test_risk_flags_should_be_normalized_by_contract(self):
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_RiskFlagEvaluator())
        init_result = service.init_training(user_id="u9")
        result = service.submit_round(
            session_id=init_result["session_id"],
            scenario_id="S1",
            user_input="hello",
        )

        self.assertEqual(result["evaluation"]["risk_flags"], ["source_exposure_risk"])

    def test_init_training_should_return_runtime_state_with_default_flags(self):
        """初始化训练时，应返回稳定运行时状态，并写入默认 runtime_flags。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=self.evaluator)

        result = service.init_training(user_id="u19-runtime-init")

        self.assertIn("runtime_state", result)
        self.assertEqual(result["runtime_state"]["current_round_no"], 0)
        self.assertEqual(result["runtime_state"]["current_scene_id"], "S1")
        self.assertEqual(
            result["runtime_state"]["runtime_flags"],
            {
                "panic_triggered": False,
                "source_exposed": False,
                "editor_locked": False,
                "high_risk_path": False,
            },
        )
        self.assertEqual(
            service.db_manager.sessions[result["session_id"]].session_meta["runtime_flags"],
            result["runtime_state"]["runtime_flags"],
        )

    def test_submit_round_should_persist_runtime_state_and_consequence_events(self):
        """来源暴露风险应触发运行时 flags、后果事件，并落入 session_meta。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_RiskFlagEvaluator())
        init_result = service.init_training(user_id="u20-runtime-submit")
        session_id = init_result["session_id"]

        result = service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )

        self.assertTrue(result["runtime_state"]["runtime_flags"]["source_exposed"])
        self.assertEqual(result["consequence_events"][0]["event_type"], "source_exposed")
        self.assertTrue(
            service.db_manager.sessions[session_id].session_meta["runtime_flags"]["source_exposed"]
        )

        round_row = service.db_manager.get_training_rounds(session_id)[0]
        self.assertTrue(round_row.user_action["runtime_state"]["runtime_flags"]["source_exposed"])
        self.assertEqual(round_row.user_action["consequence_events"][0]["event_type"], "source_exposed")

    def test_submit_round_should_trigger_public_panic_runtime_flag(self):
        """未核实即发布风险应触发公众恐慌相关运行时后果。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_PublicPanicEvaluator())
        init_result = service.init_training(user_id="u21-panic-submit")

        result = service.submit_round(
            session_id=init_result["session_id"],
            scenario_id="S1",
            user_input="hello",
        )

        self.assertTrue(result["runtime_state"]["runtime_flags"]["panic_triggered"])
        self.assertEqual(result["consequence_events"][0]["event_type"], "public_panic_triggered")
        self.assertEqual(result["consequence_events"][0]["related_flag"], "panic_triggered")

    def test_get_next_scenario_should_enter_failure_branch_after_public_panic(self):
        """触发公众恐慌后，下一场景应切换到失败分支。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_PublicPanicEvaluator())
        init_result = service.init_training(user_id="u22-branch-next")
        session_id = init_result["session_id"]

        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )
        next_result = service.get_next_scenario(session_id)

        self.assertEqual(next_result["scenario"]["id"], "S2B")
        self.assertEqual(next_result["scenario"]["branch_transition"]["source_scenario_id"], "S1")
        self.assertEqual(next_result["scenario"]["branch_transition"]["target_scenario_id"], "S2B")

    def test_branch_submission_should_reject_mainline_scenario_in_guided_mode(self):
        """失败分支锁定后，guided 模式不应再接受主线原场景提交。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_PublicPanicEvaluator())
        init_result = service.init_training(user_id="u23-branch-validate")
        session_id = init_result["session_id"]

        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )

        with self.assertRaises(TrainingScenarioMismatchError) as cm:
            service.submit_round(
                session_id=session_id,
                scenario_id="S2",
                user_input="hello-again",
            )

        self.assertIn("expected=S2B", str(cm.exception))
        self.assertEqual(cm.exception.expected_scenario_id, "S2B")
        self.assertEqual(cm.exception.round_no, 2)

    def test_branch_recovery_should_use_session_frozen_catalog_without_repository_fallback(self):
        """补救分支提交后，应只依赖会话冻结目录推进分支，不再回退实时仓储。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_PublicPanicEvaluator())
        init_result = service.init_training(user_id="u24-branch-recovery")
        session_id = init_result["session_id"]
        session_meta = service.db_manager.sessions[session_id].session_meta
        catalog_ids = [item["id"] for item in session_meta["scenario_payload_catalog"]]

        self.assertIn("S2B", catalog_ids)
        self.assertIn("S3R", catalog_ids)

        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )
        fail_repository = _FailOnScenarioReadRepository()
        service.scenario_repository = fail_repository
        service.flow_policy.branch_resolver.scenario_repository = fail_repository

        branch_result = service.get_next_scenario(session_id)
        self.assertEqual(branch_result["scenario"]["id"], "S2B")

        service.evaluator = _PanicRecoveryEvaluator()

        result = service.submit_round(
            session_id=session_id,
            scenario_id="S2B",
            user_input="repair",
            selected_option="B",
        )

        self.assertEqual(result["decision_context"]["selection_source"], "branch_transition")
        self.assertEqual(
            result["decision_context"]["selected_branch_transition"]["source_scenario_id"],
            "S1",
        )
        self.assertEqual(
            result["decision_context"]["selected_branch_transition"]["target_scenario_id"],
            "S2B",
        )

        round_row = service.db_manager.get_training_rounds(session_id)[1]
        self.assertEqual(
            round_row.user_action["decision_context"]["selected_branch_transition"]["target_scenario_id"],
            "S2B",
        )

        observations = service.db_manager.get_kt_observations(session_id)
        self.assertEqual(observations[1].scenario_id, "S2B")
        self.assertTrue(observations[1].scenario_title)

        next_result = service.get_next_scenario(session_id)
        self.assertFalse(next_result["runtime_state"]["runtime_flags"]["panic_triggered"])
        self.assertEqual(next_result["scenario"]["id"], "S3R")
        self.assertEqual(next_result["scenario"]["branch_transition"]["source_scenario_id"], "S2B")

    def test_report_and_diagnostics_should_aggregate_branch_transitions(self):
        """报告与诊断应显式聚合分支发生次数、轮次与路径摘要。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_PublicPanicEvaluator())
        init_result = service.init_training(user_id="u25-branch-summary")
        session_id = init_result["session_id"]

        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )
        service.evaluator = _PanicRecoveryEvaluator()
        service.submit_round(
            session_id=session_id,
            scenario_id="S2B",
            user_input="repair",
            selected_option="B",
        )
        service.evaluator = _FakeEvaluator()
        service.submit_round(
            session_id=session_id,
            scenario_id="S3R",
            user_input="follow-up",
            selected_option="B",
        )

        diagnostics = service.get_diagnostics(session_id)
        report = service.get_report(session_id)

        self.assertEqual(diagnostics["summary"]["branch_transition_count"], 2)
        self.assertEqual(diagnostics["summary"]["branch_transition_rounds"], [2, 3])
        self.assertEqual(
            diagnostics["summary"]["last_branch_transition"]["target_scenario_id"],
            "S3R",
        )
        self.assertEqual(
            diagnostics["summary"]["branch_transitions"][0]["target_scenario_id"],
            "S2B",
        )
        selection_source_counts = {
            item["code"]: item["count"] for item in diagnostics["summary"]["selection_source_counts"]
        }
        self.assertEqual(selection_source_counts["branch_transition"], 2)

        self.assertEqual(report["summary"]["branch_transition_count"], 2)
        self.assertEqual(report["summary"]["branch_transition_rounds"], [2, 3])
        self.assertEqual(len(report["summary"]["branch_transitions"]), 2)
        self.assertEqual(report["summary"]["branch_transitions"][1]["target_scenario_id"], "S3R")
        self.assertTrue(
            any("分支跳转" in suggestion for suggestion in report["summary"]["review_suggestions"])
        )

    def test_high_risk_round_should_mark_kt_observation(self):
        """高风险回合的 KT 观测应显式标记风险，避免后续只能反解析评估原文。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_RiskFlagEvaluator())
        init_result = service.init_training(user_id="u9-risk")
        session_id = init_result["session_id"]

        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )

        observations = service.db_manager.get_kt_observations(session_id)
        self.assertTrue(observations[0].is_high_risk)
        self.assertEqual(observations[0].primary_risk_flag, "source_exposure_risk")

    def test_get_diagnostics_should_return_structured_training_artifacts(self):
        """诊断接口应能聚合推荐日志、审计事件、KT 观测和摘要统计。"""
        service = TrainingService(db_manager=_FakeDbManager(), evaluator=_RiskFlagEvaluator())
        init_result = service.init_training(user_id="u18-diagnostics", training_mode="self-paced")
        session_id = init_result["session_id"]

        service.submit_round(
            session_id=session_id,
            scenario_id=init_result["next_scenario"]["id"],
            user_input="hello",
            selected_option="A",
        )
        diagnostics = service.get_diagnostics(session_id)

        self.assertEqual(diagnostics["session_id"], session_id)
        self.assertEqual(diagnostics["recommendation_logs"][0]["round_no"], 1)
        self.assertEqual(diagnostics["audit_events"][0]["event_type"], "session_initialized")
        self.assertEqual(diagnostics["kt_observations"][0]["round_no"], 1)
        self.assertTrue(diagnostics["runtime_state"]["runtime_flags"]["source_exposed"])
        self.assertEqual(diagnostics["summary"]["total_recommendation_logs"], 1)
        self.assertEqual(diagnostics["summary"]["total_audit_events"], 3)
        self.assertEqual(diagnostics["summary"]["total_kt_observations"], 1)
        self.assertEqual(diagnostics["summary"]["high_risk_round_nos"], [1])
        self.assertEqual(diagnostics["summary"]["recommended_vs_selected_mismatch_count"], 0)
        self.assertEqual(diagnostics["summary"]["last_primary_risk_flag"], "source_exposure_risk")
        self.assertEqual(diagnostics["summary"]["last_phase_tags"], ["opening"])
        self.assertEqual(diagnostics["summary"]["phase_transition_count"], 0)
        self.assertEqual(diagnostics["summary"]["phase_transition_rounds"], [])
        self.assertEqual(diagnostics["summary"]["source_exposed_round_count"], 1)
        self.assertEqual(diagnostics["summary"]["source_exposed_rounds"], [1])

        risk_flag_counts = {
            item["code"]: item["count"] for item in diagnostics["summary"]["risk_flag_counts"]
        }
        event_type_counts = {
            item["code"]: item["count"] for item in diagnostics["summary"]["event_type_counts"]
        }
        phase_tag_counts = {
            item["code"]: item["count"] for item in diagnostics["summary"]["phase_tag_counts"]
        }
        self.assertEqual(risk_flag_counts["source_exposure_risk"], 1)
        self.assertEqual(event_type_counts["session_initialized"], 1)
        self.assertEqual(event_type_counts["round_submitted"], 1)
        self.assertEqual(event_type_counts["source_exposed"], 1)
        self.assertEqual(phase_tag_counts["opening"], 1)


if __name__ == "__main__":
    unittest.main()
