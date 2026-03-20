"""Story session runtime manager."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace
import threading
import uuid
from typing import Any, Dict, Optional

from database.db_manager import DatabaseManager
from database.vector_db import VectorDatabase
from game.event_generator import EventGenerator
from game.story_engine import StoryEngine
from story.exceptions import StorySessionExpiredError, StorySessionNotFoundError
from story.story_store import DatabaseStoryStore, StoryRoundRecord, StorySnapshotRecord, StoryStoreProtocol
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_STORY_SESSION_TTL = timedelta(hours=24)
DEFAULT_STORY_STATE = {
    "favorability": 0.0,
    "trust": 0.0,
    "hostility": 0.0,
    "dependence": 0.0,
    "emotion": 50.0,
    "stress": 0.0,
    "anxiety": 0.0,
    "happiness": 50.0,
    "sadness": 0.0,
    "confidence": 50.0,
    "initiative": 50.0,
    "caution": 50.0,
}


class StorySessionStateAdapter:
    """Session-scoped state adapter.

    Transitional compatibility:
    1. Character profile and attributes still read from `DatabaseManager`
    2. Story runtime state no longer mutates the global `character_states` table
    3. Session snapshots become the restore source for story state
    """

    def __init__(
        self,
        *,
        base_db_manager: DatabaseManager | None = None,
        initial_state_payload: Optional[Dict[str, Any]] = None,
    ):
        self._base_db_manager = base_db_manager or DatabaseManager()
        self._state_payload = self._normalize_state_payload(initial_state_payload)
        self._state_seeded = bool(initial_state_payload)

    def get_character_states(self, character_id: int):
        payload = self.export_state_payload(character_id)
        return SimpleNamespace(**payload)

    def update_character_states(self, character_id: int, state_changes: dict):
        payload = self.export_state_payload(character_id)
        for key, delta in dict(state_changes or {}).items():
            if key not in DEFAULT_STORY_STATE:
                continue
            try:
                delta_value = float(delta)
            except (TypeError, ValueError):
                continue
            next_value = max(0.0, min(100.0, float(payload.get(key, 0.0)) + delta_value))
            payload[key] = next_value
        self._state_payload = payload
        self._state_seeded = True

    def export_state_payload(self, character_id: int) -> Dict[str, float]:
        if not self._state_seeded:
            self._state_payload = self._normalize_state_payload(
                self._read_base_state_payload(character_id)
            )
            self._state_seeded = True
        return dict(self._state_payload)

    def restore_state_payload(self, payload: Dict[str, Any] | None):
        self._state_payload = self._normalize_state_payload(payload)
        self._state_seeded = True

    def _read_base_state_payload(self, character_id: int) -> Dict[str, Any]:
        row = self._base_db_manager.get_character_states(character_id)
        if row is None:
            return dict(DEFAULT_STORY_STATE)
        return {
            key: float(getattr(row, key, DEFAULT_STORY_STATE[key]) or DEFAULT_STORY_STATE[key])
            for key in DEFAULT_STORY_STATE
        }

    @staticmethod
    def _normalize_state_payload(payload: Dict[str, Any] | None) -> Dict[str, float]:
        normalized = dict(DEFAULT_STORY_STATE)
        for key in DEFAULT_STORY_STATE:
            value = dict(payload or {}).get(key, DEFAULT_STORY_STATE[key])
            try:
                normalized[key] = float(value)
            except (TypeError, ValueError):
                normalized[key] = float(DEFAULT_STORY_STATE[key])
        return normalized

    def __getattr__(self, name: str):
        return getattr(self._base_db_manager, name)


class GameSession:
    """Story runtime session mirrored from persistent session facts."""

    def __init__(
        self,
        thread_id: str,
        user_id: str,
        character_id: int,
        game_mode: str,
        *,
        initial_state_payload: Optional[Dict[str, Any]] = None,
    ):
        self.thread_id = thread_id
        self.user_id = user_id
        self.character_id = character_id
        self.game_mode = game_mode

        logger.info("initializing story runtime session: thread_id=%s", thread_id)
        base_db_manager = DatabaseManager()
        self.db_manager = StorySessionStateAdapter(
            base_db_manager=base_db_manager,
            initial_state_payload=initial_state_payload,
        )
        self.vector_db = VectorDatabase()
        self.event_generator = EventGenerator(self.vector_db, self.db_manager)
        self.story_engine = StoryEngine(self.event_generator, self.db_manager)

        self.is_initialized = False
        self.current_round_no = 0
        self.current_dialogue_round = None
        self.lock = threading.RLock()

    def build_snapshot_payload(
        self,
        *,
        status: str,
        round_no: int,
        last_response: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "game_mode": self.game_mode,
            "status": status,
            "round_no": int(round_no),
            "is_initialized": bool(self.is_initialized),
            "current_dialogue_round": deepcopy(self.current_dialogue_round),
            "story_engine": {
                "current_event_count": int(getattr(self.story_engine, "current_event_count", 0) or 0),
                "current_event": deepcopy(getattr(self.story_engine, "current_event", None)),
                "dialogue_history": deepcopy(getattr(self.story_engine, "dialogue_history", [])),
                "current_scene": str(
                    getattr(self.story_engine, "current_scene", "") or ""
                ),
                "previous_event_contexts": list(
                    getattr(self.story_engine, "previous_event_contexts", []) or []
                ),
            },
            "current_states": self.db_manager.export_state_payload(self.character_id),
            "last_response": deepcopy(last_response or {}),
        }

    def restore_from_snapshot(self, snapshot_payload: Dict[str, Any] | None):
        payload = dict(snapshot_payload or {})
        self.is_initialized = bool(payload.get("is_initialized", False))
        self.current_round_no = int(payload.get("round_no", 0) or 0)
        self.current_dialogue_round = deepcopy(payload.get("current_dialogue_round"))
        story_engine_payload = dict(payload.get("story_engine") or {})
        self.story_engine.current_event_count = int(
            story_engine_payload.get("current_event_count", 0) or 0
        )
        self.story_engine.current_event = deepcopy(story_engine_payload.get("current_event"))
        self.story_engine.dialogue_history = list(
            story_engine_payload.get("dialogue_history") or []
        )
        if story_engine_payload.get("current_scene"):
            self.story_engine.current_scene = str(story_engine_payload.get("current_scene"))
        self.story_engine.previous_event_contexts = list(
            story_engine_payload.get("previous_event_contexts") or []
        )
        self.db_manager.restore_state_payload(payload.get("current_states"))


class GameSessionManager:
    """Persistent story session manager.

    Source of truth:
    1. `story_sessions` / `story_rounds` / `story_snapshots`
    2. In-process cache is only a runtime mirror
    """

    def __init__(
        self,
        *,
        story_store: StoryStoreProtocol | None = None,
        session_ttl: timedelta | None = None,
    ):
        self.story_store = story_store or DatabaseStoryStore()
        self.session_ttl = session_ttl or DEFAULT_STORY_SESSION_TTL
        self._runtime_sessions: Dict[str, GameSession] = {}

    def create_session(
        self,
        user_id: Optional[str],
        character_id: int,
        game_mode: str,
    ) -> GameSession:
        thread_id = str(uuid.uuid4())
        resolved_user_id = user_id or str(uuid.uuid4())
        session = GameSession(
            thread_id=thread_id,
            user_id=resolved_user_id,
            character_id=character_id,
            game_mode=game_mode,
        )
        self.story_store.create_story_session(
            thread_id=thread_id,
            user_id=resolved_user_id,
            character_id=character_id,
            game_mode=game_mode,
            status="initialized",
            expires_at=self._next_expiration(),
        )
        self._runtime_sessions[thread_id] = session
        return session

    def get_session(self, thread_id: str) -> Optional[GameSession]:
        session_record = self.get_session_record(thread_id)
        if session_record is None:
            return None
        if session_record.is_expired():
            self.story_store.mark_story_session_expired(thread_id)
            self.evict_runtime_session(thread_id)
            raise StorySessionExpiredError(thread_id=thread_id)

        cached = self._runtime_sessions.get(thread_id)
        if cached is not None:
            latest_round_no = int(
                session_record.latest_snapshot_round_no
                if session_record.latest_snapshot_round_no is not None
                else session_record.current_round_no
                or 0
            )
            if latest_round_no > int(getattr(cached, "current_round_no", 0) or 0):
                latest_snapshot = self.story_store.get_latest_story_snapshot(thread_id)
                if latest_snapshot is not None:
                    cached.restore_from_snapshot(latest_snapshot.snapshot_payload)
            return cached

        restored = GameSession(
            thread_id=session_record.thread_id,
            user_id=session_record.user_id,
            character_id=session_record.character_id,
            game_mode=session_record.game_mode,
        )
        latest_snapshot = self.story_store.get_latest_story_snapshot(thread_id)
        if latest_snapshot is not None:
            restored.restore_from_snapshot(latest_snapshot.snapshot_payload)
        else:
            restored.is_initialized = bool(session_record.is_initialized)
            restored.current_round_no = int(session_record.current_round_no or 0)
        self._runtime_sessions[thread_id] = restored
        return restored

    def get_session_or_raise(self, thread_id: str) -> GameSession:
        session = self.get_session(thread_id)
        if session is None:
            raise StorySessionNotFoundError(thread_id=thread_id)
        return session

    def get_session_record(self, thread_id: str):
        return self.story_store.get_story_session(thread_id)

    def list_story_sessions(self, *, user_id: str, limit: int = 10):
        return self.story_store.list_story_sessions_by_user(user_id, limit)

    def get_story_round(self, thread_id: str, round_no: int) -> StoryRoundRecord | None:
        return self.story_store.get_story_round_by_thread_round(thread_id, round_no)

    def get_story_rounds(self, thread_id: str) -> list[StoryRoundRecord]:
        return self.story_store.get_story_rounds(thread_id)

    def get_latest_snapshot(self, thread_id: str) -> StorySnapshotRecord | None:
        snapshot = self.story_store.get_latest_story_snapshot(thread_id)
        if snapshot is None:
            return None
        session_record = self.get_session_record(thread_id)
        if session_record is not None:
            snapshot.expires_at = session_record.expires_at
        return snapshot

    def save_story_snapshot(
        self,
        *,
        session: GameSession,
        round_no: int,
        response_payload: dict,
        status: str,
    ) -> StorySnapshotRecord:
        snapshot = self.story_store.save_story_snapshot(
            thread_id=session.thread_id,
            round_no=round_no,
            snapshot_payload=session.build_snapshot_payload(
                status=status,
                round_no=round_no,
                last_response=response_payload,
            ),
            response_payload=response_payload,
            status=status,
            current_scene_id=self._resolve_scene_id(response_payload, session),
            is_initialized=bool(session.is_initialized),
            expires_at=self._next_expiration(),
        )
        session_record = self.get_session_record(session.thread_id)
        if session_record is not None:
            snapshot.expires_at = session_record.expires_at
        session.current_round_no = round_no
        return snapshot

    def save_story_round(
        self,
        *,
        session: GameSession,
        round_no: int,
        request_payload: dict,
        response_payload: dict,
        user_input_raw: str,
        option_id: int | None,
        state_before: dict,
        status: str,
    ) -> StorySnapshotRecord:
        input_kind = "option" if option_id is not None else "free_text"
        self.story_store.save_story_round_artifacts(
            thread_id=session.thread_id,
            round_no=round_no,
            input_kind=input_kind,
            user_input_raw=user_input_raw,
            selected_option_index=option_id,
            request_payload=request_payload,
            response_payload=response_payload,
            state_before=state_before,
            state_after=session.db_manager.export_state_payload(session.character_id),
            snapshot_payload=session.build_snapshot_payload(
                status=status,
                round_no=round_no,
                last_response=response_payload,
            ),
            status=status,
            current_scene_id=self._resolve_scene_id(response_payload, session),
            expires_at=self._next_expiration(),
        )
        snapshot = self.get_latest_snapshot(session.thread_id)
        if snapshot is None:
            raise StorySessionNotFoundError(thread_id=session.thread_id)
        session.current_round_no = round_no
        return snapshot

    def reload_session(self, thread_id: str) -> Optional[GameSession]:
        self.evict_runtime_session(thread_id)
        try:
            return self.get_session(thread_id)
        except StorySessionExpiredError:
            return None

    def evict_runtime_session(self, thread_id: str):
        self._runtime_sessions.pop(thread_id, None)

    def get_cached_session_ids(self) -> list[str]:
        return list(self._runtime_sessions.keys())

    def _next_expiration(self) -> datetime:
        return datetime.utcnow() + self.session_ttl

    @staticmethod
    def _resolve_scene_id(response_payload: dict, session: GameSession) -> str | None:
        return (
            dict(response_payload or {}).get("scene")
            or getattr(session.story_engine, "current_scene", None)
        )
