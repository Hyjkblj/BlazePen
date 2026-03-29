"""Training character preview job SQLAlchemy repository."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import case
from sqlalchemy.exc import IntegrityError

from database.integrity import is_unique_constraint_conflict
from database.session_factory import get_engine, get_session_factory
from models.training import TrainingCharacterPreviewJob


class SqlAlchemyTrainingCharacterPreviewJobRepository:
    """Repository for persisted training character preview jobs."""

    def __init__(self, engine=None, session_factory=None):
        self.engine = engine or get_engine()
        self.SessionLocal = session_factory or get_session_factory()

    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_preview_job(
        self,
        *,
        character_id: int,
        idempotency_key: str,
        request_payload: dict,
        request_payload_canonical: str,
    ) -> TrainingCharacterPreviewJob:
        with self.get_session() as session:
            row = TrainingCharacterPreviewJob(
                character_id=int(character_id),
                idempotency_key=str(idempotency_key or "").strip(),
                request_payload=dict(request_payload or {}),
                request_payload_canonical=str(request_payload_canonical or "").strip(),
                status="pending",
                image_urls=[],
                error_message=None,
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as exc:
                if self._is_duplicate_preview_job_conflict(exc):
                    session.rollback()
                    existing = (
                        session.query(TrainingCharacterPreviewJob)
                        .filter(TrainingCharacterPreviewJob.idempotency_key == row.idempotency_key)
                        .first()
                    )
                    if existing is not None:
                        return existing
                raise
            return row

    def get_preview_job(self, job_id: str) -> TrainingCharacterPreviewJob | None:
        with self.get_session() as session:
            return (
                session.query(TrainingCharacterPreviewJob)
                .filter(TrainingCharacterPreviewJob.job_id == str(job_id or "").strip())
                .first()
            )

    def get_preview_job_by_idempotency_key(self, idempotency_key: str) -> TrainingCharacterPreviewJob | None:
        with self.get_session() as session:
            return (
                session.query(TrainingCharacterPreviewJob)
                .filter(TrainingCharacterPreviewJob.idempotency_key == str(idempotency_key or "").strip())
                .first()
            )

    def list_preview_jobs_by_status(self, statuses: list[str]) -> list[TrainingCharacterPreviewJob]:
        normalized_statuses = [
            str(item or "").strip().lower()
            for item in statuses or []
            if str(item or "").strip()
        ]
        if not normalized_statuses:
            return []

        with self.get_session() as session:
            return (
                session.query(TrainingCharacterPreviewJob)
                .filter(TrainingCharacterPreviewJob.status.in_(normalized_statuses))
                .order_by(TrainingCharacterPreviewJob.created_at.asc())
                .all()
            )

    def claim_preview_job(self, job_id: str) -> TrainingCharacterPreviewJob | None:
        normalized_job_id = str(job_id or "").strip()
        if not normalized_job_id:
            return None

        with self.get_session() as session:
            now = datetime.utcnow()
            updated = (
                session.query(TrainingCharacterPreviewJob)
                .filter(
                    TrainingCharacterPreviewJob.job_id == normalized_job_id,
                    TrainingCharacterPreviewJob.status == "pending",
                )
                .update(
                    {
                        TrainingCharacterPreviewJob.status: "running",
                        TrainingCharacterPreviewJob.started_at: case(
                            (TrainingCharacterPreviewJob.started_at.is_(None), now),
                            else_=TrainingCharacterPreviewJob.started_at,
                        ),
                        TrainingCharacterPreviewJob.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            if updated <= 0:
                return None

            session.flush()
            return (
                session.query(TrainingCharacterPreviewJob)
                .filter(TrainingCharacterPreviewJob.job_id == normalized_job_id)
                .first()
            )

    def update_preview_job(self, job_id: str, updates: dict) -> TrainingCharacterPreviewJob | None:
        normalized_job_id = str(job_id or "").strip()
        if not normalized_job_id:
            return None

        with self.get_session() as session:
            row = (
                session.query(TrainingCharacterPreviewJob)
                .filter(TrainingCharacterPreviewJob.job_id == normalized_job_id)
                .first()
            )
            if row is None:
                return None

            for key, value in (updates or {}).items():
                if hasattr(row, key):
                    setattr(row, key, value)
            row.updated_at = datetime.utcnow()
            session.flush()
            return row

    def complete_preview_job(
        self,
        job_id: str,
        *,
        status: str,
        image_urls: list[str] | None = None,
        error_message: str | None = None,
    ) -> TrainingCharacterPreviewJob | None:
        normalized_job_id = str(job_id or "").strip()
        if not normalized_job_id:
            return None

        with self.get_session() as session:
            row = (
                session.query(TrainingCharacterPreviewJob)
                .filter(TrainingCharacterPreviewJob.job_id == normalized_job_id)
                .first()
            )
            if row is None:
                return None

            now = datetime.utcnow()
            row.status = str(status or row.status).strip() or row.status
            if image_urls is not None:
                row.image_urls = list(image_urls)
            row.error_message = str(error_message or "").strip() or None
            row.finished_at = now
            row.updated_at = now
            session.flush()
            return row

    @staticmethod
    def _is_duplicate_preview_job_conflict(exc: IntegrityError) -> bool:
        return is_unique_constraint_conflict(
            exc,
            constraint_name="uq_training_character_preview_jobs_idempotency_key",
            fallback_token_groups=(
                ("training_character_preview_jobs", "idempotency_key"),
                ("duplicate key", "training_character_preview_jobs"),
            ),
        )
