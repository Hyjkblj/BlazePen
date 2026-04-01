"""训练域专用 SQLAlchemy 仓储实现。"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import case
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from sqlalchemy.orm import Session

from database.integrity import is_unique_constraint_conflict
from database.session_factory import get_engine, get_session_factory
from models.training import (
    EndingResult,
    KtObservation,
    KtStateSnapshot,
    NarrativeStateSnapshot,
    RoundEvaluation,
    ScenarioRecommendationLog,
    TrainingAuditEvent,
    TrainingMediaTask,
    TrainingRound,
    TrainingSession,
    TrainingStoryScript,
)
from training.constants import DEFAULT_EVAL_MODEL, SKILL_SNAPSHOT_FIELDS, S_STATE_SNAPSHOT_FIELDS, TRAINING_ENDING_TYPE_FAIL
from training.contracts import KtObservationPayload, RoundEvaluationPayload, ScenarioRecommendationLogPayload, TrainingAuditEventPayload
from training.exceptions import DuplicateRoundSubmissionError, TrainingSessionNotFoundError


class SqlAlchemyTrainingRepository:
    """训练域专用仓储。

    这里直接面向训练表和训练契约，避免把训练逻辑继续塞回通用 `DatabaseManager`。
    """

    def __init__(self, engine=None, session_factory=None):
        self.engine = engine or get_engine()
        self.SessionLocal = session_factory or get_session_factory()

    @contextmanager
    def get_session(self):
        """获取训练域数据库会话。"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_training_session_artifacts(
        self,
        user_id: str,
        character_id: int = None,
        training_mode: str = "guided",
        k_state: dict = None,
        s_state: dict = None,
        session_meta: dict = None,
        audit_event_payload: dict = None,
    ) -> TrainingSession:
        """原子化创建训练会话及 round=0 快照。"""
        normalized_k_state = dict(k_state or {})
        normalized_s_state = dict(s_state or {})
        normalized_audit_event = (
            TrainingAuditEventPayload.from_raw(audit_event_payload).to_dict()
            if audit_event_payload
            else None
        )

        with self.get_session() as session:
            row = TrainingSession(
                user_id=user_id,
                character_id=character_id,
                training_mode=training_mode,
                status="in_progress",
                k_state=normalized_k_state,
                s_state=normalized_s_state,
                session_meta=session_meta or {},
                current_round_no=0,
            )
            session.add(row)
            session.flush()

            self._create_kt_snapshot_row(session=session, session_id=row.session_id, round_no=0, k_state=normalized_k_state)
            self._create_narrative_snapshot_row(session=session, session_id=row.session_id, round_no=0, s_state=normalized_s_state)

            if normalized_audit_event:
                self._create_training_audit_event_row(
                    session=session,
                    session_id=row.session_id,
                    event_type=str(normalized_audit_event.get("event_type") or "session_initialized"),
                    round_no=normalized_audit_event.get("round_no"),
                    payload=normalized_audit_event.get("payload"),
                )

            session.flush()
            return row

    def create_training_session(
        self,
        user_id: str,
        character_id: int = None,
        training_mode: str = "guided",
        k_state: dict = None,
        s_state: dict = None,
        session_meta: dict = None,
    ) -> TrainingSession:
        """创建训练会话。"""
        with self.get_session() as session:
            row = TrainingSession(
                user_id=user_id,
                character_id=character_id,
                training_mode=training_mode,
                status="in_progress",
                k_state=k_state or {},
                s_state=s_state or {},
                session_meta=session_meta or {},
                current_round_no=0,
            )
            session.add(row)
            session.flush()
            return row

    def get_training_session(self, session_id: str) -> TrainingSession:
        """读取训练会话。"""
        with self.get_session() as session:
            return session.query(TrainingSession).filter(TrainingSession.session_id == session_id).first()

    def update_training_session(self, session_id: str, updates: dict) -> TrainingSession:
        """更新训练会话。"""
        with self.get_session() as session:
            row = session.query(TrainingSession).filter(TrainingSession.session_id == session_id).first()
            if not row:
                return None
            for key, value in updates.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            session.flush()
            return row

    def get_story_script_by_session_id(self, session_id: str) -> TrainingStoryScript | None:
        with self.get_session() as session:
            return (
                session.query(TrainingStoryScript)
                .filter(TrainingStoryScript.session_id == str(session_id))
                .first()
            )

    def count_story_scripts_excluding_session_id(self, session_id: str) -> int:
        with self.get_session() as session:
            return (
                session.query(TrainingStoryScript)
                .filter(TrainingStoryScript.session_id != str(session_id))
                .count()
            )

    def list_story_scripts_excluding_session_id(self, session_id: str, limit: int = 50) -> list[TrainingStoryScript]:
        normalized_limit = max(1, min(int(limit or 50), 200))
        with self.get_session() as session:
            return (
                session.query(TrainingStoryScript)
                .filter(TrainingStoryScript.session_id != str(session_id))
                .order_by(TrainingStoryScript.created_at.desc())
                .limit(normalized_limit)
                .all()
            )

    def create_story_script(
        self,
        *,
        session_id: str,
        payload: dict,
        provider: str = "auto",
        model: str = "auto",
        major_scene_count: int = 6,
        micro_scenes_per_gap: int = 2,
        source_script_id: str | None = None,
        status: str = "ready",
        error_code: str | None = None,
        error_message: str | None = None,
        fallback_used: bool = False,
    ) -> TrainingStoryScript:
        with self.get_session() as session:
            row = TrainingStoryScript(
                session_id=str(session_id),
                source_script_id=str(source_script_id).strip() if source_script_id else None,
                provider=str(provider or "auto"),
                model=str(model or "auto"),
                major_scene_count=int(major_scene_count or 6),
                micro_scenes_per_gap=int(micro_scenes_per_gap or 2),
                status=str(status or "ready").strip() or "ready",
                error_code=str(error_code).strip() if error_code else None,
                error_message=str(error_message).strip() if error_message else None,
                fallback_used=bool(fallback_used),
                payload=payload or {},
            )
            session.add(row)
            try:
                session.flush()
                return row
            except IntegrityError:
                session.rollback()
                existing = (
                    session.query(TrainingStoryScript)
                    .filter(TrainingStoryScript.session_id == str(session_id))
                    .first()
                )
                if existing is not None:
                    return existing
                raise

    def update_story_script_by_session_id(self, session_id: str, updates: dict) -> TrainingStoryScript | None:
        with self.get_session() as session:
            row = (
                session.query(TrainingStoryScript)
                .filter(TrainingStoryScript.session_id == str(session_id))
                .first()
            )
            if row is None:
                return None
            for key, value in (updates or {}).items():
                if hasattr(row, key):
                    setattr(row, key, value)
            session.flush()
            return row

    def claim_story_script_job(self, session_id: str, *, lease_seconds: int = 300) -> bool:
        """Try to claim a story-script generation job at store level (cross-process safe).

        Claim rules:
        - pending -> running (claim)
        - running can be reclaimed if lease expired (updated_at too old)
        - ready/succeeded/failed are terminal
        """
        normalized_session_id = str(session_id or "").strip()
        if not normalized_session_id:
            return False
        lease_seconds = max(30, int(lease_seconds or 300))
        lease_deadline = datetime.utcnow() - timedelta(seconds=lease_seconds)
        with self.get_session() as session:
            updated = (
                session.query(TrainingStoryScript)
                .filter(
                    TrainingStoryScript.session_id == normalized_session_id,
                    TrainingStoryScript.status == "pending",
                )
                .update(
                    {
                        "status": "running",
                        "updated_at": datetime.utcnow(),
                    },
                    synchronize_session=False,
                )
            )
            if updated:
                session.flush()
                return True

            # Reclaim stale running rows (best-effort lease).
            updated = (
                session.query(TrainingStoryScript)
                .filter(
                    TrainingStoryScript.session_id == normalized_session_id,
                    TrainingStoryScript.status == "running",
                    TrainingStoryScript.updated_at < lease_deadline,
                )
                .update(
                    {
                        "status": "running",
                        "updated_at": datetime.utcnow(),
                    },
                    synchronize_session=False,
                )
            )
            if updated:
                session.flush()
                return True
            return False

    def create_media_task(
        self,
        *,
        session_id: str,
        round_no: int | None,
        task_type: str,
        idempotency_key: str,
        request_payload: dict,
        max_retries: int = 0,
    ) -> TrainingMediaTask:
        """Create a training media task row with idempotency protection."""
        with self.get_session() as session:
            row = TrainingMediaTask(
                session_id=session_id,
                round_no=round_no,
                task_type=task_type,
                status="pending",
                idempotency_key=idempotency_key,
                request_payload=request_payload or {},
                retry_count=0,
                max_retries=int(max_retries or 0),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as exc:
                if self._is_duplicate_media_task_conflict(exc):
                    session.rollback()
                    existing = (
                        session.query(TrainingMediaTask)
                        .filter(TrainingMediaTask.idempotency_key == idempotency_key)
                        .first()
                    )
                    if existing is not None:
                        return existing
                raise
            return row

    def get_media_task(self, task_id: str) -> TrainingMediaTask | None:
        """Read a training media task by task_id."""
        with self.get_session() as session:
            return session.query(TrainingMediaTask).filter(TrainingMediaTask.task_id == task_id).first()

    def get_media_task_by_idempotency_key(self, idempotency_key: str) -> TrainingMediaTask | None:
        """Read a training media task by idempotency key."""
        with self.get_session() as session:
            return (
                session.query(TrainingMediaTask)
                .filter(TrainingMediaTask.idempotency_key == idempotency_key)
                .first()
            )

    def update_media_task(self, task_id: str, updates: dict) -> TrainingMediaTask | None:
        """Update mutable fields for a media task row."""
        with self.get_session() as session:
            row = session.query(TrainingMediaTask).filter(TrainingMediaTask.task_id == task_id).first()
            if row is None:
                return None

            for key, value in (updates or {}).items():
                if hasattr(row, key):
                    setattr(row, key, value)
            row.updated_at = datetime.utcnow()
            session.flush()
            return row

    def list_media_tasks(self, session_id: str, round_no: int | None = None) -> list[TrainingMediaTask]:
        """List media tasks in a training session, optionally filtered by round."""
        with self.get_session() as session:
            query = session.query(TrainingMediaTask).filter(TrainingMediaTask.session_id == session_id)
            if round_no is not None:
                query = query.filter(TrainingMediaTask.round_no == round_no)
            return query.order_by(TrainingMediaTask.created_at.asc()).all()

    def list_media_tasks_by_status(self, statuses: list[str]) -> list[TrainingMediaTask]:
        """List media tasks by statuses across sessions."""
        normalized_statuses = [
            str(item).strip().lower()
            for item in statuses or []
            if str(item).strip()
        ]
        if not normalized_statuses:
            return []

        with self.get_session() as session:
            return (
                session.query(TrainingMediaTask)
                .filter(TrainingMediaTask.status.in_(normalized_statuses))
                .order_by(TrainingMediaTask.created_at.asc())
                .all()
            )

    def claim_media_task(self, task_id: str) -> TrainingMediaTask | None:
        """Claim a pending media task using a compare-and-set style transition."""
        with self.get_session() as session:
            now = datetime.utcnow()
            updated_rows = (
                session.query(TrainingMediaTask)
                .filter(
                    TrainingMediaTask.task_id == task_id,
                    TrainingMediaTask.status == "pending",
                )
                .update(
                    {
                        TrainingMediaTask.status: "running",
                        TrainingMediaTask.started_at: case(
                            (TrainingMediaTask.started_at.is_(None), now),
                            else_=TrainingMediaTask.started_at,
                        ),
                        TrainingMediaTask.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            if updated_rows != 1:
                return None

            row = (
                session.query(TrainingMediaTask)
                .filter(TrainingMediaTask.task_id == task_id)
                .first()
            )
            session.flush()
            return row

    def complete_media_task(
        self,
        task_id: str,
        *,
        status: str,
        result_payload: dict | None = None,
        error_payload: dict | None = None,
        retry_count: int | None = None,
    ) -> TrainingMediaTask | None:
        """Mark a media task as completed/failed/timeout with result payloads."""
        with self.get_session() as session:
            row = session.query(TrainingMediaTask).filter(TrainingMediaTask.task_id == task_id).first()
            if row is None:
                return None

            now = datetime.utcnow()
            row.status = status
            row.result_payload = result_payload
            row.error_payload = error_payload
            if retry_count is not None:
                row.retry_count = int(retry_count)
            row.finished_at = now
            row.updated_at = now
            session.flush()
            return row

    def create_training_round(
        self,
        session_id: str,
        round_no: int,
        scenario_id: str,
        user_input_raw: str,
        selected_option: str = None,
        user_action: dict = None,
        state_before: dict = None,
        state_after: dict = None,
        kt_before: dict = None,
        kt_after: dict = None,
        feedback_text: str = None,
        node_code: str = None,
    ) -> TrainingRound:
        """创建训练回合记录。"""
        with self.get_session() as session:
            row = TrainingRound(
                session_id=session_id,
                round_no=round_no,
                scenario_id=scenario_id,
                node_code=node_code,
                user_input_raw=user_input_raw,
                selected_option=selected_option,
                user_action=user_action or {},
                state_before=state_before or {},
                state_after=state_after or {},
                kt_before=kt_before or {},
                kt_after=kt_after or {},
                feedback_text=feedback_text,
            )
            session.add(row)
            session.flush()
            return row

    def get_training_rounds(self, session_id: str) -> list:
        """读取训练会话的全部回合。"""
        with self.get_session() as session:
            return (
                session.query(TrainingRound)
                .filter(TrainingRound.session_id == session_id)
                .order_by(TrainingRound.round_no.asc())
                .all()
            )

    def get_training_round_by_session_round(self, session_id: str, round_no: int) -> TrainingRound:
        """按 `(session_id, round_no)` 读取单回合。"""
        with self.get_session() as session:
            return (
                session.query(TrainingRound)
                .filter(TrainingRound.session_id == session_id, TrainingRound.round_no == round_no)
                .first()
            )

    def create_round_evaluation(self, round_id: str, payload: dict, llm_model: str = None) -> RoundEvaluation:
        """保存回合评估。"""
        normalized = RoundEvaluationPayload.from_raw(payload)
        normalized_payload = normalized.to_dict()
        model_name = llm_model or normalized.llm_model or DEFAULT_EVAL_MODEL
        with self.get_session() as session:
            row = RoundEvaluation(
                round_id=round_id,
                llm_model=model_name,
                confidence=normalized.confidence,
                risk_flags=normalized.risk_flags,
                skill_delta=normalized.skill_delta,
                s_delta=normalized.s_delta,
                evidence=normalized.evidence,
                skill_scores_preview=normalized.skill_scores_preview,
                raw_payload=normalized_payload,
            )
            session.add(row)
            session.flush()
            return row

    def get_round_evaluation_by_round_id(self, round_id: str) -> RoundEvaluation:
        """按 round_id 读取单条评估记录。"""
        with self.get_session() as session:
            return session.query(RoundEvaluation).filter(RoundEvaluation.round_id == round_id).first()

    def get_round_evaluations_by_session(self, session_id: str) -> list:
        """按会话读取评估结果。"""
        with self.get_session() as session:
            return (
                session.query(RoundEvaluation)
                .join(TrainingRound, RoundEvaluation.round_id == TrainingRound.round_id)
                .filter(TrainingRound.session_id == session_id)
                .order_by(TrainingRound.round_no.asc())
                .all()
            )

    def create_kt_snapshot(self, session_id: str, round_no: int, k_state: dict) -> KtStateSnapshot:
        """保存 KT 快照。"""
        with self.get_session() as session:
            row = self._create_kt_snapshot_row(
                session=session,
                session_id=session_id,
                round_no=round_no,
                k_state=k_state or {},
            )
            session.flush()
            return row

    def create_narrative_snapshot(self, session_id: str, round_no: int, s_state: dict) -> NarrativeStateSnapshot:
        """保存 S 状态快照。"""
        with self.get_session() as session:
            row = self._create_narrative_snapshot_row(
                session=session,
                session_id=session_id,
                round_no=round_no,
                s_state=s_state or {},
            )
            session.flush()
            return row

    def save_training_round_artifacts(
        self,
        session_id: str,
        round_no: int,
        scenario_id: str,
        user_input_raw: str,
        selected_option: str,
        user_action: dict,
        state_before: dict,
        state_after: dict,
        kt_before: dict,
        kt_after: dict,
        feedback_text: str,
        evaluation_payload: dict,
        ending_payload: dict,
        status: str,
        end_time: datetime,
        session_meta: dict = None,
        recommendation_log_payload: dict = None,
        audit_event_payloads: list[dict] = None,
        kt_observation_payload: dict = None,
        media_task_specs: list[dict] | None = None,
    ) -> TrainingRound:
        """以原子方式持久化单回合全部工件。"""
        normalized = RoundEvaluationPayload.from_raw(evaluation_payload)
        payload = normalized.to_dict()
        model_name = normalized.llm_model or DEFAULT_EVAL_MODEL
        normalized_recommendation_log = (
            ScenarioRecommendationLogPayload.from_raw(recommendation_log_payload).to_dict()
            if recommendation_log_payload
            else None
        )
        normalized_audit_event_payloads = [
            item.to_dict()
            for item in (
                TrainingAuditEventPayload.from_raw(event_payload)
                for event_payload in audit_event_payloads or []
            )
            if item is not None
        ]
        normalized_kt_observation = (
            KtObservationPayload.from_raw(kt_observation_payload).to_dict()
            if kt_observation_payload
            else None
        )

        with self.get_session() as session:
            session_row = session.query(TrainingSession).filter(TrainingSession.session_id == session_id).first()
            if session_row is None:
                raise TrainingSessionNotFoundError(session_id=session_id)

            round_row = TrainingRound(
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
            )
            session.add(round_row)
            try:
                session.flush()
            except IntegrityError as exc:
                if self._is_duplicate_round_conflict(exc):
                    raise DuplicateRoundSubmissionError(session_id=session_id, round_no=round_no) from exc
                raise

            session.add(
                RoundEvaluation(
                    round_id=round_row.round_id,
                    llm_model=model_name,
                    confidence=normalized.confidence,
                    risk_flags=normalized.risk_flags,
                    skill_delta=normalized.skill_delta,
                    s_delta=normalized.s_delta,
                    evidence=normalized.evidence,
                    skill_scores_preview=normalized.skill_scores_preview,
                    raw_payload=payload,
                )
            )
            self._create_kt_snapshot_row(session=session, session_id=session_id, round_no=round_no, k_state=kt_after or {})
            self._create_narrative_snapshot_row(session=session, session_id=session_id, round_no=round_no, s_state=state_after or {})

            session_row.current_round_no = round_no
            session_row.current_scenario_id = scenario_id
            session_row.k_state = kt_after or {}
            session_row.s_state = state_after or {}
            if session_meta is not None:
                # 运行时 flags 与会话冻结信息共用 session_meta，避免再造平行状态源。
                session_row.session_meta = dict(session_meta or {})
            session_row.status = status or session_row.status
            session_row.updated_at = datetime.utcnow()
            if end_time is not None:
                session_row.end_time = end_time

            if ending_payload is not None:
                self._upsert_ending_result_row(session=session, session_id=session_id, ending=ending_payload)

            if normalized_recommendation_log:
                self._upsert_scenario_recommendation_log_row(
                    session=session,
                    session_id=session_id,
                    round_no=round_no,
                    payload=normalized_recommendation_log,
                )

            for event_payload in normalized_audit_event_payloads:
                self._create_training_audit_event_row(
                    session=session,
                    session_id=session_id,
                    event_type=str(event_payload.get("event_type") or "unknown_event"),
                    round_no=event_payload.get("round_no"),
                    payload=event_payload.get("payload"),
                )

            if normalized_kt_observation:
                self._create_kt_observation_row(
                    session=session,
                    session_id=session_id,
                    round_no=round_no,
                    payload=normalized_kt_observation,
                )

            created_media_tasks: list[TrainingMediaTask] = []
            for media_task_spec in media_task_specs or []:
                task_type = str((media_task_spec or {}).get("task_type") or "").strip().lower()
                idempotency_key = str((media_task_spec or {}).get("idempotency_key") or "").strip()
                if not task_type or not idempotency_key:
                    continue

                created_media_tasks.append(
                    self._create_media_task_row(
                        session=session,
                        session_id=session_id,
                        round_no=round_no,
                        task_type=task_type,
                        idempotency_key=idempotency_key,
                        request_payload=dict((media_task_spec or {}).get("request_payload", {}) or {}),
                        max_retries=int((media_task_spec or {}).get("max_retries", 0) or 0),
                    )
                )

            for media_task_row in created_media_tasks:
                self._create_training_audit_event_row(
                    session=session,
                    session_id=session_id,
                    event_type="training_media_task_enqueued",
                    round_no=round_no,
                    payload={
                        "route": "training.submit_round",
                        "session_id": session_id,
                        "round_no": round_no,
                        "task_id": media_task_row.task_id,
                        "task_type": media_task_row.task_type,
                        "status": media_task_row.status,
                    },
                )

            try:
                session.flush()
            except IntegrityError as exc:
                if self._is_duplicate_media_task_conflict(exc):
                    raise DuplicateRoundSubmissionError(session_id=session_id, round_no=round_no) from exc
                raise
            return round_row

    @staticmethod
    def _is_duplicate_round_conflict(exc: IntegrityError) -> bool:
        """识别训练回合重复提交冲突。"""
        return is_unique_constraint_conflict(
            exc,
            constraint_name="uq_training_rounds_session_round",
            fallback_token_groups=(
                ("training_rounds", "round_no", "session_id"),
                ("duplicate key", "training_rounds"),
            ),
        )

    @staticmethod
    def _is_duplicate_media_task_conflict(exc: IntegrityError) -> bool:
        """Detect duplicate idempotency_key conflicts for media tasks."""
        return is_unique_constraint_conflict(
            exc,
            constraint_name="uq_training_media_tasks_idempotency_key",
            fallback_token_groups=(
                ("training_media_tasks", "idempotency_key"),
                ("duplicate key", "training_media_tasks"),
            ),
        )

    def upsert_ending_result(self, session_id: str, ending: dict) -> EndingResult:
        """保存或更新结局。"""
        with self.get_session() as session:
            row = self._upsert_ending_result_row(session=session, session_id=session_id, ending=ending)
            session.flush()
            return row

    def get_ending_result(self, session_id: str) -> EndingResult:
        """读取结局结果。"""
        with self.get_session() as session:
            return session.query(EndingResult).filter(EndingResult.session_id == session_id).first()

    def upsert_scenario_recommendation_log(
        self,
        session_id: str,
        round_no: int,
        payload: dict,
    ) -> ScenarioRecommendationLog:
        """保存或更新某一轮的推荐日志。"""
        normalized_payload = ScenarioRecommendationLogPayload.from_raw(payload).to_dict()
        with self.get_session() as session:
            row = self._upsert_scenario_recommendation_log_row(
                session=session,
                session_id=session_id,
                round_no=round_no,
                payload=normalized_payload,
            )
            session.flush()
            return row

    def get_scenario_recommendation_logs(self, session_id: str) -> list:
        """按会话读取推荐日志。"""
        with self.get_session() as session:
            return (
                session.query(ScenarioRecommendationLog)
                .filter(ScenarioRecommendationLog.session_id == session_id)
                .order_by(ScenarioRecommendationLog.round_no.asc(), ScenarioRecommendationLog.created_at.asc())
                .all()
            )

    def create_training_audit_event(
        self,
        session_id: str,
        event_type: str,
        round_no: int = None,
        payload: dict = None,
    ) -> TrainingAuditEvent:
        """追加训练审计事件。"""
        normalized_payload = TrainingAuditEventPayload(
            event_type=event_type,
            round_no=round_no,
            payload=payload or {},
        ).to_dict()
        with self.get_session() as session:
            row = self._create_training_audit_event_row(
                session=session,
                session_id=session_id,
                event_type=normalized_payload["event_type"],
                round_no=normalized_payload.get("round_no"),
                payload=normalized_payload.get("payload"),
            )
            session.flush()
            return row

    def get_training_audit_events(self, session_id: str) -> list:
        """按会话读取审计事件。"""
        with self.get_session() as session:
            return (
                session.query(TrainingAuditEvent)
                .filter(TrainingAuditEvent.session_id == session_id)
                .order_by(TrainingAuditEvent.created_at.asc())
                .all()
            )

    def create_kt_observation(
        self,
        session_id: str,
        round_no: int,
        payload: dict,
    ) -> KtObservation:
        """追加单轮 KT 结构化观测。"""
        normalized_payload = KtObservationPayload.from_raw(payload)
        if normalized_payload is None:
            raise ValueError("kt observation payload is invalid")

        with self.get_session() as session:
            row = self._create_kt_observation_row(
                session=session,
                session_id=session_id,
                round_no=round_no,
                payload=normalized_payload.to_dict(),
            )
            session.flush()
            return row

    def get_kt_observations(self, session_id: str) -> list:
        """按会话读取 KT 结构化观测。"""
        with self.get_session() as session:
            return (
                session.query(KtObservation)
                .filter(KtObservation.session_id == session_id)
                .order_by(KtObservation.round_no.asc(), KtObservation.created_at.asc())
                .all()
            )

    def _upsert_ending_result_row(self, session: Session, session_id: str, ending: dict) -> EndingResult:
        """在给定事务内保存或更新结局。"""
        row = session.query(EndingResult).filter(EndingResult.session_id == session_id).first()
        if row is None:
            row = EndingResult(
                session_id=session_id,
                ending_type=ending.get("type", TRAINING_ENDING_TYPE_FAIL),
                ending_score=float(ending.get("score", 0.0)),
                explanation=ending.get("explanation", ""),
                report_payload=ending,
            )
            session.add(row)
            return row

        row.ending_type = ending.get("type", row.ending_type)
        row.ending_score = float(ending.get("score", row.ending_score))
        row.explanation = ending.get("explanation", row.explanation)
        row.report_payload = ending
        return row

    def _create_kt_snapshot_row(
        self,
        session: Session,
        session_id: str,
        round_no: int,
        k_state: dict,
    ) -> KtStateSnapshot:
        """在给定事务里保存 KT 快照。"""
        row = KtStateSnapshot(session_id=session_id, round_no=round_no)
        for skill_code, field_name in SKILL_SNAPSHOT_FIELDS.items():
            setattr(row, field_name, float((k_state or {}).get(skill_code, 0.0)))
        session.add(row)
        return row

    def _create_narrative_snapshot_row(
        self,
        session: Session,
        session_id: str,
        round_no: int,
        s_state: dict,
    ) -> NarrativeStateSnapshot:
        """在给定事务里保存 S 状态快照。"""
        row = NarrativeStateSnapshot(session_id=session_id, round_no=round_no)
        for state_code, field_name in S_STATE_SNAPSHOT_FIELDS.items():
            setattr(row, field_name, float((s_state or {}).get(state_code, 0.0)))
        session.add(row)
        return row

    def _upsert_scenario_recommendation_log_row(
        self,
        session: Session,
        session_id: str,
        round_no: int,
        payload: dict,
    ) -> ScenarioRecommendationLog:
        """在给定事务里保存推荐日志。"""
        row = (
            session.query(ScenarioRecommendationLog)
            .filter(
                ScenarioRecommendationLog.session_id == session_id,
                ScenarioRecommendationLog.round_no == round_no,
            )
            .first()
        )
        if row is None:
            row = ScenarioRecommendationLog(session_id=session_id, round_no=round_no)
            session.add(row)

        row.training_mode = str((payload or {}).get("training_mode") or "guided")
        row.selection_source = (payload or {}).get("selection_source")
        row.recommended_scenario_id = (payload or {}).get("recommended_scenario_id")
        row.selected_scenario_id = (payload or {}).get("selected_scenario_id")
        row.candidate_pool = list((payload or {}).get("candidate_pool", []) or [])
        row.recommended_recommendation = dict((payload or {}).get("recommended_recommendation", {}) or {})
        row.selected_recommendation = dict((payload or {}).get("selected_recommendation", {}) or {})
        row.decision_context = dict((payload or {}).get("decision_context", {}) or {})
        row.updated_at = datetime.utcnow()
        return row

    def _create_training_audit_event_row(
        self,
        session: Session,
        session_id: str,
        event_type: str,
        round_no: int = None,
        payload: dict = None,
    ) -> TrainingAuditEvent:
        """在给定事务里追加审计事件。"""
        row = TrainingAuditEvent(
            session_id=session_id,
            event_type=event_type,
            round_no=round_no,
            payload=payload or {},
        )
        session.add(row)
        return row

    def _create_media_task_row(
        self,
        *,
        session: Session,
        session_id: str,
        round_no: int,
        task_type: str,
        idempotency_key: str,
        request_payload: dict,
        max_retries: int = 0,
    ) -> TrainingMediaTask:
        """Create submit-round media task row inside the current transaction."""
        existing = (
            session.query(TrainingMediaTask)
            .filter(TrainingMediaTask.idempotency_key == idempotency_key)
            .first()
        )
        if existing is not None:
            if (
                str(existing.session_id) == str(session_id)
                and int(existing.round_no or 0) == int(round_no)
                and str(existing.task_type) == str(task_type)
            ):
                return existing
            raise DuplicateRoundSubmissionError(session_id=session_id, round_no=round_no)

        row = TrainingMediaTask(
            session_id=session_id,
            round_no=round_no,
            task_type=task_type,
            status="pending",
            idempotency_key=idempotency_key,
            request_payload=request_payload or {},
            retry_count=0,
            max_retries=int(max_retries or 0),
        )
        session.add(row)
        return row

    def _create_kt_observation_row(
        self,
        session: Session,
        session_id: str,
        round_no: int,
        payload: dict,
    ) -> KtObservation:
        """在给定事务里保存 KT 结构化观测。"""
        row = (
            session.query(KtObservation)
            .filter(
                KtObservation.session_id == session_id,
                KtObservation.round_no == round_no,
            )
            .first()
        )
        if row is None:
            row = KtObservation(session_id=session_id, round_no=round_no)
            session.add(row)

        row.scenario_id = str((payload or {}).get("scenario_id") or "")
        row.scenario_title = str((payload or {}).get("scenario_title") or "")
        row.training_mode = str((payload or {}).get("training_mode") or "guided")
        row.primary_skill_code = (payload or {}).get("primary_skill_code")
        row.primary_risk_flag = (payload or {}).get("primary_risk_flag")
        row.is_high_risk = bool((payload or {}).get("is_high_risk", False))
        row.target_skills = list((payload or {}).get("target_skills", []) or [])
        row.weak_skills_before = list((payload or {}).get("weak_skills_before", []) or [])
        row.risk_flags = list((payload or {}).get("risk_flags", []) or [])
        row.focus_tags = list((payload or {}).get("focus_tags", []) or [])
        row.evidence = list((payload or {}).get("evidence", []) or [])
        row.skill_observations = list((payload or {}).get("skill_observations", []) or [])
        row.state_observations = list((payload or {}).get("state_observations", []) or [])
        row.observation_summary = str((payload or {}).get("observation_summary") or "")
        row.raw_payload = dict(payload or {})
        return row
