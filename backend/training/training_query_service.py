"""Read-only training query service.

This service owns stable training read models and only reads persisted facts.
It must not repair or rewrite session state on GET paths.
"""

from __future__ import annotations

from typing import Any, Dict, List

from training.constants import DEFAULT_K_STATE, DEFAULT_S_STATE, SKILL_CODES
from training.contracts import RoundEvaluationPayload
from training.exceptions import (
    TrainingSessionNotFoundError,
    TrainingSessionRecoveryStateError,
)
from training.output_assembler_policy import TrainingOutputAssemblerPolicy
from training.report_context_policy import TrainingReportContextPolicy
from training.reporting_policy import TrainingReportingPolicy
from training.round_flow_policy import TrainingRoundFlowPolicy
from training.runtime_artifact_policy import TrainingRuntimeArtifactPolicy
from training.scenario_policy import ScenarioPolicy
from training.session_snapshot_policy import (
    SessionScenarioSnapshotBundle,
    SessionScenarioSnapshotPolicy,
)
from training.training_mode import TrainingModeCatalog
from training.training_outputs import (
    TrainingDiagnosticsOutput,
    TrainingHistoryOutput,
    TrainingProgressOutput,
    TrainingReportOutput,
    TrainingSessionProgressAnchorOutput,
    TrainingSessionSummaryOutput,
    calculate_progress_percent,
)
from training.training_store import TrainingStoreProtocol
from utils.logger import get_logger

logger = get_logger(__name__)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _normalize_character_id(value: Any) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized > 0 else None


