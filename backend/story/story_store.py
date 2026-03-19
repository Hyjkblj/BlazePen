"""Story-domain storage adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Protocol

from story.story_repository import SqlAlchemyStoryRepository


@dataclass(slots=True)
class StorySessionRecord:
    """Stable story session read model."""

    thread_id: str
    user_id: str
    character_id: int
    game_mode: str = "solo"
    status: str = "initialized"
    current_round_no: int = 0
    current_scene_id: str | None = None
    latest_snapshot_round_no: int | None = None
    is_initialized: bool = False
    session_meta: Dict[str, Any] = field(default_factory=dict)
    expires_at: datetime | None = None
    last_active_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_expired(self, now: datetime | None = None) -> bool:
        current_time = now or datetime.utcnow()
        return self.status == "expired" or (
            self.expires_at is not None and self.expires_at <= current_time
        )


@dataclass(slots=True)
class StoryRoundRecord:
    """Stable story round read model."""

    round_id: str
    thread_id: str
    round_no: int
    input_kind: str = "free_text"
    user_input_raw: str = ""
    selected_option_index: int | None = None
    request_payload: Dict[str, Any] = field(default_factory=dict)
    response_payload: Dict[str, Any] = field(default_factory=dict)
    state_before: Dict[str, Any] = field(default_factory=dict)
    state_after: Dict[str, Any] = field(default_factory=dict)
    status: str = "in_progress"
    created_at: datetime | None = None


@dataclass(slots=True)
class StorySnapshotRecord:
    """Stable story snapshot read model."""

    snapshot_id: str
    thread_id: str
    round_no: int
    status: str = "initialized"
    current_scene_id: str | None = None
    snapshot_payload: Dict[str, Any] = field(default_factory=dict)
    response_payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    expires_at: datetime | None = None

    def to_summary(self) -> Dict[str, Any]:
        response_payload = dict(self.response_payload or {})
        snapshot_payload = dict(self.snapshot_payload or {})
        return {
            "thread_id": self.thread_id,
            "status": self.status,
            "round_no": int(self.round_no),
            "scene": self.current_scene_id or response_payload.get("scene"),
            "event_title": response_payload.get("event_title"),
            "current_states": dict(
                snapshot_payload.get("current_states")
                or response_payload.get("current_states")
                or {}
            ),
            "is_event_finished": bool(response_payload.get("is_event_finished", False)),
            "is_game_finished": bool(response_payload.get("is_game_finished", False)),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class StoryStoreProtocol(Protocol):
    """Minimal story persistence interface used by the runtime layer."""

    def create_story_session(
        self,
        *,
        thread_id: str,
        user_id: str,
        character_id: int,
        game_mode: str,
        status: str,
        expires_at: datetime | None,
    ) -> StorySessionRecord:
        ...

    def get_story_session(self, thread_id: str) -> StorySessionRecord | None:
        ...

    def update_story_session(self, thread_id: str, updates: dict) -> StorySessionRecord | None:
        ...

    def mark_story_session_expired(self, thread_id: str) -> StorySessionRecord | None:
        ...

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
    ) -> StorySnapshotRecord:
        ...

    def get_latest_story_snapshot(self, thread_id: str) -> StorySnapshotRecord | None:
        ...

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
    ) -> StoryRoundRecord:
        ...

    def get_story_round_by_thread_round(self, thread_id: str, round_no: int) -> StoryRoundRecord | None:
        ...

    def get_story_rounds(self, thread_id: str) -> List[StoryRoundRecord]:
        ...


class DatabaseStoryStore:
    """Adapt repository rows into stable story-domain records."""

    def __init__(self, storage_backend: Any = None):
        self.storage_backend = storage_backend or SqlAlchemyStoryRepository()

    def create_story_session(
        self,
        *,
        thread_id: str,
        user_id: str,
        character_id: int,
        game_mode: str,
        status: str = "initialized",
        expires_at: datetime | None = None,
    ) -> StorySessionRecord:
        row = self.storage_backend.create_story_session(
            thread_id=thread_id,
            user_id=user_id,
            character_id=character_id,
            game_mode=game_mode,
            status=status,
            expires_at=expires_at,
        )
        return self._to_story_session_record(row)

    def get_story_session(self, thread_id: str) -> StorySessionRecord | None:
        return self._to_story_session_record(self.storage_backend.get_story_session(thread_id))

    def update_story_session(self, thread_id: str, updates: dict) -> StorySessionRecord | None:
        return self._to_story_session_record(
            self.storage_backend.update_story_session(thread_id, updates)
        )

    def mark_story_session_expired(self, thread_id: str) -> StorySessionRecord | None:
        return self._to_story_session_record(
            self.storage_backend.mark_story_session_expired(thread_id)
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
    ) -> StorySnapshotRecord:
        row = self.storage_backend.save_story_snapshot(
            thread_id=thread_id,
            round_no=round_no,
            snapshot_payload=snapshot_payload,
            response_payload=response_payload,
            status=status,
            current_scene_id=current_scene_id,
            is_initialized=is_initialized,
            expires_at=expires_at,
        )
        return self._to_story_snapshot_record(row)

    def get_latest_story_snapshot(self, thread_id: str) -> StorySnapshotRecord | None:
        return self._to_story_snapshot_record(
            self.storage_backend.get_latest_story_snapshot(thread_id)
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
    ) -> StoryRoundRecord:
        row = self.storage_backend.save_story_round_artifacts(
            thread_id=thread_id,
            round_no=round_no,
            input_kind=input_kind,
            user_input_raw=user_input_raw,
            selected_option_index=selected_option_index,
            request_payload=request_payload,
            response_payload=response_payload,
            state_before=state_before,
            state_after=state_after,
            snapshot_payload=snapshot_payload,
            status=status,
            current_scene_id=current_scene_id,
            expires_at=expires_at,
        )
        return self._to_story_round_record(row)

    def get_story_round_by_thread_round(self, thread_id: str, round_no: int) -> StoryRoundRecord | None:
        return self._to_story_round_record(
            self.storage_backend.get_story_round_by_thread_round(thread_id, round_no)
        )

    def get_story_rounds(self, thread_id: str) -> List[StoryRoundRecord]:
        return [
            self._to_story_round_record(row)
            for row in self.storage_backend.get_story_rounds(thread_id)
        ]

    @staticmethod
    def _to_story_session_record(row: Any) -> StorySessionRecord | None:
        if row is None:
            return None
        return StorySessionRecord(
            thread_id=str(getattr(row, "thread_id", "")),
            user_id=str(getattr(row, "user_id", "")),
            character_id=int(getattr(row, "character_id", 0) or 0),
            game_mode=str(getattr(row, "game_mode", "solo") or "solo"),
            status=str(getattr(row, "status", "initialized") or "initialized"),
            current_round_no=int(getattr(row, "current_round_no", 0) or 0),
            current_scene_id=getattr(row, "current_scene_id", None),
            latest_snapshot_round_no=getattr(row, "latest_snapshot_round_no", None),
            is_initialized=bool(getattr(row, "is_initialized", False)),
            session_meta=dict(getattr(row, "session_meta", {}) or {}),
            expires_at=getattr(row, "expires_at", None),
            last_active_at=getattr(row, "last_active_at", None),
            created_at=getattr(row, "created_at", None),
            updated_at=getattr(row, "updated_at", None),
        )

    @staticmethod
    def _to_story_round_record(row: Any) -> StoryRoundRecord | None:
        if row is None:
            return None
        return StoryRoundRecord(
            round_id=str(getattr(row, "round_id", "")),
            thread_id=str(getattr(row, "thread_id", "")),
            round_no=int(getattr(row, "round_no", 0) or 0),
            input_kind=str(getattr(row, "input_kind", "free_text") or "free_text"),
            user_input_raw=str(getattr(row, "user_input_raw", "") or ""),
            selected_option_index=getattr(row, "selected_option_index", None),
            request_payload=dict(getattr(row, "request_payload", {}) or {}),
            response_payload=dict(getattr(row, "response_payload", {}) or {}),
            state_before=dict(getattr(row, "state_before", {}) or {}),
            state_after=dict(getattr(row, "state_after", {}) or {}),
            status=str(getattr(row, "status", "in_progress") or "in_progress"),
            created_at=getattr(row, "created_at", None),
        )

    @staticmethod
    def _to_story_snapshot_record(row: Any) -> StorySnapshotRecord | None:
        if row is None:
            return None
        return StorySnapshotRecord(
            snapshot_id=str(getattr(row, "snapshot_id", "")),
            thread_id=str(getattr(row, "thread_id", "")),
            round_no=int(getattr(row, "round_no", 0) or 0),
            status=str(getattr(row, "status", "initialized") or "initialized"),
            current_scene_id=getattr(row, "current_scene_id", None),
            snapshot_payload=dict(getattr(row, "snapshot_payload", {}) or {}),
            response_payload=dict(getattr(row, "response_payload", {}) or {}),
            created_at=getattr(row, "created_at", None),
            updated_at=getattr(row, "updated_at", None),
            expires_at=getattr(row, "expires_at", None)
            if hasattr(row, "expires_at")
            else None,
        )
