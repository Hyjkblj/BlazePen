"""训练服务（P2）：负责流程编排、状态更新与持久化调用。"""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from types import SimpleNamespace
from typing import Any, Dict, List

from training.constants import DEFAULT_EVAL_MODEL, DEFAULT_K_STATE, DEFAULT_S_STATE, SKILL_CODES, TRAINING_RUNTIME_CONFIG
from training.consequence_engine import ConsequenceEngine
from training.contracts import RoundEvaluationPayload
from training.ending_policy import EndingPolicy
from training.evaluator import TrainingRoundEvaluator
from training.exceptions import DuplicateRoundSubmissionError, TrainingSessionNotFoundError
from training.phase_policy import TrainingPhasePolicy, TrainingPhaseSnapshot
from training.recommendation_policy import RecommendationPolicy
from training.reporting_policy import TrainingReportingPolicy
from training.round_flow_policy import TrainingRoundFlowPolicy
from training.runtime_events import RuntimeConsequenceEvent
from training.runtime_state import GameRuntimeFlags, GameRuntimeState
from training.scenario_policy import ScenarioPolicy
from training.session_snapshot_policy import SessionScenarioSnapshotPolicy
from training.training_outputs import (
    TrainingAuditEventOutput,
    TrainingConsequenceEventOutput,
    TrainingDecisionCandidateOutput,
    TrainingDiagnosticsOutput,
    TrainingEvaluationOutput,
    TrainingInitOutput,
    TrainingKtObservationOutput,
    TrainingNextScenarioOutput,
    TrainingPlayerProfileOutput,
    TrainingProgressOutput,
    TrainingRecommendationLogOutput,
    TrainingReportHistoryItemOutput,
    TrainingReportOutput,
    TrainingRuntimeStateOutput,
    TrainingRoundDecisionContextOutput,
    TrainingRoundSubmitOutput,
    TrainingScenarioOutput,
)
from training.scenario_repository import ScenarioRepository
from training.telemetry_policy import TrainingTelemetryPolicy
from training.training_mode import TrainingModeCatalog
from training.training_store import DatabaseTrainingStore, TrainingStoreProtocol
from utils.logger import get_logger

logger = get_logger(__name__)

USER_ACTION_TEXT_KEY = "text"
USER_ACTION_SELECTED_OPTION_KEY = "selected_option"
USER_ACTION_DECISION_CONTEXT_KEY = "decision_context"
USER_ACTION_RUNTIME_STATE_KEY = "runtime_state"
USER_ACTION_CONSEQUENCE_EVENTS_KEY = "consequence_events"
USER_ACTION_BRANCH_HINTS_KEY = "branch_hints"
SELECTION_SOURCE_ORDERED_SEQUENCE = "ordered_sequence"
SELECTION_SOURCE_TOP_RECOMMENDATION = "top_recommendation"
SELECTION_SOURCE_CANDIDATE_POOL = "candidate_pool"
SELECTION_SOURCE_FALLBACK_SEQUENCE = "fallback_sequence"
SELECTION_SOURCE_BRANCH_TRANSITION = "branch_transition"


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