class TrainingQueryService:
    """Build stable read models directly from persisted training facts."""

    def __init__(
        self,
        *,
        training_store: TrainingStoreProtocol,
        scenario_policy: ScenarioPolicy,
        session_snapshot_policy: SessionScenarioSnapshotPolicy,
        flow_policy: TrainingRoundFlowPolicy,
        reporting_policy: TrainingReportingPolicy,
        report_context_policy: TrainingReportContextPolicy,
        runtime_artifact_policy: TrainingRuntimeArtifactPolicy,
        output_assembler_policy: TrainingOutputAssemblerPolicy,
        mode_catalog: TrainingModeCatalog,
    ):
        self.training_store = training_store
        self.scenario_policy = scenario_policy
        self.session_snapshot_policy = session_snapshot_policy
        self.flow_policy = flow_policy
        self.reporting_policy = reporting_policy
        self.report_context_policy = report_context_policy
        self.runtime_artifact_policy = runtime_artifact_policy
        self.output_assembler_policy = output_assembler_policy
        self.mode_catalog = mode_catalog

    @classmethod
    def from_runtime(cls, runtime_support: Any) -> "TrainingQueryService":
        """Reuse an existing training runtime bundle through public collaborators."""
        return cls(
            training_store=runtime_support.training_store,
            scenario_policy=runtime_support.scenario_policy,
            session_snapshot_policy=runtime_support.session_snapshot_policy,
            flow_policy=runtime_support.flow_policy,
            reporting_policy=runtime_support.reporting_policy,
            report_context_policy=runtime_support.report_context_policy,
            runtime_artifact_policy=runtime_support.runtime_artifact_policy,
            output_assembler_policy=runtime_support.output_assembler_policy,
            mode_catalog=runtime_support.mode_catalog,
        )

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Return the stable recovery summary for a training session."""
        logger.info("training session summary requested: session_id=%s", session_id)

        session = self._get_session_or_raise(session_id)
        session_sequence = self._read_persisted_session_sequence_or_raise(session_id, session)
        snapshot_bundle = self._read_session_snapshots_or_raise(session_id, session)
        is_completed = session.status == "completed"
        total_rounds = len(session_sequence)
        resumable_scenario = None
        scenario_candidates = []
        runtime_scene_id = getattr(session, "current_scenario_id", None)

        if not is_completed:
            next_scenario_bundle = self._build_session_resume_bundle(
                session_id=session_id,
                session=session,
                session_sequence=session_sequence,
                snapshot_bundle=snapshot_bundle,
            )
            resumable_scenario = self.output_assembler_policy.build_scenario_output(next_scenario_bundle.scenario)
            scenario_candidates = self.output_assembler_policy.build_scenario_output_list(
                next_scenario_bundle.scenario_candidates
            ) or []
            runtime_scene_id = (getattr(next_scenario_bundle, "scenario", {}) or {}).get("id")

        return TrainingSessionSummaryOutput(
            session_id=session_id,
            character_id=_normalize_character_id(getattr(session, "character_id", None)),
            status=session.status,
            training_mode=self._normalize_session_training_mode(session),
            current_round_no=session.current_round_no,
            total_rounds=total_rounds,
            k_state=self._normalize_k_state(session.k_state),
            s_state=self._normalize_s_state(session.s_state),
            progress_anchor=self._build_training_session_progress_anchor(
                current_round_no=session.current_round_no,
                total_rounds=total_rounds,
                is_completed=is_completed,
            ),
            player_profile=self._resolve_session_player_profile(session),
            runtime_state=self._build_training_runtime_state_output(
                self._build_runtime_state(
                    session=session,
                    current_round_no=session.current_round_no,
                    current_scene_id=runtime_scene_id,
                )
            ),
            resumable_scenario=resumable_scenario,
            scenario_candidates=scenario_candidates,
            can_resume=not is_completed and resumable_scenario is not None,
            is_completed=is_completed,
            created_at=self._serialize_optional_datetime(getattr(session, "created_at", None)),
            updated_at=self._serialize_optional_datetime(getattr(session, "updated_at", None)),
            end_time=self._serialize_optional_datetime(getattr(session, "end_time", None)),
        ).to_dict()

    def get_progress(self, session_id: str) -> Dict[str, Any]:
        """Return the stable progress read model for a training session."""
        logger.info("training progress requested: session_id=%s", session_id)

        session = self._get_session_or_raise(session_id)
        session_sequence = self._read_persisted_session_sequence_or_raise(session_id, session)
        self._read_session_snapshots_or_raise(session_id, session)
        latest_decision_context, latest_consequence_events = (
            self._get_latest_round_runtime_artifacts(session_id)
        )

        return TrainingProgressOutput(
            session_id=session_id,
            character_id=_normalize_character_id(getattr(session, "character_id", None)),
            status=session.status,
            round_no=session.current_round_no,
            total_rounds=len(session_sequence),
            k_state=self._normalize_k_state(session.k_state),
            s_state=self._normalize_s_state(session.s_state),
            player_profile=self._resolve_session_player_profile(session),
            runtime_state=self._build_training_runtime_state_output(
                self._build_runtime_state(session=session)
            ),
            decision_context=latest_decision_context,
            consequence_events=latest_consequence_events,
        ).to_dict()

    def get_history(self, session_id: str) -> Dict[str, Any]:
        """Return the canonical training history read model."""
        logger.info("training history requested: session_id=%s", session_id)

        session = self._get_session_or_raise(session_id)
        session_sequence = self._read_persisted_session_sequence_or_raise(session_id, session)
        self._read_session_snapshots_or_raise(session_id, session)
        rounds = self.training_store.get_training_rounds(session_id)
        evaluations = self.training_store.get_round_evaluations_by_session(session_id)
        kt_observations = self.training_store.get_kt_observations(session_id)
        eval_map = {item.round_id: item for item in evaluations}
        kt_observation_map = {item.round_no: item for item in kt_observations}
        is_completed = session.status == "completed"

        return TrainingHistoryOutput(
            session_id=session_id,
            character_id=_normalize_character_id(getattr(session, "character_id", None)),
            status=session.status,
            training_mode=self._normalize_session_training_mode(session),
            current_round_no=session.current_round_no,
            total_rounds=len(session_sequence),
            progress_anchor=self._build_training_session_progress_anchor(
                current_round_no=session.current_round_no,
                total_rounds=len(session_sequence),
                is_completed=is_completed,
            ),
            player_profile=self._resolve_session_player_profile(session),
            runtime_state=self._build_training_runtime_state_output(
                self._build_runtime_state(session=session)
            ),
            history=self.report_context_policy.build_report_history(
                rounds=rounds,
                eval_map=eval_map,
                kt_observation_map=kt_observation_map,
            ),
            is_completed=is_completed,
            created_at=self._serialize_optional_datetime(getattr(session, "created_at", None)),
            updated_at=self._serialize_optional_datetime(getattr(session, "updated_at", None)),
            end_time=self._serialize_optional_datetime(getattr(session, "end_time", None)),
        ).to_dict()

    def get_report(self, session_id: str) -> Dict[str, Any]:
        """Return the stable training report read model."""
        logger.info("training report requested: session_id=%s", session_id)

        session = self._get_session_or_raise(session_id)
        self._read_persisted_session_sequence_or_raise(session_id, session)
        snapshot_bundle = self._read_session_snapshots_or_raise(session_id, session)
        rounds = self.training_store.get_training_rounds(session_id)
        evaluations = self.training_store.get_round_evaluations_by_session(session_id)
        kt_observations = self.training_store.get_kt_observations(session_id)
        scenario_title_map = self.report_context_policy.build_report_scenario_title_map(
            snapshot_bundle.scenario_payload_catalog
        )
        eval_map = {item.round_id: item for item in evaluations}
        kt_observation_map = {item.round_no: item for item in kt_observations}
        ending = self.training_store.get_ending_result(session_id)

        history = self.report_context_policy.build_report_history(
            rounds=rounds,
            eval_map=eval_map,
            kt_observation_map=kt_observation_map,
        )
        initial_k_state, initial_s_state = self.report_context_policy.resolve_report_initial_states(
            session=session,
            rounds=rounds,
        )
        final_k = self._normalize_k_state(session.k_state)
        final_s = self._normalize_s_state(session.s_state)
        round_snapshots = self.report_context_policy.build_report_round_snapshots(
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
            character_id=_normalize_character_id(getattr(session, "character_id", None)),
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
        """Return the stable diagnostics read model for a training session."""
        logger.info("training diagnostics requested: session_id=%s", session_id)

        session = self._get_session_or_raise(session_id)
        # Diagnostics must consume the same persisted recovery facts as the
        # other read models; otherwise corrupted sessions can silently fork UX.
        self._read_persisted_session_sequence_or_raise(session_id, session)
        self._read_session_snapshots_or_raise(session_id, session)
        recommendation_logs = self.training_store.get_scenario_recommendation_logs(session_id)
        audit_events = self.training_store.get_training_audit_events(session_id)
        kt_observations = self.training_store.get_kt_observations(session_id)

        recommendation_outputs = self.output_assembler_policy.build_recommendation_log_outputs(recommendation_logs)
        audit_event_outputs = self.output_assembler_policy.build_audit_event_outputs(audit_events)
        kt_observation_outputs = self.output_assembler_policy.build_kt_observation_outputs(kt_observations)
        summary_output = self.reporting_policy.build_diagnostics_summary(
            recommendation_logs=recommendation_outputs,
            audit_events=audit_event_outputs,
            kt_observations=kt_observation_outputs,
        )

        return TrainingDiagnosticsOutput(
            session_id=session_id,
            character_id=_normalize_character_id(getattr(session, "character_id", None)),
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

    def _get_session_or_raise(self, session_id: str) -> Any:
        session = self.training_store.get_training_session(session_id)
        if session is None:
            raise TrainingSessionNotFoundError(session_id=session_id)
        return session

    def _read_persisted_session_sequence_or_raise(
        self,
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

    def _read_session_snapshots_or_raise(
        self,
        session_id: str,
        session: Any,
    ) -> SessionScenarioSnapshotBundle:
        return self.session_snapshot_policy.require_session_snapshots(
            session_id=session_id,
            session=session,
        )

    def _build_session_resume_bundle(
        self,
        *,
        session_id: str,
        session: Any,
        session_sequence: List[Dict[str, str]],
        snapshot_bundle: SessionScenarioSnapshotBundle,
    ) -> Any:
        try:
            return self.flow_policy.build_next_scenario_bundle(
                training_mode=self._normalize_session_training_mode(session),
                current_round_no=session.current_round_no,
                session_sequence=session_sequence,
                scenario_payload_sequence=snapshot_bundle.scenario_payload_sequence,
                scenario_payload_catalog=snapshot_bundle.scenario_payload_catalog,
                completed_scenario_ids=self._get_completed_scenario_ids(session_id),
                k_state=self._normalize_k_state(session.k_state),
                s_state=self._normalize_s_state(session.s_state),
                recent_risk_rounds=self._get_recent_risk_rounds(session_id),
                runtime_flags=self.runtime_artifact_policy.resolve_session_runtime_flags(session),
                current_scenario_id=getattr(session, "current_scenario_id", None),
            )
        except ValueError as exc:
            raise TrainingSessionRecoveryStateError(
                session_id=session_id,
                reason="scenario_flow_unavailable",
                details={
                    "phase": "summary_resume",
                    "flow_error": str(exc),
                },
            ) from exc

    def _get_completed_scenario_ids(self, session_id: str) -> List[str]:
        return [row.scenario_id for row in self.training_store.get_training_rounds(session_id)]

    def _get_recent_risk_rounds(self, session_id: str) -> List[List[str]]:
        risk_rounds: List[List[str]] = []
        for evaluation_row in self.training_store.get_round_evaluations_by_session(session_id):
            payload = RoundEvaluationPayload.from_raw(getattr(evaluation_row, "raw_payload", None)).to_dict()
            risk_rounds.append([str(flag) for flag in payload.get("risk_flags", []) if str(flag or "").strip()])
        return risk_rounds

    def _get_latest_round_runtime_artifacts(self, session_id: str) -> tuple[Any, List[Any]]:
        """Extract the latest round decision/consequence artifacts for progress reads."""
        rounds = self.training_store.get_training_rounds(session_id)
        if not rounds:
            return None, []

        latest_round = max(rounds, key=lambda row: int(getattr(row, "round_no", 0) or 0))
        latest_user_action = getattr(latest_round, "user_action", None)
        return (
            self.runtime_artifact_policy.extract_round_decision_context(latest_user_action),
            self.runtime_artifact_policy.extract_round_consequence_events(latest_user_action),
        )

    def _normalize_session_training_mode(self, session: Any) -> str:
        return self.mode_catalog.normalize(
            getattr(session, "training_mode", "guided"),
            default="guided",
            raise_on_unknown=False,
        ) or "guided"

    def _resolve_session_player_profile_payload(self, session: Any) -> Dict[str, Any]:
        return dict(self.scenario_policy.resolve_session_player_profile(session) or {})

    def _resolve_session_player_profile(self, session: Any) -> Any:
        return self.output_assembler_policy.build_player_profile_output(
            self._resolve_session_player_profile_payload(session)
        )

    def _build_runtime_state(
        self,
        *,
        session: Any,
        current_round_no: int | None = None,
        current_scene_id: str | None = None,
        k_state: Dict[str, Any] | None = None,
        s_state: Dict[str, Any] | None = None,
        runtime_flags: Dict[str, Any] | None = None,
    ) -> Any:
        return self.runtime_artifact_policy.build_runtime_state(
            session=session,
            player_profile=self._resolve_session_player_profile_payload(session),
            current_round_no=current_round_no,
            current_scene_id=current_scene_id,
            k_state=k_state,
            s_state=s_state,
            runtime_flags=runtime_flags,
        )

    def _build_training_runtime_state_output(self, runtime_state: Any) -> Any:
        return self.output_assembler_policy.build_runtime_state_output(runtime_state)

    def _build_training_session_progress_anchor(
        self,
        *,
        current_round_no: int,
        total_rounds: int,
        is_completed: bool,
    ) -> TrainingSessionProgressAnchorOutput:
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

    def _normalize_k_state(self, k_state: Dict[str, float] | None) -> Dict[str, float]:
        source = k_state or {}
        return {
            code: round(_clamp(float(source.get(code, DEFAULT_K_STATE[code]))), 4)
            for code in SKILL_CODES
        }

    def _normalize_s_state(self, s_state: Dict[str, float] | None) -> Dict[str, float]:
        source = s_state or {}
        return {
            key: round(_clamp(float(source.get(key, DEFAULT_S_STATE[key]))), 4)
            for key in DEFAULT_S_STATE.keys()
        }

    @staticmethod
    def _serialize_optional_datetime(value) -> str | None:
        return value.isoformat() if value is not None else None
