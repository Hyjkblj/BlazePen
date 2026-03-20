"""SQLAlchemy repository for story-domain persistence."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from database.integrity import is_unique_constraint_conflict
from database.session_factory import get_engine, get_session_factory
from models.story import StoryRound, StorySession, StorySnapshot
from story.exceptions import DuplicateStoryRoundSubmissionError, StorySessionNotFoundError


class SqlAlchemyStoryRepository:
    """Story-domain repository backed by SQLAlchemy."""

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

    def create_story_session(
        self,
        *,
        thread_id: str,
        user_id: str,
        character_id: int,
        game_mode: str,
        status: str = "initialized",
        expires_at: datetime | None = None,
    ) -> StorySession:
        with self.get_session() as session:
            row = StorySession(
                thread_id=thread_id,
                user_id=user_id,
                character_id=character_id,
                game_mode=game_mode,
                status=status,
                expires_at=expires_at,
                last_active_at=datetime.utcnow(),
            )
            session.add(row)
            session.flush()
            return row

    def get_story_session(self, thread_id: str) -> StorySession | None:
        with self.get_session() as session:
            return (
                session.query(StorySession)
                .filter(StorySession.thread_id == thread_id)
                .first()
            )

    def list_story_sessions_by_user(self, user_id: str, limit: int = 10) -> list[StorySession]:
        with self.get_session() as session:
            return (
                session.query(StorySession)
                .filter(StorySession.user_id == user_id)
                .order_by(
                    StorySession.last_active_at.desc(),
                    StorySession.updated_at.desc(),
                    StorySession.created_at.desc(),
                )
                .limit(limit)
                .all()
            )

    def update_story_session(self, thread_id: str, updates: dict) -> StorySession | None:
        with self.get_session() as session:
            row = (
                session.query(StorySession)
                .filter(StorySession.thread_id == thread_id)
                .first()
            )
            if row is None:
                return None
            for key, value in updates.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            row.updated_at = datetime.utcnow()
            session.flush()
            return row

    def mark_story_session_expired(self, thread_id: str) -> StorySession | None:
        return self.update_story_session(
            thread_id,
            {
                "status": "expired",
                "updated_at": datetime.utcnow(),
            },
        )

    def save_story_snapshot(
        self,
        *,
        thread_id: str,
        round_no: int,
        snapshot_payload: dict,
        response_payload: dict,
        status: str,
        current_scene_id: str | None,
        is_initialized: bool,
        expires_at: datetime | None,
    ) -> StorySnapshot:
        with self.get_session() as session:
            session_row = (
                session.query(StorySession)
                .filter(StorySession.thread_id == thread_id)
                .first()
            )
            if session_row is None:
                raise StorySessionNotFoundError(thread_id=thread_id)

            snapshot_row = self._upsert_story_snapshot_row(
                session=session,
                thread_id=thread_id,
                round_no=round_no,
                snapshot_payload=snapshot_payload,
                response_payload=response_payload,
                status=status,
                current_scene_id=current_scene_id,
            )

            session_row.status = status
            session_row.current_round_no = max(int(session_row.current_round_no or 0), int(round_no))
            session_row.current_scene_id = current_scene_id
            session_row.latest_snapshot_round_no = round_no
            session_row.is_initialized = bool(is_initialized)
            session_row.last_active_at = datetime.utcnow()
            session_row.updated_at = datetime.utcnow()
            session_row.expires_at = expires_at
            session.flush()
            return snapshot_row

    def get_latest_story_snapshot(self, thread_id: str) -> StorySnapshot | None:
        with self.get_session() as session:
            return (
                self._latest_story_snapshot_query(session)
                .filter(StorySession.thread_id == thread_id)
                .first()
            )

    def get_latest_story_snapshots(self, thread_ids: list[str]) -> list[StorySnapshot]:
        if not thread_ids:
            return []

        with self.get_session() as session:
            return (
                self._latest_story_snapshot_query(session)
                .filter(StorySession.thread_id.in_(thread_ids))
                .order_by(StorySession.thread_id.asc())
                .all()
            )

    def save_story_round_artifacts(
        self,
        *,
        thread_id: str,
        round_no: int,
        input_kind: str,
        user_input_raw: str,
        selected_option_index: int | None,
        request_payload: dict,
        response_payload: dict,
        state_before: dict,
        state_after: dict,
        snapshot_payload: dict,
        status: str,
        current_scene_id: str | None,
        expires_at: datetime | None,
    ) -> StoryRound:
        with self.get_session() as session:
            session_row = (
                session.query(StorySession)
                .filter(StorySession.thread_id == thread_id)
                .first()
            )
            if session_row is None:
                raise StorySessionNotFoundError(thread_id=thread_id)

            round_row = StoryRound(
                thread_id=thread_id,
                round_no=round_no,
                input_kind=input_kind,
                user_input_raw=user_input_raw,
                selected_option_index=selected_option_index,
                request_payload=request_payload or {},
                response_payload=response_payload or {},
                state_before=state_before or {},
                state_after=state_after or {},
                status=status,
            )
            session.add(round_row)
            try:
                session.flush()
            except IntegrityError as exc:
                if self._is_duplicate_round_conflict(exc):
                    raise DuplicateStoryRoundSubmissionError(
                        thread_id=thread_id,
                        round_no=round_no,
                    ) from exc
                raise

            self._upsert_story_snapshot_row(
                session=session,
                thread_id=thread_id,
                round_no=round_no,
                snapshot_payload=snapshot_payload,
                response_payload=response_payload,
                status=status,
                current_scene_id=current_scene_id,
            )

            session_row.current_round_no = round_no
            session_row.current_scene_id = current_scene_id
            session_row.latest_snapshot_round_no = round_no
            session_row.status = status
            session_row.is_initialized = True
            session_row.last_active_at = datetime.utcnow()
            session_row.updated_at = datetime.utcnow()
            session_row.expires_at = expires_at
            session.flush()
            return round_row

    def get_story_round_by_thread_round(self, thread_id: str, round_no: int) -> StoryRound | None:
        with self.get_session() as session:
            return (
                session.query(StoryRound)
                .filter(
                    StoryRound.thread_id == thread_id,
                    StoryRound.round_no == round_no,
                )
                .first()
            )

    def get_story_rounds(self, thread_id: str) -> list[StoryRound]:
        with self.get_session() as session:
            return (
                session.query(StoryRound)
                .filter(StoryRound.thread_id == thread_id)
                .order_by(StoryRound.round_no.asc())
                .all()
            )

    @staticmethod
    def _is_duplicate_round_conflict(exc: IntegrityError) -> bool:
        return is_unique_constraint_conflict(
            exc,
            constraint_name="uq_story_rounds_thread_round",
            fallback_token_groups=(
                ("story_rounds", "thread_id", "round_no"),
                ("duplicate key", "story_rounds"),
            ),
        )

    @staticmethod
    def _upsert_story_snapshot_row(
        *,
        session,
        thread_id: str,
        round_no: int,
        snapshot_payload: dict,
        response_payload: dict,
        status: str,
        current_scene_id: str | None,
    ) -> StorySnapshot:
        row = (
            session.query(StorySnapshot)
            .filter(
                StorySnapshot.thread_id == thread_id,
                StorySnapshot.round_no == round_no,
            )
            .first()
        )
        if row is None:
            row = StorySnapshot(
                thread_id=thread_id,
                round_no=round_no,
            )
            session.add(row)
        row.status = status
        row.current_scene_id = current_scene_id
        row.snapshot_payload = snapshot_payload or {}
        row.response_payload = response_payload or {}
        row.updated_at = datetime.utcnow()
        session.flush()
        return row

    @staticmethod
    def _latest_story_snapshot_query(session):
        """Return the authoritative latest snapshot query.

        The single fact source for "latest snapshot" is
        `story_sessions.latest_snapshot_round_no`. Query code should not
        rescan snapshot history and infer latest rows from max(round_no).
        """

        return (
            session.query(StorySnapshot)
            .join(
                StorySession,
                (StorySession.thread_id == StorySnapshot.thread_id)
                & (StorySession.latest_snapshot_round_no == StorySnapshot.round_no),
            )
            .filter(StorySession.latest_snapshot_round_no.isnot(None))
        )