class TrainingService:
    """训练服务：只做业务编排，不关心底层数据库异常细节。"""

    _SCENARIO_SEQUENCE: List[Dict[str, str]] = list(
        {"id": item.id, "title": item.title} for item in TRAINING_RUNTIME_CONFIG.scenario.default_sequence
    )

    @staticmethod
    def _build_default_scenario_sequence(runtime_config: Any) -> List[Dict[str, str]]:
        """优先从当前运行时配置构建默认场景序列，避免偷偷绑定模块级常量。"""
        return [
            {
                "id": str(item.id),
                "title": str(item.title),
            }
            for item in runtime_config.scenario.default_sequence
        ]

    def __init__(
        self,
        db_manager: Any = None,
        evaluator: Any = None,
        training_store: TrainingStoreProtocol | None = None,
        scenario_sequence: List[Dict[str, str]] | None = None,
        scenario_policy: ScenarioPolicy | None = None,
        ending_policy: EndingPolicy | None = None,
        scenario_repository: ScenarioRepository | None = None,
        recommendation_policy: RecommendationPolicy | None = None,
        phase_policy: TrainingPhasePolicy | None = None,
        flow_policy: TrainingRoundFlowPolicy | None = None,
        telemetry_policy: TrainingTelemetryPolicy | None = None,
        reporting_policy: TrainingReportingPolicy | None = None,
        consequence_engine: ConsequenceEngine | None = None,
        session_snapshot_policy: SessionScenarioSnapshotPolicy | None = None,
        runtime_config: Any = None,
    ):
        self.runtime_config = runtime_config or TRAINING_RUNTIME_CONFIG
        self.mode_catalog = TrainingModeCatalog(runtime_config=self.runtime_config)

        # 兼容旧构造参数：允许继续传入 fake db_manager / 旧持久化对象，
        # 但服务内部默认已切到训练专用 store，而不是直接 new 通用 DatabaseManager。
        if training_store is not None:
            self.training_store = training_store
            self.db_manager = db_manager or getattr(training_store, "db_manager", training_store)
        else:
            self.training_store = DatabaseTrainingStore(db_manager)
            # 为了兼容现有测试对 `service.db_manager` 的观察，这里继续暴露底层对象别名。
            self.db_manager = db_manager or getattr(self.training_store, "db_manager", self.training_store)

        self._lock = Lock()
        self.evaluator = evaluator or TrainingRoundEvaluator(runtime_config=self.runtime_config)
        self.scenario_repository = scenario_repository or ScenarioRepository()
        # 阶段策略独立注入，供推荐、审计、后续诊断面板复用。
        self.phase_policy = phase_policy or TrainingPhasePolicy(runtime_config=self.runtime_config)
        self.recommendation_policy = recommendation_policy or RecommendationPolicy(
            runtime_config=self.runtime_config,
            phase_policy=self.phase_policy,
        )
        # 报告与诊断聚合统一下沉到独立 policy，避免 TrainingService 再次膨胀。
        self.reporting_policy = reporting_policy or TrainingReportingPolicy(runtime_config=self.runtime_config)
        # 观测与审计组装统一下沉到 telemetry policy，避免 service 内继续散落结构化日志细节。
        self.telemetry_policy = telemetry_policy or TrainingTelemetryPolicy(phase_policy=self.phase_policy)
        # 运行时后果由独立引擎负责，服务层只做编排与持久化。
        self.consequence_engine = consequence_engine or ConsequenceEngine()

        default_scenario_sequence = self._build_default_scenario_sequence(self.runtime_config)
        self._scenario_sequence = list(scenario_sequence or default_scenario_sequence)
        self.scenario_policy = scenario_policy or ScenarioPolicy(
            default_sequence=self._scenario_sequence,
            scenario_version=self.runtime_config.scenario.version,
            runtime_config=self.runtime_config,
        )
        # 会话快照策略独立抽离，便于后续继续演进老会话回填、快照诊断和分支冻结逻辑。
        self.session_snapshot_policy = session_snapshot_policy or SessionScenarioSnapshotPolicy(
            scenario_policy=self.scenario_policy,
            scenario_repository=self.scenario_repository,
        )
        self.flow_policy = flow_policy or TrainingRoundFlowPolicy(
            scenario_policy=self.scenario_policy,
            recommendation_policy=self.recommendation_policy,
            runtime_config=self.runtime_config,
        )
        self.ending_policy = ending_policy or EndingPolicy(runtime_config=self.runtime_config)

    def init_training(
        self,
        user_id: str,
        character_id: int | None = None,
        training_mode: str = "guided",
        player_profile: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """初始化训练会话，并创建 round=0 的初始快照。"""
        normalized_mode = self.mode_catalog.normalize(training_mode, default="guided")

        with self._lock:
            # 在会话创建时同时冻结主线快照和可达分支目录，避免后续发版导致老会话内容漂移。
            snapshot_bundle = self.session_snapshot_policy.freeze_session_snapshots(
                self.scenario_policy.get_default_sequence()
            )
            frozen_payload_sequence = snapshot_bundle.scenario_payload_sequence
            frozen_payload_catalog = snapshot_bundle.scenario_payload_catalog
            sequence = self.scenario_repository.build_summary_sequence(frozen_payload_sequence)
            initial_phase_snapshot = self.phase_policy.resolve_round_phase(
                training_mode=normalized_mode,
                round_no=1,
                total_rounds=len(sequence),
            )
            session_meta = self.scenario_policy.build_session_meta(
                sequence,
                scenario_payload_sequence=frozen_payload_sequence,
                scenario_payload_catalog=frozen_payload_catalog,
                scenario_bank_version=self.scenario_repository.version,
                player_profile=player_profile,
            )
            session_meta = self._merge_session_meta_runtime_flags(
                session_meta=session_meta,
                runtime_flags=self._build_default_runtime_flags(),
            )
            row = self.training_store.create_training_session_artifacts(
                user_id=user_id,
                character_id=character_id,
                training_mode=normalized_mode,
                k_state=dict(DEFAULT_K_STATE),
                s_state=dict(DEFAULT_S_STATE),
                session_meta=session_meta,
                audit_event_payload=self.telemetry_policy.build_session_initialized_audit_event(
                    training_mode=normalized_mode,
                    scenario_bank_version=self.scenario_repository.version,
                    scenario_count=len(sequence),
                    phase_snapshot=initial_phase_snapshot,
                ).to_dict(),
            )
            session_id = row.session_id

        logger.info("training session initialized: session_id=%s user_id=%s", session_id, user_id)
        next_scenario_bundle = self.flow_policy.build_next_scenario_bundle(
            training_mode=normalized_mode,
            current_round_no=row.current_round_no,
            session_sequence=sequence,
            scenario_payload_sequence=frozen_payload_sequence,
            scenario_payload_catalog=frozen_payload_catalog,
            completed_scenario_ids=[],
            k_state=self._normalize_k_state(row.k_state),
            s_state=self._normalize_s_state(row.s_state),
            recent_risk_rounds=[],
            runtime_flags=self._resolve_session_runtime_flags(row),
            current_scenario_id=getattr(row, "current_scenario_id", None),
        )
        return TrainingInitOutput(
            session_id=session_id,
            status=row.status,
            round_no=row.current_round_no,
            # 对外统一返回补齐后的状态结构，避免前端处理历史脏数据时缺键。
            k_state=self._normalize_k_state(row.k_state),
            s_state=self._normalize_s_state(row.s_state),
            player_profile=self._resolve_session_player_profile(row),
            runtime_state=self._build_training_runtime_state_output(
                self._build_runtime_state(
                    session=row,
                    current_round_no=row.current_round_no,
                    current_scene_id=(
                        getattr(next_scenario_bundle, "scenario", {}) or {}
                    ).get("id"),
                )
            ),
            next_scenario=self._build_training_scenario_output(next_scenario_bundle.scenario),
            scenario_candidates=self._build_training_scenario_output_list(next_scenario_bundle.scenario_candidates),
        ).to_dict()

    def get_next_scenario(self, session_id: str) -> Dict[str, Any]:
        """根据当前回合返回下一场景。"""
        session = self._get_session_or_raise(session_id)
        if session.status == "completed":
            ending = self.training_store.get_ending_result(session_id)
            return TrainingNextScenarioOutput(
                session_id=session_id,
                status="completed",
                round_no=session.current_round_no,
                # 已完成时仍返回稳定字段，避免前端按分支解析两套结构。
                scenario=None,
                scenario_candidates=[],
                k_state=self._normalize_k_state(session.k_state),
                s_state=self._normalize_s_state(session.s_state),
                player_profile=self._resolve_session_player_profile(session),
                runtime_state=self._build_training_runtime_state_output(
                    self._build_runtime_state(session=session)
                ),
                ending=ending.report_payload if ending else None,
            ).to_dict()

        snapshot_bundle = self.session_snapshot_policy.ensure_session_snapshots(
            session=session,
            training_store=self.training_store,
        )
        session = snapshot_bundle.session or session
        scenario_payload_sequence = snapshot_bundle.scenario_payload_sequence
        scenario_payload_catalog = snapshot_bundle.scenario_payload_catalog
        session_sequence = self._resolve_session_scenario_sequence(session)
        if not session_sequence:
            raise ValueError("scenario sequence is empty")

        next_scenario_bundle = self.flow_policy.build_next_scenario_bundle(
            training_mode=self._normalize_session_training_mode(session),
            current_round_no=session.current_round_no,
            session_sequence=session_sequence,
            scenario_payload_sequence=scenario_payload_sequence,
            scenario_payload_catalog=scenario_payload_catalog,
            completed_scenario_ids=self._get_completed_scenario_ids(session_id),
            k_state=self._normalize_k_state(session.k_state),
            s_state=self._normalize_s_state(session.s_state),
            recent_risk_rounds=self._get_recent_risk_rounds(session_id),
            runtime_flags=self._resolve_session_runtime_flags(session),
            current_scenario_id=getattr(session, "current_scenario_id", None),
        )
        return TrainingNextScenarioOutput(
            session_id=session_id,
            status=session.status,
            round_no=session.current_round_no + 1,
            scenario=self._build_training_scenario_output(next_scenario_bundle.scenario),
            scenario_candidates=self._build_training_scenario_output_list(next_scenario_bundle.scenario_candidates),
            k_state=self._normalize_k_state(session.k_state),
            s_state=self._normalize_s_state(session.s_state),
            player_profile=self._resolve_session_player_profile(session),
            runtime_state=self._build_training_runtime_state_output(
                self._build_runtime_state(
                    session=session,
                    current_round_no=session.current_round_no,
                    current_scene_id=(
                        getattr(next_scenario_bundle, "scenario", {}) or {}
                    ).get("id"),
                )
            ),
        ).to_dict()

    def submit_round(
        self,
        session_id: str,
        scenario_id: str,
        user_input: str,
        selected_option: str | None = None,
    ) -> Dict[str, Any]:
        """提交单回合，并原子化保存本回合所有工件。"""
        session = self._get_session_or_raise(session_id)
        if session.status == "completed":
            raise ValueError("training session already completed")

        snapshot_bundle = self.session_snapshot_policy.ensure_session_snapshots(
            session=session,
            training_store=self.training_store,
        )
        session = snapshot_bundle.session or session
        scenario_payload_sequence = snapshot_bundle.scenario_payload_sequence
        scenario_payload_catalog = snapshot_bundle.scenario_payload_catalog
        session_sequence = self._resolve_session_scenario_sequence(session)
        training_mode = self._normalize_session_training_mode(session)
        completed_scenario_ids = self._get_completed_scenario_ids(session_id)
        k_before = self._normalize_k_state(session.k_state)
        s_before = self._normalize_s_state(session.s_state)
        recent_risk_rounds = self._get_recent_risk_rounds(session_id)
        round_no = session.current_round_no + 1

        # 先基于当前上下文生成推荐结果，确保“前端看到的候选集”和“提交时回放的决策上下文”来自同一份数据。
        next_scenario_bundle = self.flow_policy.build_next_scenario_bundle(
            training_mode=training_mode,
            current_round_no=session.current_round_no,
            session_sequence=session_sequence,
            scenario_payload_sequence=scenario_payload_sequence,
            scenario_payload_catalog=scenario_payload_catalog,
            completed_scenario_ids=completed_scenario_ids,
            k_state=k_before,
            s_state=s_before,
            recent_risk_rounds=recent_risk_rounds,
            runtime_flags=self._resolve_session_runtime_flags(session),
            current_scenario_id=getattr(session, "current_scenario_id", None),
        )
        self.flow_policy.validate_submission(
            training_mode=training_mode,
            current_round_no=session.current_round_no,
            submitted_scenario_id=scenario_id,
            session_sequence=session_sequence,
            scenario_payload_sequence=scenario_payload_sequence,
            scenario_payload_catalog=scenario_payload_catalog,
            completed_scenario_ids=completed_scenario_ids,
            k_state=k_before,
            s_state=s_before,
            recent_risk_rounds=recent_risk_rounds,
            runtime_flags=self._resolve_session_runtime_flags(session),
            current_scenario_id=getattr(session, "current_scenario_id", None),
        )
        decision_context = self._build_round_decision_context(
            training_mode=training_mode,
            submitted_scenario_id=scenario_id,
            next_scenario_bundle=next_scenario_bundle,
        )
        user_action = self._build_round_user_action(
            user_input=user_input,
            selected_option=selected_option,
            decision_context=decision_context,
        )
        recommendation_log_payload = self._build_recommendation_log_payload(
            training_mode=training_mode,
            decision_context=decision_context,
        )
        selected_scenario_payload = self.session_snapshot_policy.resolve_scenario_payload_by_id(
            scenario_payload_sequence=scenario_payload_sequence,
            scenario_payload_catalog=scenario_payload_catalog,
            scenario_id=scenario_id,
        )

        # 评估结果在服务边界统一过契约，避免下游散落字典键判断。
        eval_result = RoundEvaluationPayload.from_raw(
            self.evaluator.evaluate_round(
                user_input=user_input,
                scenario_id=scenario_id,
                round_no=round_no,
                k_before=k_before,
                s_before=s_before,
            )
        ).to_dict()

        updated_k = self._update_k(k_before, eval_result["skill_delta"])
        updated_s = self._update_s(s_before, eval_result["s_delta"])
        runtime_state = self._build_runtime_state(
            session=session,
            current_round_no=round_no,
            current_scene_id=scenario_id,
            k_state=updated_k,
            s_state=updated_s,
        )
        consequence_result = self.consequence_engine.apply(
            runtime_state=runtime_state,
            evaluation_payload=eval_result,
            round_no=round_no,
            scenario_payload=selected_scenario_payload,
            selected_option=selected_option,
            recent_risk_rounds=recent_risk_rounds,
        )
        runtime_state = consequence_result.runtime_state
        updated_session_meta = self._merge_session_meta_runtime_flags(
            session_meta=getattr(session, "session_meta", None),
            runtime_flags=runtime_state.runtime_flags.to_dict(),
        )
        user_action = self._attach_runtime_artifacts_to_user_action(
            user_action=user_action,
            runtime_state=runtime_state,
            consequence_events=consequence_result.consequence_events,
            branch_hints=consequence_result.branch_hints,
        )

        is_completed = self.flow_policy.is_session_completed(
            round_no=round_no,
            session_sequence=session_sequence,
        )
        current_phase_snapshot = self.phase_policy.resolve_round_phase(
            training_mode=training_mode,
            round_no=round_no,
            total_rounds=len(session_sequence),
        )
        previous_phase_snapshot = self._resolve_previous_phase_snapshot(
            training_mode=training_mode,
            round_no=round_no,
            total_rounds=len(session_sequence),
        )
        status = "completed" if is_completed else session.status
        end_time = datetime.utcnow() if is_completed else None

        ending_payload = None
        if is_completed:
            # 在入库前先算结局，确保“结局 + 会话完成状态”同事务提交。
            history_rows = self.training_store.get_round_evaluations_by_session(session_id)
            history_rows = list(history_rows) + [SimpleNamespace(risk_flags=eval_result.get("risk_flags", []))]
            ending_payload = self._resolve_ending(updated_k, updated_s, history_rows)
        audit_event_payloads = self._build_round_audit_event_payloads(
            training_mode=training_mode,
            round_no=round_no,
            scenario_id=scenario_id,
            selected_option=selected_option,
            eval_result=eval_result,
            decision_context=decision_context,
            current_phase_snapshot=current_phase_snapshot,
            previous_phase_snapshot=previous_phase_snapshot,
            is_completed=is_completed,
            ending_payload=ending_payload,
        )
        audit_event_payloads.extend(
            self._build_runtime_consequence_audit_event_payloads(
                training_mode=training_mode,
                round_no=round_no,
                runtime_flags=runtime_state.runtime_flags,
                consequence_events=consequence_result.consequence_events,
                branch_hints=consequence_result.branch_hints,
            )
        )
        kt_observation_payload = self._build_kt_observation_payload(
            training_mode=training_mode,
            round_no=round_no,
            scenario_payload=selected_scenario_payload,
            k_before=k_before,
            k_after=updated_k,
            s_before=s_before,
            s_after=updated_s,
            eval_result=eval_result,
        )

        try:
            # DB 层会把数据库特有异常翻译成领域异常，服务层只处理业务语义。
            self.training_store.save_training_round_artifacts(
                session_id=session_id,
                round_no=round_no,
                scenario_id=scenario_id,
                user_input_raw=user_input,
                selected_option=selected_option,
                user_action=user_action,
                state_before=s_before,
                state_after=updated_s,
                kt_before=k_before,
                kt_after=updated_k,
                feedback_text="; ".join(eval_result.get("evidence", [])),
                evaluation_payload=eval_result,
                ending_payload=ending_payload,
                status=status,
                end_time=end_time,
                session_meta=updated_session_meta,
                recommendation_log_payload=recommendation_log_payload,
                audit_event_payloads=audit_event_payloads,
                kt_observation_payload=kt_observation_payload,
            )
        except DuplicateRoundSubmissionError:
            # 并发重试命中唯一约束时，优先返回已落库结果，实现幂等体验。
            existing = self._build_duplicate_submit_response(session_id=session_id, round_no=round_no)
            if existing is not None:
                logger.info(
                    "duplicate round submission idempotent hit: session_id=%s round_no=%s",
                    session_id,
                    round_no,
                )
                return existing
            raise ValueError(f"duplicate round submission: session_id={session_id}, round_no={round_no}")
        except TrainingSessionNotFoundError as exc:
            raise ValueError(str(exc)) from exc

        return TrainingRoundSubmitOutput(
            session_id=session_id,
            round_no=round_no,
            evaluation=self._build_training_evaluation_output(eval_result),
            k_state=updated_k,
            s_state=updated_s,
            player_profile=self._resolve_session_player_profile(session),
            runtime_state=self._build_training_runtime_state_output(runtime_state),
            consequence_events=self._build_training_consequence_event_outputs(
                consequence_result.consequence_events
            ),
            is_completed=is_completed,
            ending=ending_payload,
            decision_context=decision_context,
        ).to_dict()

    def get_progress(self, session_id: str) -> Dict[str, Any]:
        """获取训练进度。"""
        session = self._get_session_or_raise(session_id)
        session_sequence = self._resolve_session_scenario_sequence(session)
        return TrainingProgressOutput(
            session_id=session_id,
            status=session.status,
            round_no=session.current_round_no,
            total_rounds=len(session_sequence),
            k_state=self._normalize_k_state(session.k_state),
            s_state=self._normalize_s_state(session.s_state),
            player_profile=self._resolve_session_player_profile(session),
            runtime_state=self._build_training_runtime_state_output(
                self._build_runtime_state(session=session)
            ),
        ).to_dict()

    def get_report(self, session_id: str) -> Dict[str, Any]:
        """获取报告（含历史回放与最终状态）。"""
        session = self._get_session_or_raise(session_id)
        rounds = self.training_store.get_training_rounds(session_id)
        evaluations = self.training_store.get_round_evaluations_by_session(session_id)
        kt_observations = self.training_store.get_kt_observations(session_id)
        snapshot_bundle = self.session_snapshot_policy.ensure_session_snapshots(
            session=session,
            training_store=self.training_store,
        )
        session = snapshot_bundle.session or session
        scenario_payload_sequence = snapshot_bundle.scenario_payload_sequence
        scenario_payload_catalog = snapshot_bundle.scenario_payload_catalog
        scenario_title_map = self._build_report_scenario_title_map(scenario_payload_catalog)
        eval_map = {item.round_id: item for item in evaluations}
        kt_observation_map = {item.round_no: item for item in kt_observations}
        ending = self.training_store.get_ending_result(session_id)

        history = self._build_training_report_history(
            rounds=rounds,
            eval_map=eval_map,
            kt_observation_map=kt_observation_map,
        )

        # 报告图表统一以 round=0 作为起点，前端无需再自己猜测初始状态。
        initial_k_state, initial_s_state = self._resolve_report_initial_states(
            session=session,
            rounds=rounds,
        )
        final_k = self._normalize_k_state(session.k_state)
        final_s = self._normalize_s_state(session.s_state)
        round_snapshots = self._build_training_report_round_snapshots(
            rounds=rounds,
            eval_map=eval_map,
            kt_observation_map=kt_observation_map,
            scenario_title_map=scenario_title_map,
        )
        report_artifacts = self.reporting_policy.build_report_artifacts(
            initial_k_state=initial_k_state,
            initial_s_state=initial_s_state,
            final_k_state=final_k,
            final_s_state=final_s,
            round_snapshots=round_snapshots,
        )
        report_summary = report_artifacts.summary
        report_improvement = (
            float(report_summary.get("weighted_score_delta", 0.0) or 0.0)
            if isinstance(report_summary, dict)
            else float(getattr(report_summary, "weighted_score_delta", 0.0) or 0.0)
        )
        return TrainingReportOutput(
            session_id=session_id,
            status=session.status,
            rounds=session.current_round_no,
            k_state_final=final_k,
            s_state_final=final_s,
            improvement=report_improvement,
            player_profile=self._resolve_session_player_profile(session),
            runtime_state=self._build_training_runtime_state_output(
                self._build_runtime_state(session=session)
            ),
            ending=ending.report_payload if ending else None,
            summary=report_summary,
            ability_radar=report_artifacts.ability_radar,
            state_radar=report_artifacts.state_radar,
            growth_curve=report_artifacts.growth_curve,
            history=history,
        ).to_dict()

    def get_diagnostics(self, session_id: str) -> Dict[str, Any]:
        """获取训练诊断数据，聚合推荐日志、审计事件和 KT 结构化观测。"""
        session = self._get_session_or_raise(session_id)
        recommendation_logs = self.training_store.get_scenario_recommendation_logs(session_id)
        audit_events = self.training_store.get_training_audit_events(session_id)
        kt_observations = self.training_store.get_kt_observations(session_id)

        recommendation_outputs = self._build_training_recommendation_log_outputs(recommendation_logs)
        audit_event_outputs = self._build_training_audit_event_outputs(audit_events)
        kt_observation_outputs = self._build_training_kt_observation_outputs(kt_observations)

        summary_output = self.reporting_policy.build_diagnostics_summary(
            recommendation_logs=recommendation_outputs,
            audit_events=audit_event_outputs,
            kt_observations=kt_observation_outputs,
        )

        return TrainingDiagnosticsOutput(
            session_id=session_id,
            status=session.status,
            round_no=session.current_round_no,
            player_profile=self._resolve_session_player_profile(session),
            runtime_state=self._build_training_runtime_state_output(
                self._build_runtime_state(session=session)
            ),
            summary=summary_output,
            recommendation_logs=recommendation_outputs,
            audit_events=audit_event_outputs,
            kt_observations=kt_observation_outputs,
        ).to_dict()

    def _resolve_report_initial_states(
        self,
        session: Any,
        rounds: List[Any],
    ) -> tuple[Dict[str, float], Dict[str, float]]:
        """解析报告起点状态。

        规则：
        1. 有回合时，以首轮 `before` 状态作为 round=0 起点
        2. 无回合时，以当前会话状态作为起点
        """
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

    def _build_training_report_history(
        self,
        rounds: List[Any],
        eval_map: Dict[str, Any],
        kt_observation_map: Dict[int, Any],
    ) -> List[TrainingReportHistoryItemOutput]:
        """批量构建训练报告回放历史，避免主流程内联过多 DTO 拼装细节。"""
        history: List[TrainingReportHistoryItemOutput] = []
        for row in rounds:
            evaluation_row = eval_map.get(row.round_id)
            evaluation_payload = None
            if evaluation_row:
                # 报告回放也走同一契约，保证前后端看到的是稳定结构。
                evaluation_payload = self._build_training_evaluation_output(evaluation_row.raw_payload)

            history.append(
                TrainingReportHistoryItemOutput(
                    round_no=row.round_no,
                    scenario_id=row.scenario_id,
                    user_input=row.user_input_raw,
                    selected_option=row.selected_option,
                    evaluation=evaluation_payload,
                    k_state_before=row.kt_before,
                    k_state_after=row.kt_after,
                    s_state_before=row.state_before,
                    s_state_after=row.state_after,
                    timestamp=row.created_at.isoformat() if row.created_at else None,
                    decision_context=self._extract_round_decision_context(row.user_action),
                    kt_observation=self._build_training_kt_observation_output(
                        kt_observation_map.get(row.round_no)
                    ),
                    runtime_state=self._extract_round_runtime_state(row.user_action),
                    consequence_events=self._extract_round_consequence_events(row.user_action),
                )
            )
        return history

    def _build_report_scenario_title_map(
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

    def _build_training_report_round_snapshots(
        self,
        rounds: List[Any],
        eval_map: Dict[str, Any],
        kt_observation_map: Dict[int, Any],
        scenario_title_map: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """把回合行数据整理成报告策略可直接消费的标准快照。"""
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

            # 历史数据可能还没有 KT 观测，报告层统一回退到评估结果补齐风险字段。
            snapshots.append(
                {
                    "round_no": round_no,
                    "scenario_id": scenario_id,
                    "scenario_title": (
                        kt_observation_output.scenario_title
                        if kt_observation_output is not None
                        and kt_observation_output.scenario_title
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
                    "runtime_flags": self._extract_round_runtime_flags(row.user_action),
                    "consequence_events": [
                        item.to_dict()
                        for item in self._extract_round_consequence_events(row.user_action)
                    ],
                    "branch_transition": self._extract_round_branch_transition(row.user_action),
                    "timestamp": (
                        getattr(row, "created_at", None).isoformat()
                        if getattr(row, "created_at", None)
                        else None
                    ),
                }
            )
        return snapshots

    def _resolve_session_scenario_sequence(self, session: Any) -> List[Dict[str, str]]:
        return self.scenario_policy.resolve_session_sequence(session)

    def _resolve_session_player_profile(
        self,
        session: Any,
    ) -> TrainingPlayerProfileOutput | None:
        """统一从会话中读取并归一化玩家档案，避免对外输出直接暴露原始 session_meta。"""
        return self._build_training_player_profile_output(self.scenario_policy.resolve_session_player_profile(session))

    def _resolve_session_player_profile_payload(
        self,
        session: Any,
    ) -> Dict[str, Any]:
        """读取玩家档案原始字典，供运行时状态聚合复用。"""
        payload = self.scenario_policy.resolve_session_player_profile(session)
        return dict(payload or {})

    def _build_default_runtime_flags(self) -> Dict[str, bool]:
        """构建默认运行时 flags。"""
        return GameRuntimeFlags().to_dict()

    def _resolve_session_runtime_flags(
        self,
        session: Any,
    ) -> Dict[str, bool]:
        """统一从 session_meta 中读取运行时 flags。"""
        session_meta = getattr(session, "session_meta", None)
        if not isinstance(session_meta, dict):
            return self._build_default_runtime_flags()
        return GameRuntimeFlags.from_payload(session_meta.get("runtime_flags")).to_dict()

    def _merge_session_meta_runtime_flags(
        self,
        session_meta: Dict[str, Any] | None,
        runtime_flags: Dict[str, Any] | GameRuntimeFlags | None,
    ) -> Dict[str, Any]:
        """在保留原有 session_meta 的前提下更新运行时 flags。"""
        normalized_meta = dict(session_meta or {})
        normalized_flags = (
            runtime_flags.to_dict()
            if isinstance(runtime_flags, GameRuntimeFlags)
            else GameRuntimeFlags.from_payload(runtime_flags).to_dict()
        )
        normalized_meta["runtime_flags"] = normalized_flags
        return normalized_meta

    def _build_runtime_state(
        self,
        *,
        session: Any,
        current_round_no: int | None = None,
        current_scene_id: str | None = None,
        k_state: Dict[str, Any] | None = None,
        s_state: Dict[str, Any] | None = None,
        runtime_flags: Dict[str, Any] | GameRuntimeFlags | None = None,
    ) -> GameRuntimeState:
        """统一构建运行时状态，避免服务层散落重复聚合逻辑。"""
        return GameRuntimeState.from_session(
            session,
            round_no=current_round_no,
            current_scene_id=current_scene_id,
            k_state=k_state,
            s_state=s_state,
            player_profile=self._resolve_session_player_profile_payload(session),
            runtime_flags=(
                runtime_flags
                if runtime_flags is not None
                else self._resolve_session_runtime_flags(session)
            ),
        )

    def _get_session_or_raise(self, session_id: str) -> Any:
        session = self.training_store.get_training_session(session_id)
        if not session:
            raise ValueError(f"session not found: {session_id}")
        return session

    def _get_completed_scenario_ids(self, session_id: str) -> List[str]:
        """读取已完成回合的场景 ID 列表，供流转策略复用。"""
        return [row.scenario_id for row in self.training_store.get_training_rounds(session_id)]

    def _get_recent_risk_rounds(self, session_id: str) -> List[List[str]]:
        """读取最近回合的风险标记历史，供推荐策略识别重复错误。"""
        risk_rounds: List[List[str]] = []
        for evaluation_row in self.training_store.get_round_evaluations_by_session(session_id):
            payload = RoundEvaluationPayload.from_raw(getattr(evaluation_row, "raw_payload", None)).to_dict()
            risk_rounds.append([str(flag) for flag in payload.get("risk_flags", []) if str(flag or "").strip()])
        return risk_rounds

    def _extract_round_runtime_state(
        self,
        user_action: Dict[str, Any] | None,
    ) -> TrainingRuntimeStateOutput | None:
        """从回合 user_action 中恢复运行时状态。"""
        if not isinstance(user_action, dict):
            return None
        return self._build_training_runtime_state_output(user_action.get(USER_ACTION_RUNTIME_STATE_KEY))

    def _extract_round_runtime_flags(
        self,
        user_action: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        """从回合 user_action 中提取运行时 flags。"""
        runtime_state = self._extract_round_runtime_state(user_action)
        if runtime_state is None:
            return {}
        return runtime_state.to_dict().get("runtime_flags", {})

    def _extract_round_consequence_events(
        self,
        user_action: Dict[str, Any] | None,
    ) -> List[TrainingConsequenceEventOutput]:
        """从回合 user_action 中恢复后果事件列表。"""
        if not isinstance(user_action, dict):
            return []
        return self._build_training_consequence_event_outputs(
            user_action.get(USER_ACTION_CONSEQUENCE_EVENTS_KEY)
        )

    def _build_training_scenario_output(self, payload: Dict[str, Any] | None) -> TrainingScenarioOutput | None:
        """把原始场景字典转换成稳定场景 DTO。"""
        return TrainingScenarioOutput.from_payload(payload)

    def _build_training_player_profile_output(
        self,
        payload: Dict[str, Any] | None,
    ) -> TrainingPlayerProfileOutput | None:
        """把玩家档案字典转换成稳定输出 DTO。"""
        return TrainingPlayerProfileOutput.from_payload(payload)

    def _build_training_evaluation_output(self, payload: Dict[str, Any] | None) -> TrainingEvaluationOutput:
        """把原始评估字典转换成稳定评估 DTO。"""
        return TrainingEvaluationOutput.from_payload(payload)

    def _build_training_runtime_state_output(
        self,
        runtime_state: GameRuntimeState | Dict[str, Any] | None,
    ) -> TrainingRuntimeStateOutput | None:
        """把运行时状态转换成稳定输出 DTO。"""
        if runtime_state is None:
            return None
        payload = runtime_state.to_dict() if isinstance(runtime_state, GameRuntimeState) else runtime_state
        return TrainingRuntimeStateOutput.from_payload(payload)

    def _build_training_consequence_event_output(
        self,
        payload: RuntimeConsequenceEvent | Dict[str, Any] | None,
    ) -> TrainingConsequenceEventOutput | None:
        """把运行时后果事件转换成稳定输出 DTO。"""
        if payload is None:
            return None
        event_payload = payload.to_dict() if isinstance(payload, RuntimeConsequenceEvent) else payload
        return TrainingConsequenceEventOutput.from_payload(event_payload)

    def _build_training_consequence_event_outputs(
        self,
        payloads: List[RuntimeConsequenceEvent | Dict[str, Any]] | None,
    ) -> List[TrainingConsequenceEventOutput]:
        """批量转换运行时后果事件。"""
        outputs: List[TrainingConsequenceEventOutput] = []
        for item in payloads or []:
            output = self._build_training_consequence_event_output(item)
            if output is not None:
                outputs.append(output)
        return outputs

    def _build_training_kt_observation_output(self, row: Any) -> TrainingKtObservationOutput | None:
        """把 KT 观测记录转换成稳定输出 DTO。"""
        if row is None:
            return None
        return TrainingKtObservationOutput.from_payload(
            {
                "round_no": getattr(row, "round_no", None),
                "scenario_id": getattr(row, "scenario_id", None),
                "scenario_title": getattr(row, "scenario_title", ""),
                "training_mode": getattr(row, "training_mode", "guided"),
                "primary_skill_code": getattr(row, "primary_skill_code", None),
                "primary_risk_flag": getattr(row, "primary_risk_flag", None),
                "is_high_risk": getattr(row, "is_high_risk", False),
                "target_skills": getattr(row, "target_skills", []),
                "weak_skills_before": getattr(row, "weak_skills_before", []),
                "risk_flags": getattr(row, "risk_flags", []),
                "focus_tags": getattr(row, "focus_tags", []),
                "evidence": getattr(row, "evidence", []),
                "skill_observations": getattr(row, "skill_observations", []),
                "state_observations": getattr(row, "state_observations", []),
                "observation_summary": getattr(row, "observation_summary", ""),
            }
        )

    def _build_training_recommendation_log_output(self, row: Any) -> TrainingRecommendationLogOutput | None:
        """把推荐日志记录转换成稳定输出 DTO。"""
        if row is None:
            return None
        return TrainingRecommendationLogOutput.from_payload(
            {
                "round_no": getattr(row, "round_no", None),
                "training_mode": getattr(row, "training_mode", "guided"),
                "selection_source": getattr(row, "selection_source", None),
                "recommended_scenario_id": getattr(row, "recommended_scenario_id", None),
                "selected_scenario_id": getattr(row, "selected_scenario_id", None),
                "candidate_pool": getattr(row, "candidate_pool", []),
                "recommended_recommendation": getattr(row, "recommended_recommendation", {}),
                "selected_recommendation": getattr(row, "selected_recommendation", {}),
                "decision_context": getattr(row, "decision_context", {}),
            }
        )

    def _build_training_recommendation_log_outputs(
        self,
        rows: List[Any],
    ) -> List[TrainingRecommendationLogOutput]:
        """批量转换推荐日志，统一过滤空值，保持诊断主流程简洁。"""
        outputs: List[TrainingRecommendationLogOutput] = []
        for row in rows:
            output = self._build_training_recommendation_log_output(row)
            if output is not None:
                outputs.append(output)
        return outputs

    def _build_training_audit_event_output(self, row: Any) -> TrainingAuditEventOutput | None:
        """把审计事件记录转换成稳定输出 DTO。"""
        if row is None:
            return None
        return TrainingAuditEventOutput.from_payload(
            {
                "event_type": getattr(row, "event_type", None),
                "round_no": getattr(row, "round_no", None),
                "payload": getattr(row, "payload", {}),
                "timestamp": getattr(row, "created_at", None).isoformat() if getattr(row, "created_at", None) else None,
            }
        )

    def _build_training_audit_event_outputs(
        self,
        rows: List[Any],
    ) -> List[TrainingAuditEventOutput]:
        """批量转换审计事件，统一过滤空值，保持诊断主流程简洁。"""
        outputs: List[TrainingAuditEventOutput] = []
        for row in rows:
            output = self._build_training_audit_event_output(row)
            if output is not None:
                outputs.append(output)
        return outputs

    def _build_training_kt_observation_outputs(
        self,
        rows: List[Any],
    ) -> List[TrainingKtObservationOutput]:
        """批量转换 KT 观测，统一过滤空值，便于报告和诊断共用。"""
        outputs: List[TrainingKtObservationOutput] = []
        for row in rows:
            output = self._build_training_kt_observation_output(row)
            if output is not None:
                outputs.append(output)
        return outputs

    def _build_training_scenario_output_list(
        self,
        payloads: List[Dict[str, Any]] | None,
    ) -> List[TrainingScenarioOutput] | None:
        """批量转换候选场景列表，并自动过滤无效项。"""
        if payloads is None:
            return None

        outputs: List[TrainingScenarioOutput] = []
        for item in payloads:
            scenario_output = self._build_training_scenario_output(item)
            if scenario_output is not None:
                outputs.append(scenario_output)
        return outputs

    def _build_duplicate_submit_response(self, session_id: str, round_no: int) -> Dict[str, Any] | None:
        """从已落库数据构建幂等响应。"""
        round_row = self.training_store.get_training_round_by_session_round(session_id, round_no)
        if round_row is None:
            return None

        session = self._get_session_or_raise(session_id)
        session_sequence = self._resolve_session_scenario_sequence(session)
        evaluation_row = self.training_store.get_round_evaluation_by_round_id(round_row.round_id)
        ending_row = self.training_store.get_ending_result(session_id)

        evaluation_payload = (
            evaluation_row.raw_payload
            if evaluation_row and evaluation_row.raw_payload
            else {
                "llm_model": DEFAULT_EVAL_MODEL,
                "confidence": 0.5,
                "risk_flags": [],
                "skill_delta": {},
                "s_delta": {},
                "evidence": [self.runtime_config.messages.duplicate_fallback_evidence],
                "skill_scores_preview": {},
                "eval_mode": "duplicate_fallback",
            }
        )
        if evaluation_row is None or not evaluation_row.raw_payload:
            logger.warning(
                "duplicate idempotent path missing evaluation payload: session_id=%s round_no=%s round_id=%s",
                session_id,
                round_no,
                round_row.round_id,
            )

        normalized_eval = RoundEvaluationPayload.from_raw(evaluation_payload).to_dict()
        is_completed = self.flow_policy.is_terminal_state(
            round_no=round_no,
            session_sequence=session_sequence,
            session_status=session.status,
            has_ending=bool(ending_row),
        )

        return TrainingRoundSubmitOutput(
            session_id=session_id,
            round_no=round_row.round_no,
            evaluation=self._build_training_evaluation_output(normalized_eval),
            k_state=round_row.kt_after or self._normalize_k_state(session.k_state),
            s_state=round_row.state_after or self._normalize_s_state(session.s_state),
            player_profile=self._resolve_session_player_profile(session),
            runtime_state=self._extract_round_runtime_state(round_row.user_action),
            consequence_events=self._extract_round_consequence_events(round_row.user_action),
            is_completed=is_completed,
            ending=ending_row.report_payload if ending_row else None,
            decision_context=self._extract_round_decision_context(round_row.user_action),
        ).to_dict()

    def _build_round_user_action(
        self,
        user_input: str,
        selected_option: str | None,
        decision_context: TrainingRoundDecisionContextOutput | None,
    ) -> Dict[str, Any]:
        """统一封装回合提交时写入 user_action 的结构，减少服务层散落的契约键名。"""
        payload = {
            USER_ACTION_TEXT_KEY: user_input,
            USER_ACTION_SELECTED_OPTION_KEY: selected_option,
        }
        if decision_context is not None:
            payload[USER_ACTION_DECISION_CONTEXT_KEY] = decision_context.to_dict()
        return payload

    def _attach_runtime_artifacts_to_user_action(
        self,
        user_action: Dict[str, Any],
        runtime_state: GameRuntimeState,
        consequence_events: List[RuntimeConsequenceEvent],
        branch_hints: List[str] | None = None,
    ) -> Dict[str, Any]:
        """把运行时结果并入 user_action，便于历史回放与幂等重放。"""
        payload = dict(user_action or {})
        payload[USER_ACTION_RUNTIME_STATE_KEY] = runtime_state.to_dict()
        payload[USER_ACTION_CONSEQUENCE_EVENTS_KEY] = [item.to_dict() for item in consequence_events or []]
        if branch_hints:
            payload[USER_ACTION_BRANCH_HINTS_KEY] = [
                str(item) for item in branch_hints if str(item or "").strip()
            ]
        return payload

    def _build_recommendation_log_payload(
        self,
        training_mode: str,
        decision_context: TrainingRoundDecisionContextOutput | None,
    ) -> Dict[str, Any] | None:
        """把回合决策上下文转换成独立推荐日志，避免后续分析时反复解析 user_action。"""
        recommendation_log = self.telemetry_policy.build_recommendation_log(
            training_mode=training_mode,
            decision_context=decision_context,
        )
        return recommendation_log.to_dict() if recommendation_log is not None else None

    def _build_round_audit_event_payloads(
        self,
        training_mode: str,
        round_no: int,
        scenario_id: str,
        selected_option: str | None,
        eval_result: Dict[str, Any],
        decision_context: TrainingRoundDecisionContextOutput | None,
        current_phase_snapshot: TrainingPhaseSnapshot | None,
        previous_phase_snapshot: TrainingPhaseSnapshot | None,
        is_completed: bool,
        ending_payload: Dict[str, Any] | None,
    ) -> List[Dict[str, Any]]:
        """生成回合提交相关的审计事件，收口事件结构，避免 service 到处手写日志载荷。"""
        return [
            item.to_dict()
            for item in self.telemetry_policy.build_round_audit_events(
                training_mode=training_mode,
                round_no=round_no,
                scenario_id=scenario_id,
                selected_option=selected_option,
                evaluation_payload=eval_result,
                decision_context=decision_context,
                phase_snapshot=current_phase_snapshot,
                previous_phase_snapshot=previous_phase_snapshot,
                is_completed=is_completed,
                ending_payload=ending_payload,
            )
        ]

    def _build_runtime_consequence_audit_event_payloads(
        self,
        training_mode: str,
        round_no: int,
        runtime_flags: GameRuntimeFlags | Dict[str, Any],
        consequence_events: List[RuntimeConsequenceEvent],
        branch_hints: List[str] | None,
    ) -> List[Dict[str, Any]]:
        """生成运行时后果相关审计事件。"""
        return [
            item.to_dict()
            for item in self.telemetry_policy.build_runtime_consequence_audit_events(
                round_no=round_no,
                training_mode=training_mode,
                runtime_flags=runtime_flags,
                consequence_events=consequence_events,
                branch_hints=branch_hints,
            )
        ]

    def _resolve_previous_phase_snapshot(
        self,
        training_mode: str,
        round_no: int,
        total_rounds: int,
    ) -> TrainingPhaseSnapshot | None:
        """解析上一轮的阶段快照，供阶段切换审计事件使用。"""
        if int(round_no) <= 1:
            return None
        return self.phase_policy.resolve_round_phase(
            training_mode=training_mode,
            round_no=int(round_no) - 1,
            total_rounds=total_rounds,
        )

    def _build_kt_observation_payload(
        self,
        training_mode: str,
        round_no: int,
        scenario_payload: Dict[str, Any] | None,
        k_before: Dict[str, float],
        k_after: Dict[str, float],
        s_before: Dict[str, float],
        s_after: Dict[str, float],
        eval_result: Dict[str, Any],
    ) -> Dict[str, Any] | None:
        """把回合状态变化收口成 KT 结构化观测，供后续诊断与分析复用。"""
        observation = self.telemetry_policy.build_kt_observation(
            training_mode=training_mode,
            round_no=round_no,
            scenario_payload=scenario_payload,
            k_before=k_before,
            k_after=k_after,
            s_before=s_before,
            s_after=s_after,
            evaluation_payload=eval_result,
        )
        return observation.to_dict() if observation is not None else None

    def _extract_round_decision_context(
        self,
        user_action: Dict[str, Any] | None,
    ) -> TrainingRoundDecisionContextOutput | None:
        """从持久化的 user_action 中读取决策上下文，兼容历史数据缺失该字段的情况。"""
        if not isinstance(user_action, dict):
            return None
        return TrainingRoundDecisionContextOutput.from_payload(user_action.get(USER_ACTION_DECISION_CONTEXT_KEY))

    def _extract_round_branch_transition(
        self,
        user_action: Dict[str, Any] | None,
    ) -> Dict[str, Any] | None:
        """从回合决策上下文中提取已选分支跳转，供报告与诊断聚合复用。"""
        decision_context = self._extract_round_decision_context(user_action)
        if decision_context is None:
            return None
        branch_transition = getattr(decision_context, "selected_branch_transition", None)
        return branch_transition.to_dict() if branch_transition is not None else None

    def _build_round_decision_context(
        self,
        training_mode: str,
        submitted_scenario_id: str,
        next_scenario_bundle: Any,
    ) -> TrainingRoundDecisionContextOutput | None:
        """把本回合推荐结果转成稳定的“决策上下文”，供落库、响应和报告回放复用。"""
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
        """提取当前回合可见的场景候选集，供决策上下文序列化。"""
        candidate_source = getattr(next_scenario_bundle, "scenario_candidates", None)
        if candidate_source is None:
            candidate_source = [getattr(next_scenario_bundle, "scenario", None)]

        scenario_payloads: List[Dict[str, Any]] = []
        for item in candidate_source or []:
            if isinstance(item, dict) and str(item.get("id") or "").strip():
                scenario_payloads.append(dict(item))
        return scenario_payloads

    def _extract_recommended_scenario_payload(self, next_scenario_bundle: Any) -> Dict[str, Any] | None:
        """只有场景携带 recommendation 元信息时，才视为真正的推荐结果。"""
        scenario_payload = getattr(next_scenario_bundle, "scenario", None)
        if not isinstance(scenario_payload, dict):
            return None
        if not isinstance(scenario_payload.get("recommendation"), dict):
            return None
        return dict(scenario_payload)

    def _find_scenario_payload_by_id(
        self,
        scenario_payloads: List[Dict[str, Any]],
        scenario_id: str,
    ) -> Dict[str, Any] | None:
        """按场景 ID 在候选集中定位原始场景载荷，便于提取推荐元信息。"""
        for payload in scenario_payloads:
            if str(payload.get("id") or "").strip() == str(scenario_id or "").strip():
                return dict(payload)
        return None

    def _extract_recommendation_payload(
        self,
        scenario_payload: Dict[str, Any] | None,
    ) -> Dict[str, Any] | None:
        """从场景载荷中抽取推荐元信息，避免上下文里嵌入整份场景数据。"""
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
        """提取场景附带的分支跳转上下文，供日志、诊断和报告复用。"""
        if not isinstance(scenario_payload, dict):
            return None
        branch_transition = scenario_payload.get("branch_transition")
        if not isinstance(branch_transition, dict):
            return None
        return dict(branch_transition)

    def _build_decision_candidate_payloads(
        self,
        scenario_payloads: List[Dict[str, Any]],
        selected_scenario_id: str,
        recommended_scenario_id: str | None,
    ) -> List[Dict[str, Any]]:
        """把完整场景载荷收敛成适合回放展示的候选题摘要。"""
        candidate_outputs: List[Dict[str, Any]] = []
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
                    "is_selected": scenario_id == str(selected_scenario_id or "").strip(),
                    "is_recommended": scenario_id == str(recommended_scenario_id or "").strip(),
                }
            )
            if candidate_output is not None:
                candidate_outputs.append(candidate_output.to_dict())
        return candidate_outputs

    def _resolve_selection_source(
        self,
        training_mode: str,
        submitted_scenario_id: str,
        recommended_scenario_id: str | None,
        scenario_payloads: List[Dict[str, Any]],
        selected_scenario_payload: Dict[str, Any] | None = None,
    ) -> str:
        """标记本回合场景是按固定顺序、顶级推荐还是候选池选择出来的。"""
        normalized_mode = self.mode_catalog.normalize(
            training_mode,
            default="guided",
            raise_on_unknown=False,
        ) or "guided"
        submitted_scenario_id = str(submitted_scenario_id or "").strip()

        # 分支跳转是独立来源，不能继续被记成普通主线顺序提交。
        if isinstance(selected_scenario_payload, dict) and isinstance(selected_scenario_payload.get("branch_transition"), dict):
            return SELECTION_SOURCE_BRANCH_TRANSITION

        if recommended_scenario_id:
            if submitted_scenario_id == recommended_scenario_id:
                return SELECTION_SOURCE_TOP_RECOMMENDATION

            candidate_ids = {
                str(payload.get("id") or "").strip()
                for payload in scenario_payloads
                if isinstance(payload, dict)
            }
            if submitted_scenario_id in candidate_ids:
                return SELECTION_SOURCE_CANDIDATE_POOL
            return SELECTION_SOURCE_FALLBACK_SEQUENCE

        if self.recommendation_policy.supports_mode(normalized_mode):
            return SELECTION_SOURCE_FALLBACK_SEQUENCE
        return SELECTION_SOURCE_ORDERED_SEQUENCE

    def _normalize_k_state(self, k_state: Dict[str, float] | None) -> Dict[str, float]:
        source = k_state or {}
        return {
            code: round(_clamp(float(source.get(code, DEFAULT_K_STATE[code]))), 4)
            for code in SKILL_CODES
        }

    def _normalize_session_training_mode(self, session: Any) -> str:
        """优先信任已入库模式，但对历史脏数据做兜底规范化。"""
        return self.mode_catalog.normalize(
            getattr(session, "training_mode", "guided"),
            default="guided",
            raise_on_unknown=False,
        ) or "guided"

    def _normalize_s_state(self, s_state: Dict[str, float] | None) -> Dict[str, float]:
        source = s_state or {}
        return {
            key: round(_clamp(float(source.get(key, DEFAULT_S_STATE[key]))), 4)
            for key in DEFAULT_S_STATE.keys()
        }

    def _update_k(self, k_state: Dict[str, float], skill_delta: Dict[str, float]) -> Dict[str, float]:
        updated: Dict[str, float] = {}
        for code in SKILL_CODES:
            updated[code] = round(
                _clamp(float(k_state.get(code, DEFAULT_K_STATE[code])) + float(skill_delta.get(code, 0.0))),
                4,
            )
        return updated

    def _update_s(self, s_state: Dict[str, float], s_delta: Dict[str, float]) -> Dict[str, float]:
        updated: Dict[str, float] = {}
        for key in DEFAULT_S_STATE.keys():
            updated[key] = round(
                _clamp(float(s_state.get(key, DEFAULT_S_STATE[key])) + float(s_delta.get(key, 0.0))),
                4,
            )
        return updated

    def _resolve_ending(self, k: Dict[str, float], s: Dict[str, float], evaluation_rows: List[Any]) -> Dict[str, Any]:
        # 保留兼容包装方法，实际规则由 EndingPolicy 承担。
        return self.ending_policy.resolve(k_state=k, s_state=s, evaluation_rows=evaluation_rows)
