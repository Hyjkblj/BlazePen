"""训练服务（P2）：负责流程编排、状态更新与持久化调用。"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from threading import Lock
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Dict, List

from training.constants import DEFAULT_EVAL_MODEL, DEFAULT_K_STATE, DEFAULT_S_STATE, SKILL_CODES, TRAINING_RUNTIME_CONFIG
from training.consequence_engine import ConsequenceEngine
from training.contracts import RoundEvaluationPayload
from training.decision_context_policy import TrainingDecisionContextPolicy
from training.ending_policy import EndingPolicy
from training.evaluator import TrainingRoundEvaluator
from training.exceptions import (
    DuplicateRoundSubmissionError,
    TrainingScenarioMismatchError,
    TrainingSessionCompletedError,
    TrainingSessionNotFoundError,
    TrainingSessionRecoveryStateError,
)
from training.output_assembler_policy import TrainingOutputAssemblerPolicy
from training.phase_policy import TrainingPhasePolicy, TrainingPhaseSnapshot
from training.report_context_policy import TrainingReportContextPolicy
from training.recommendation_policy import RecommendationPolicy
from training.recommendation_agent import RecommendationAgent
from training.director_agent import ExecutionPlan, TrainingDirectorAgent
from training.reporting_policy import TrainingReportingPolicy
from training.round_transition_policy import TrainingRoundTransitionPolicy
from training.round_flow_policy import TrainingRoundFlowPolicy
from training.runtime_artifact_policy import TrainingRuntimeArtifactPolicy
from training.runtime_events import RuntimeConsequenceEvent
from training.runtime_state import GameRuntimeFlags, GameRuntimeState
from training.media_task_policy import TrainingMediaTaskPolicy
from training.scenario_policy import ScenarioPolicy
from training.session_snapshot_policy import SessionScenarioSnapshotPolicy
from training.session_storyline_policy import SessionStorylinePolicy
from training.training_outputs import (
    TrainingAuditEventOutput,
    TrainingConsequenceEventOutput,
    TrainingDiagnosticsOutput,
    TrainingEvaluationOutput,
    TrainingInitOutput,
    TrainingKtObservationOutput,
    TrainingNextScenarioOutput,
    TrainingPlayerProfileOutput,
    TrainingRecommendationLogOutput,
    TrainingReportHistoryItemOutput,
    TrainingReportOutput,
    TrainingRuntimeStateOutput,
    TrainingRoundDecisionContextOutput,
    TrainingRoundMediaTaskSummaryOutput,
    TrainingRoundSubmitOutput,
    TrainingScenarioOutput,
    TrainingSessionProgressAnchorOutput,
    calculate_progress_percent,
)
from training.scenario_repository import ScenarioRepository
from training.telemetry_policy import TrainingTelemetryPolicy
from training.training_mode import TrainingModeCatalog
from training.training_store import DatabaseTrainingStore, TrainingMediaTaskRecord, TrainingStoreProtocol
from utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from training.training_query_service import TrainingQueryService


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _normalize_character_id(value: Any) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized > 0 else None


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

    @staticmethod
    def _resolve_injected_policy_dependency(
        *,
        owner_name: str,
        policy: Any,
        attribute_name: str,
    ) -> Any:
        if not hasattr(policy, attribute_name):
            raise ValueError(
                f"{owner_name} must expose .{attribute_name} to keep the training runtime contract consistent"
            )

        dependency = getattr(policy, attribute_name)
        if dependency is None:
            raise ValueError(
                f"{owner_name}.{attribute_name} must not be None when injecting training policies"
            )
        return dependency

    @staticmethod
    def _resolve_injected_policy_contract(
        *,
        contract_name: str,
        candidates: List[tuple[str, Any | None]],
    ) -> Any | None:
        resolved_source = None
        resolved_policy = None
        for source_name, policy in candidates:
            if policy is None:
                continue
            if resolved_policy is None:
                resolved_source = source_name
                resolved_policy = policy
                continue
            if policy is not resolved_policy:
                raise ValueError(
                    f"inconsistent {contract_name} injection: "
                    f"{resolved_source} and {source_name} must share the same instance"
                )
        return resolved_policy

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
        decision_context_policy: TrainingDecisionContextPolicy | None = None,
        runtime_artifact_policy: TrainingRuntimeArtifactPolicy | None = None,
        round_transition_policy: TrainingRoundTransitionPolicy | None = None,
        output_assembler_policy: TrainingOutputAssemblerPolicy | None = None,
        report_context_policy: TrainingReportContextPolicy | None = None,
        media_task_policy: TrainingMediaTaskPolicy | None = None,
        session_storyline_policy: SessionStorylinePolicy | None = None,
        runtime_config: Any = None,
        query_service: "TrainingQueryService | None" = None,
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
        self.recommendation_policy = recommendation_policy or RecommendationAgent(
            runtime_config=self.runtime_config,
            phase_policy=self.phase_policy,
        )
        # 报告与诊断聚合统一下沉到独立 policy，避免 TrainingService 再次膨胀。
        self.reporting_policy = reporting_policy or TrainingReportingPolicy(runtime_config=self.runtime_config)
        # 观测与审计组装统一下沉到 telemetry policy，避免 service 内继续散落结构化日志细节。
        self.telemetry_policy = telemetry_policy or TrainingTelemetryPolicy(phase_policy=self.phase_policy)
        # 运行时后果由独立引擎负责，服务层只做编排与持久化。
        self.consequence_engine = consequence_engine or ConsequenceEngine()
        # Director Agent：在每轮提交前生成执行计划，预留 LLM 决策接口。
        self.director_agent = TrainingDirectorAgent(runtime_config=self.runtime_config)
        # Optional async dispatch hook (injected by API wiring).
        # Kept as a runtime attribute to avoid hard dependency cycles.
        self.media_task_executor = None

        default_scenario_sequence = self._build_default_scenario_sequence(self.runtime_config)
        self._scenario_sequence = list(scenario_sequence or default_scenario_sequence)
        self.scenario_policy = scenario_policy or ScenarioPolicy(
            default_sequence=self._scenario_sequence,
            scenario_version=self.runtime_config.scenario.version,
            runtime_config=self.runtime_config,
        )
        # 会话剧本策略：在初始化时可按需扩展为「大场景 + 小场景」连续线路，
        # 且小场景与大场景一样参与完整回合测评。
        self.session_storyline_policy = session_storyline_policy or SessionStorylinePolicy(
            scenario_repository=self.scenario_repository,
        )
        # 会话快照策略独立抽离，便于后续继续演进老会话回填、快照诊断和分支冻结逻辑。
        self.session_snapshot_policy = session_snapshot_policy or SessionScenarioSnapshotPolicy(
            scenario_policy=self.scenario_policy,
            scenario_repository=self.scenario_repository,
        )
        # 回合决策上下文装配独立下沉，避免服务层继续堆积推荐/分支来源判定细节。
        self.decision_context_policy = decision_context_policy or TrainingDecisionContextPolicy(
            recommendation_policy=self.recommendation_policy,
            mode_catalog=self.mode_catalog,
            runtime_config=self.runtime_config,
        )
        # 运行时状态与回合工件的组装单独下沉，继续降低 service 对 user_action 契约的耦合。
        self.runtime_artifact_policy = runtime_artifact_policy or TrainingRuntimeArtifactPolicy()
        # 单回合状态推进链路单独下沉，避免 submit_round 同时承载评估、状态演化和 user_action 回写。
        self.round_transition_policy = round_transition_policy or TrainingRoundTransitionPolicy(
            runtime_artifact_policy=self.runtime_artifact_policy,
        )
        # 输出 DTO 装配统一下沉，避免服务层继续持有大段 payload -> DTO 转换逻辑。
        self.output_assembler_policy = output_assembler_policy or TrainingOutputAssemblerPolicy()
        # 报告回放上下文装配独立下沉，避免 service 再持有大段 history/snapshot 组装逻辑。
        self.report_context_policy = report_context_policy or TrainingReportContextPolicy(
            runtime_artifact_policy=self.runtime_artifact_policy,
            output_assembler_policy=self.output_assembler_policy,
        )
        self.media_task_policy = media_task_policy or TrainingMediaTaskPolicy()
        resolved_round_runtime_artifact_policy = (
            self._resolve_injected_policy_dependency(
                owner_name="round_transition_policy",
                policy=round_transition_policy,
                attribute_name="runtime_artifact_policy",
            )
            if round_transition_policy is not None
            else None
        )
        resolved_report_runtime_artifact_policy = (
            self._resolve_injected_policy_dependency(
                owner_name="report_context_policy",
                policy=report_context_policy,
                attribute_name="runtime_artifact_policy",
            )
            if report_context_policy is not None
            else None
        )
        resolved_report_output_assembler_policy = (
            self._resolve_injected_policy_dependency(
                owner_name="report_context_policy",
                policy=report_context_policy,
                attribute_name="output_assembler_policy",
            )
            if report_context_policy is not None
            else None
        )

        self.runtime_artifact_policy = self._resolve_injected_policy_contract(
            contract_name="runtime_artifact_policy",
            candidates=[
                ("runtime_artifact_policy", runtime_artifact_policy),
                ("round_transition_policy.runtime_artifact_policy", resolved_round_runtime_artifact_policy),
                ("report_context_policy.runtime_artifact_policy", resolved_report_runtime_artifact_policy),
            ],
        ) or self.runtime_artifact_policy
        self.output_assembler_policy = self._resolve_injected_policy_contract(
            contract_name="output_assembler_policy",
            candidates=[
                ("output_assembler_policy", output_assembler_policy),
                ("report_context_policy.output_assembler_policy", resolved_report_output_assembler_policy),
            ],
        ) or self.output_assembler_policy

        if getattr(self.round_transition_policy, "runtime_artifact_policy", None) is not self.runtime_artifact_policy:
            self.round_transition_policy.runtime_artifact_policy = self.runtime_artifact_policy
        if getattr(self.report_context_policy, "runtime_artifact_policy", None) is not self.runtime_artifact_policy:
            self.report_context_policy.runtime_artifact_policy = self.runtime_artifact_policy
        if getattr(self.report_context_policy, "output_assembler_policy", None) is not self.output_assembler_policy:
            self.report_context_policy.output_assembler_policy = self.output_assembler_policy

        self.flow_policy = flow_policy or TrainingRoundFlowPolicy(
            scenario_policy=self.scenario_policy,
            recommendation_policy=self.recommendation_policy,
            runtime_config=self.runtime_config,
        )
        self.ending_policy = ending_policy or EndingPolicy(runtime_config=self.runtime_config)
        if query_service is not None:
            self.query_service = query_service
        else:
            from training.training_query_service import TrainingQueryService

            self.query_service = TrainingQueryService.from_runtime(self)

    def _build_init_session_sequence(
        self,
        *,
        training_mode: str,
        player_profile: Dict[str, Any] | None,
        storyline_seed: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Resolve init-time session sequence with optional storyline expansion."""
        base_sequence = self.scenario_policy.get_default_sequence()
        try:
            expanded_sequence = self.session_storyline_policy.build_session_sequence(
                training_mode=training_mode,
                base_sequence=base_sequence,
                player_profile=player_profile,
                storyline_seed=storyline_seed,
            )
        except Exception as exc:
            logger.warning(
                "build init session sequence failed, fallback to default sequence: mode=%s error=%s",
                training_mode,
                str(exc),
            )
            return list(base_sequence)

        return list(expanded_sequence or base_sequence)

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
            # Persist a deterministic storyline seed as a session fact source.
            # Never derive from uuid4 during recovery paths.
            resolved_seed = ""
            if isinstance(player_profile, dict):
                resolved_seed = str(
                    (player_profile.get("script_seed") or player_profile.get("storyline_seed") or "")
                ).strip()
            if not resolved_seed:
                resolved_seed = uuid4().hex

            session_sequence = self._build_init_session_sequence(
                training_mode=normalized_mode,
                player_profile=player_profile,
                storyline_seed=resolved_seed,
            )
            # 在会话创建时同时冻结主线快照和可达分支目录，避免后续发版导致老会话内容漂移。
            snapshot_bundle = self.session_snapshot_policy.freeze_session_snapshots(
                session_sequence
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
            session_meta["script_seed"] = resolved_seed
            session_meta["storyline_seed"] = resolved_seed
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
            character_id=_normalize_character_id(getattr(row, "character_id", None)),
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
            scenario_sequence=list(sequence),
        ).to_dict()

    def bind_session_character(self, session_id: str, character_id: int) -> Dict[str, Any]:
        """Bind a training session created without character_id to a concrete character row."""
        normalized_session_id = str(session_id or "").strip()
        if not normalized_session_id:
            raise TrainingSessionNotFoundError(session_id=str(session_id))
        try:
            cid = int(character_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("character_id must be a positive integer") from exc
        if cid < 1:
            raise ValueError("character_id must be a positive integer")
        session = self.training_store.get_training_session(normalized_session_id)
        if session is None:
            raise TrainingSessionNotFoundError(session_id=normalized_session_id)
        if getattr(session, "status", None) == "completed":
            raise TrainingSessionCompletedError(session_id=normalized_session_id)
        self.training_store.update_training_session(
            normalized_session_id,
            {"character_id": cid},
        )
        return {"session_id": normalized_session_id, "character_id": cid}

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

        session, _, next_scenario_bundle = self._build_session_resume_bundle(session_id=session_id, session=session)
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
        media_tasks: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """提交单回合，并原子化保存本回合所有工件。"""
        session = self._get_session_or_raise(session_id)
        if session.status == "completed":
            raise TrainingSessionCompletedError(session_id=session_id)

        snapshot_bundle = self.session_snapshot_policy.require_session_snapshots(
            session_id=session_id,
            session=session,
        )
        scenario_payload_sequence = snapshot_bundle.scenario_payload_sequence
        scenario_payload_catalog = snapshot_bundle.scenario_payload_catalog
        session_sequence = self._read_persisted_session_sequence_or_raise(
            session_id=session_id,
            session=session,
        )
        training_mode = self._normalize_session_training_mode(session)
        completed_scenario_ids = self._get_completed_scenario_ids(session_id)
        k_before = self._normalize_k_state(session.k_state)
        s_before = self._normalize_s_state(session.s_state)
        recent_risk_rounds = self._get_recent_risk_rounds(session_id)
        round_no = session.current_round_no + 1
        normalized_media_task_specs = self._normalize_submit_round_media_tasks(
            session_id=session_id,
            round_no=round_no,
            media_tasks=media_tasks,
        )

        # ---- Director Agent 执行计划 ----
        runtime_flags = self._resolve_session_runtime_flags(session)
        try:
            execution_plan = self.director_agent.plan(
                session=session,
                round_no=round_no,
                k_state=k_before,
                s_state=s_before,
                recent_risk_rounds=recent_risk_rounds,
                runtime_flags=runtime_flags,
            )
            if execution_plan.needs_script_refresh:
                logger.info(
                    "director_agent: needs_script_refresh=True session_id=%s round_no=%s",
                    session_id, round_no,
                )
            if execution_plan.force_low_risk_scenario:
                logger.info(
                    "director_agent: force_low_risk_scenario=True session_id=%s round_no=%s",
                    session_id, round_no,
                )
        except Exception as exc:
            logger.warning("director_agent.plan failed, using default plan: %s", exc)
            execution_plan = ExecutionPlan()
        # ---- 结束 Director Agent ----

        # 先基于当前上下文生成推荐结果，确保“前端看到的候选集”和“提交时回放的决策上下文”来自同一份数据。
        try:
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
                runtime_flags=runtime_flags,
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
                runtime_flags=runtime_flags,
                current_scenario_id=getattr(session, "current_scenario_id", None),
            )
        except TrainingScenarioMismatchError:
            raise
        except ValueError as exc:
            raise TrainingSessionRecoveryStateError(
                session_id=session_id,
                reason="scenario_flow_unavailable",
                details={
                    "phase": "submit_validation",
                    "flow_error": str(exc),
                },
            ) from exc
        decision_context = self._build_round_decision_context(
            training_mode=training_mode,
            submitted_scenario_id=scenario_id,
            next_scenario_bundle=next_scenario_bundle,
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
        recent_history = self._build_recent_history(session_id=session_id, round_no=round_no)
        transition_artifacts = self.round_transition_policy.build_round_transition_artifacts(
            session=session,
            evaluator=self.evaluator,
            consequence_engine=self.consequence_engine,
            round_no=round_no,
            scenario_id=scenario_id,
            user_input=user_input,
            selected_option=selected_option,
            decision_context=decision_context,
            k_before=k_before,
            s_before=s_before,
            recent_risk_rounds=recent_risk_rounds,
            scenario_payload=selected_scenario_payload,
            recent_history=recent_history,
        )
        eval_result = transition_artifacts.evaluation_payload
        updated_k = transition_artifacts.updated_k_state
        updated_s = transition_artifacts.updated_s_state
        runtime_state = transition_artifacts.runtime_state
        consequence_result = transition_artifacts.consequence_result
        updated_session_meta = transition_artifacts.updated_session_meta
        user_action = transition_artifacts.user_action

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
                media_task_specs=normalized_media_task_specs,
            )
        except DuplicateRoundSubmissionError:
            # 并发重试命中唯一约束时，优先返回已落库结果，实现幂等体验。
            existing = self._build_duplicate_submit_response(
                session_id=session_id,
                round_no=round_no,
                include_media_tasks=bool(normalized_media_task_specs),
            )
            if existing is not None:
                logger.info(
                    "duplicate round submission idempotent hit: session_id=%s round_no=%s",
                    session_id,
                    round_no,
                )
                return existing
            raise DuplicateRoundSubmissionError(session_id=session_id, round_no=round_no)

        round_media_tasks = (
            self._list_round_media_tasks(session_id=session_id, round_no=round_no)
            if normalized_media_task_specs
            else []
        )

        if round_media_tasks and self.media_task_executor is not None:
            for task in round_media_tasks:
                task_id = str(getattr(task, "task_id", "") or "").strip()
                status = str(getattr(task, "status", "") or "").strip().lower()
                if not task_id or status not in {"pending", "running"}:
                    continue
                try:
                    self.media_task_executor.submit_task(task_id)
                except Exception as exc:
                    logger.warning(
                        "training media task dispatch failed in service: task_id=%s session_id=%s round_no=%s error=%s",
                        task_id,
                        session_id,
                        round_no,
                        str(exc),
                    )
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
            media_tasks=self._build_round_media_task_summary_outputs(round_media_tasks),
            is_completed=is_completed,
            ending=ending_payload,
            decision_context=decision_context,
        ).to_dict()

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Transitional compatibility wrapper for the training query service."""
        return self.query_service.get_session_summary(session_id)

    def get_progress(self, session_id: str) -> Dict[str, Any]:
        """获取训练进度。"""
        return self.query_service.get_progress(session_id)

    def get_history(self, session_id: str) -> Dict[str, Any]:
        """Transitional compatibility wrapper for the training query service."""
        return self.query_service.get_history(session_id)

    def get_report(self, session_id: str) -> Dict[str, Any]:
        """Transitional compatibility wrapper for the training query service."""
        return self.query_service.get_report(session_id)

    def get_diagnostics(self, session_id: str) -> Dict[str, Any]:
        """Transitional compatibility wrapper for the training query service."""
        return self.query_service.get_diagnostics(session_id)

    # Transitional compatibility only:
    # keep the legacy read-model builders private while local scripts migrate to
    # the canonical query service entrypoints. Router and service public methods
    # must continue to read through `TrainingQueryService`.
    def _legacy_get_report(self, session_id: str) -> Dict[str, Any]:
        """获取报告（含历史回放与最终状态）。"""
        session = self._get_session_or_raise(session_id)
        rounds = self.training_store.get_training_rounds(session_id)
        evaluations = self.training_store.get_round_evaluations_by_session(session_id)
        kt_observations = self.training_store.get_kt_observations(session_id)
        snapshot_bundle = self.session_snapshot_policy.require_session_snapshots(
            session_id=session_id,
            session=session,
        )
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
            round_snapshots=round_snapshots,
            history=history,
        ).to_dict()

    def _legacy_get_diagnostics(self, session_id: str) -> Dict[str, Any]:
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

    def _ensure_session_snapshot_state(
        self,
        session_id: str,
        session: Any,
    ) -> tuple[Any, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Load persisted snapshot-backed scenario payloads without mutating storage."""
        snapshot_bundle = self.session_snapshot_policy.require_session_snapshots(
            session_id=session_id,
            session=session,
        )
        return (
            session,
            snapshot_bundle.scenario_payload_sequence,
            snapshot_bundle.scenario_payload_catalog,
        )

    def _build_session_resume_bundle(
        self,
        *,
        session_id: str,
        session: Any,
    ) -> tuple[Any, List[Dict[str, str]], Any]:
        """Build the resumable scenario bundle from the session fact source."""
        session, scenario_payload_sequence, scenario_payload_catalog = self._ensure_session_snapshot_state(
            session_id=session_id,
            session=session,
        )
        session_sequence = self._read_persisted_session_sequence_or_raise(
            session_id=session_id,
            session=session,
        )

        try:
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
        except ValueError as exc:
            raise TrainingSessionRecoveryStateError(
                session_id=session_id,
                reason="scenario_flow_unavailable",
                details={
                    "phase": "resume_bundle",
                    "flow_error": str(exc),
                },
            ) from exc
        return session, session_sequence, next_scenario_bundle

    def _build_training_session_progress_anchor(
        self,
        *,
        current_round_no: int,
        total_rounds: int,
        is_completed: bool,
    ) -> TrainingSessionProgressAnchorOutput:
        """Build a stable progress anchor for recovery and resume flows."""
        completed_rounds = max(int(current_round_no), 0)
        normalized_total_rounds = max(int(total_rounds), 0)
        remaining_rounds = max(normalized_total_rounds - completed_rounds, 0)
        next_round_no = None if is_completed or remaining_rounds == 0 else completed_rounds + 1
        return TrainingSessionProgressAnchorOutput(
            current_round_no=completed_rounds,
            total_rounds=normalized_total_rounds,
            completed_rounds=completed_rounds,
            remaining_rounds=remaining_rounds,
            progress_percent=calculate_progress_percent(
                completed_rounds=completed_rounds,
                total_rounds=normalized_total_rounds,
            ),
            next_round_no=next_round_no,
        )

    @staticmethod
    def _serialize_optional_datetime(value: datetime | None) -> str | None:
        """Serialize optional datetimes into ISO-8601 strings for DTO output."""
        return value.isoformat() if value is not None else None

    def _resolve_report_initial_states(
        self,
        session: Any,
        rounds: List[Any],
    ) -> tuple[Dict[str, float], Dict[str, float]]:
        """委托报告上下文策略解析报告起点状态。"""
        return self.report_context_policy.resolve_report_initial_states(
            session=session,
            rounds=rounds,
        )

    def _build_training_report_history(
        self,
        rounds: List[Any],
        eval_map: Dict[str, Any],
        kt_observation_map: Dict[int, Any],
    ) -> List[TrainingReportHistoryItemOutput]:
        """委托报告上下文策略构建训练报告回放历史。"""
        return self.report_context_policy.build_report_history(
            rounds=rounds,
            eval_map=eval_map,
            kt_observation_map=kt_observation_map,
        )

    def _build_report_scenario_title_map(
        self,
        scenario_payload_sequence: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """委托报告上下文策略构建场景标题索引。"""
        return self.report_context_policy.build_report_scenario_title_map(scenario_payload_sequence)

    def _build_training_report_round_snapshots(
        self,
        rounds: List[Any],
        eval_map: Dict[str, Any],
        kt_observation_map: Dict[int, Any],
        scenario_title_map: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """委托报告上下文策略构建 round_snapshots。"""
        return self.report_context_policy.build_report_round_snapshots(
            rounds=rounds,
            eval_map=eval_map,
            kt_observation_map=kt_observation_map,
            scenario_title_map=scenario_title_map,
        )

    def _read_persisted_session_sequence_or_raise(
        self,
        *,
        session_id: str,
        session: Any,
    ) -> List[Dict[str, str]]:
        session_sequence = self.scenario_policy.read_persisted_session_sequence(session)
        if session_sequence:
            return session_sequence
        raise TrainingSessionRecoveryStateError(
            session_id=session_id,
            reason="scenario_sequence_empty",
            details={
                "current_round_no": int(getattr(session, "current_round_no", 0) or 0),
            },
        )

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
        """委托运行时工件策略构建默认 flags。"""
        return self.runtime_artifact_policy.build_default_runtime_flags()

    def _resolve_session_runtime_flags(
        self,
        session: Any,
    ) -> Dict[str, bool]:
        """委托运行时工件策略读取会话 runtime_flags。"""
        return self.runtime_artifact_policy.resolve_session_runtime_flags(session)

    def _merge_session_meta_runtime_flags(
        self,
        session_meta: Dict[str, Any] | None,
        runtime_flags: Dict[str, Any] | GameRuntimeFlags | None,
    ) -> Dict[str, Any]:
        """委托运行时工件策略合并 session_meta 与 runtime_flags。"""
        return self.runtime_artifact_policy.merge_session_meta_runtime_flags(
            session_meta=session_meta,
            runtime_flags=runtime_flags,
        )

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
        """委托运行时工件策略构建统一运行时状态。"""
        return self.runtime_artifact_policy.build_runtime_state(
            session=session,
            player_profile=self._resolve_session_player_profile_payload(session),
            current_round_no=current_round_no,
            current_scene_id=current_scene_id,
            k_state=k_state,
            s_state=s_state,
            runtime_flags=runtime_flags,
        )

    def _get_session_or_raise(self, session_id: str) -> Any:
        session = self.training_store.get_training_session(session_id)
        if not session:
            raise TrainingSessionNotFoundError(session_id=session_id)
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

    def _build_recent_history(
        self,
        session_id: str,
        round_no: int,
        window: int = 3,
    ) -> List[Dict[str, Any]]:
        """从已落库的历史回合中提取最近 window 轮的评估摘要。"""
        if round_no < 3:
            return []
        try:
            rows = list(self.training_store.get_round_evaluations_by_session(session_id))
            recent = rows[-window:]
            result = []
            for row in recent:
                eval_payload = getattr(row, "evaluation_payload", None) or {}
                if not isinstance(eval_payload, dict):
                    eval_payload = {}
                result.append({
                    "round_no": getattr(row, "round_no", None),
                    "scenario_id": getattr(row, "scenario_id", None),
                    "risk_flags": eval_payload.get("risk_flags", []),
                    "evidence": eval_payload.get("evidence", [])[:2],
                })
            return result
        except Exception as exc:
            logger.warning("_build_recent_history failed: %s", exc)
            return []

    def _extract_round_runtime_state(
        self,
        user_action: Dict[str, Any] | None,
    ) -> TrainingRuntimeStateOutput | None:
        """委托运行时工件策略恢复回合运行时状态。"""
        return self.runtime_artifact_policy.extract_round_runtime_state(user_action)

    def _extract_round_runtime_flags(
        self,
        user_action: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        """委托运行时工件策略提取回合 runtime_flags。"""
        return self.runtime_artifact_policy.extract_round_runtime_flags(user_action)

    def _extract_round_consequence_events(
        self,
        user_action: Dict[str, Any] | None,
    ) -> List[TrainingConsequenceEventOutput]:
        """委托运行时工件策略恢复回合后果事件。"""
        return self.runtime_artifact_policy.extract_round_consequence_events(user_action)

    def _build_training_scenario_output(self, payload: Dict[str, Any] | None) -> TrainingScenarioOutput | None:
        """委托输出装配策略转换场景 DTO。"""
        return self.output_assembler_policy.build_scenario_output(payload)

    def _build_training_player_profile_output(
        self,
        payload: Dict[str, Any] | None,
    ) -> TrainingPlayerProfileOutput | None:
        """委托输出装配策略转换玩家档案 DTO。"""
        return self.output_assembler_policy.build_player_profile_output(payload)

    def _build_training_evaluation_output(self, payload: Dict[str, Any] | None) -> TrainingEvaluationOutput:
        """委托输出装配策略转换评估 DTO。"""
        return self.output_assembler_policy.build_evaluation_output(payload)

    def _build_training_runtime_state_output(
        self,
        runtime_state: GameRuntimeState | Dict[str, Any] | None,
    ) -> TrainingRuntimeStateOutput | None:
        """委托输出装配策略转换运行时状态 DTO。"""
        return self.output_assembler_policy.build_runtime_state_output(runtime_state)

    def _build_training_consequence_event_output(
        self,
        payload: RuntimeConsequenceEvent | Dict[str, Any] | None,
    ) -> TrainingConsequenceEventOutput | None:
        """委托输出装配策略转换单个后果事件 DTO。"""
        return self.output_assembler_policy.build_consequence_event_output(payload)

    def _build_training_consequence_event_outputs(
        self,
        payloads: List[RuntimeConsequenceEvent | Dict[str, Any]] | None,
    ) -> List[TrainingConsequenceEventOutput]:
        """委托输出装配策略批量转换后果事件 DTO。"""
        return self.output_assembler_policy.build_consequence_event_outputs(payloads)

    def _build_training_kt_observation_output(self, row: Any) -> TrainingKtObservationOutput | None:
        """委托输出装配策略转换 KT 观测 DTO。"""
        return self.output_assembler_policy.build_kt_observation_output(row)

    def _build_training_recommendation_log_output(self, row: Any) -> TrainingRecommendationLogOutput | None:
        """委托输出装配策略转换推荐日志 DTO。"""
        return self.output_assembler_policy.build_recommendation_log_output(row)

    def _build_training_recommendation_log_outputs(
        self,
        rows: List[Any],
    ) -> List[TrainingRecommendationLogOutput]:
        """委托输出装配策略批量转换推荐日志 DTO。"""
        return self.output_assembler_policy.build_recommendation_log_outputs(rows)

    def _build_training_audit_event_output(self, row: Any) -> TrainingAuditEventOutput | None:
        """委托输出装配策略转换审计事件 DTO。"""
        return self.output_assembler_policy.build_audit_event_output(row)

    def _build_training_audit_event_outputs(
        self,
        rows: List[Any],
    ) -> List[TrainingAuditEventOutput]:
        """委托输出装配策略批量转换审计事件 DTO。"""
        return self.output_assembler_policy.build_audit_event_outputs(rows)

    def _build_training_kt_observation_outputs(
        self,
        rows: List[Any],
    ) -> List[TrainingKtObservationOutput]:
        """委托输出装配策略批量转换 KT 观测 DTO。"""
        return self.output_assembler_policy.build_kt_observation_outputs(rows)

    def _build_training_scenario_output_list(
        self,
        payloads: List[Dict[str, Any]] | None,
    ) -> List[TrainingScenarioOutput] | None:
        """委托输出装配策略批量转换候选场景 DTO。"""
        return self.output_assembler_policy.build_scenario_output_list(payloads)

    def _build_duplicate_submit_response(
        self,
        session_id: str,
        round_no: int,
        *,
        include_media_tasks: bool = False,
    ) -> Dict[str, Any] | None:
        """从已落库数据构建幂等响应。"""
        round_row = self.training_store.get_training_round_by_session_round(session_id, round_no)
        if round_row is None:
            return None

        session = self._get_session_or_raise(session_id)
        session_sequence = self._read_persisted_session_sequence_or_raise(
            session_id=session_id,
            session=session,
        )
        evaluation_row = self.training_store.get_round_evaluation_by_round_id(round_row.round_id)
        ending_row = self.training_store.get_ending_result(session_id)
        round_media_tasks = (
            self._list_round_media_tasks(session_id=session_id, round_no=round_no)
            if include_media_tasks
            else []
        )

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
            media_tasks=self._build_round_media_task_summary_outputs(round_media_tasks),
            is_completed=is_completed,
            ending=ending_row.report_payload if ending_row else None,
            decision_context=self._extract_round_decision_context(round_row.user_action),
        ).to_dict()

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

    def _normalize_submit_round_media_tasks(
        self,
        *,
        session_id: str,
        round_no: int,
        media_tasks: List[Dict[str, Any]] | None,
    ) -> List[dict]:
        if not media_tasks:
            return []

        normalized_specs: List[dict] = []
        seen_idempotency_keys: set[str] = set()
        for item in media_tasks:
            normalized_item = dict(item or {})
            normalized_task = self.media_task_policy.normalize_create_request(
                session_id=session_id,
                round_no=round_no,
                task_type=normalized_item.get("task_type"),
                payload=dict(normalized_item.get("payload", {}) or {}),
                idempotency_key=None,
                max_retries=normalized_item.get("max_retries", 0),
            )
            if normalized_task.idempotency_key in seen_idempotency_keys:
                continue
            seen_idempotency_keys.add(normalized_task.idempotency_key)
            normalized_specs.append(
                {
                    "task_type": normalized_task.task_type,
                    "idempotency_key": normalized_task.idempotency_key,
                    "request_payload": normalized_task.payload,
                    "max_retries": normalized_task.max_retries,
                }
            )
        return normalized_specs

    def _list_round_media_tasks(self, *, session_id: str, round_no: int) -> List[TrainingMediaTaskRecord]:
        try:
            return self.training_store.list_media_tasks(session_id=session_id, round_no=round_no)
        except (AttributeError, NotImplementedError):
            logger.warning(
                "training store does not support round media task reads: session_id=%s round_no=%s",
                session_id,
                round_no,
            )
            return []

    @staticmethod
    def _build_round_media_task_summary_outputs(
        rows: List[TrainingMediaTaskRecord],
    ) -> List[TrainingRoundMediaTaskSummaryOutput]:
        outputs: List[TrainingRoundMediaTaskSummaryOutput] = []
        for row in rows or []:
            outputs.append(
                TrainingRoundMediaTaskSummaryOutput(
                    task_id=row.task_id,
                    task_type=row.task_type,
                    status=row.status,
                )
            )
        return outputs

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
        """委托运行时工件策略恢复回合决策上下文。"""
        return self.runtime_artifact_policy.extract_round_decision_context(user_action)

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
        return self.decision_context_policy.build_round_decision_context(
            training_mode=training_mode,
            submitted_scenario_id=submitted_scenario_id,
            next_scenario_bundle=next_scenario_bundle,
        )

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

    def _resolve_ending(self, k: Dict[str, float], s: Dict[str, float], evaluation_rows: List[Any]) -> Dict[str, Any]:
        # 保留兼容包装方法，实际规则由 EndingPolicy 承担。
        return self.ending_policy.resolve(k_state=k, s_state=s, evaluation_rows=evaluation_rows)

