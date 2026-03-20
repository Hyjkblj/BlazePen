"""Story-history query service.

Read-only query assembly for PR-BE-05. This service only reads persisted
story facts and must not mutate or restore the live runtime session.
"""

from __future__ import annotations

from typing import Any, Dict

from story.exceptions import StorySessionNotFoundError
from utils.logger import get_logger

logger = get_logger(__name__)


class StoryHistoryService:
    """Own story history read models built from persisted rounds."""

    def __init__(self, *, session_manager):
        self.session_manager = session_manager

    def get_story_history(self, thread_id: str) -> Dict[str, Any]:
        logger.info("story history requested: thread_id=%s", thread_id)

        session_record = self.session_manager.get_session_record(thread_id)
        if session_record is None:
            raise StorySessionNotFoundError(thread_id=thread_id)

        rounds = self.session_manager.get_story_rounds(thread_id)
        latest_snapshot = self.session_manager.get_latest_snapshot(thread_id)

        history_items = [self._build_history_item(round_record) for round_record in rounds]
        return {
            "thread_id": thread_id,
            "status": self._resolve_effective_status(session_record),
            "current_round_no": int(getattr(session_record, "current_round_no", 0) or 0),
            "latest_scene": getattr(session_record, "current_scene_id", None),
            "updated_at": self._isoformat(getattr(session_record, "updated_at", None)),
            "expires_at": self._isoformat(getattr(session_record, "expires_at", None)),
            "history": history_items,
            "latest_snapshot": latest_snapshot.to_summary() if latest_snapshot is not None else None,
        }

    def _build_history_item(self, round_record) -> Dict[str, Any]:
        response_payload = dict(getattr(round_record, "response_payload", {}) or {})
        state_before = dict(getattr(round_record, "state_before", {}) or {})
        state_after = dict(getattr(round_record, "state_after", {}) or {})

        return {
            "round_no": int(getattr(round_record, "round_no", 0) or 0),
            "status": str(getattr(round_record, "status", "in_progress") or "in_progress"),
            "scene": response_payload.get("scene"),
            "event_title": response_payload.get("event_title"),
            "character_dialogue": response_payload.get("character_dialogue"),
            "user_action": self._build_user_action(round_record),
            "state_summary": {
                "changes": self._build_state_changes(state_before, state_after),
                "current_states": response_payload.get("current_states") or state_after,
            },
            "is_event_finished": bool(response_payload.get("is_event_finished", False)),
            "is_game_finished": bool(response_payload.get("is_game_finished", False)),
            "created_at": self._isoformat(getattr(round_record, "created_at", None)),
        }

    @staticmethod
    def _build_user_action(round_record) -> Dict[str, Any]:
        request_payload = dict(getattr(round_record, "request_payload", {}) or {})
        selected_option = dict(request_payload.get("selected_option") or {})
        input_kind = str(getattr(round_record, "input_kind", "free_text") or "free_text")
        raw_input = str(
            getattr(round_record, "user_input_raw", "")
            or request_payload.get("user_input")
            or ""
        )
        option_index = getattr(round_record, "selected_option_index", None)
        option_text = selected_option.get("text")
        option_type = selected_option.get("type")

        summary = raw_input
        if input_kind == "option":
            summary = (
                str(option_text)
                if option_text not in (None, "")
                else StoryHistoryService._fallback_option_summary(option_index)
            )

        return {
            "kind": input_kind,
            "summary": summary,
            "raw_input": raw_input or None,
            "option_index": option_index,
            "option_text": option_text,
            "option_type": option_type,
        }

    @staticmethod
    def _build_state_changes(state_before: Dict[str, Any], state_after: Dict[str, Any]) -> Dict[str, float]:
        changes: Dict[str, float] = {}
        for key, after_value in dict(state_after or {}).items():
            try:
                before_number = float(dict(state_before or {}).get(key, 0.0) or 0.0)
                after_number = float(after_value or 0.0)
            except (TypeError, ValueError):
                continue
            delta = after_number - before_number
            if abs(delta) > 1e-9:
                changes[key] = delta
        return changes

    @staticmethod
    def _resolve_effective_status(session_record) -> str:
        if session_record is None:
            return "missing"
        if session_record.is_expired():
            return "expired"
        return str(getattr(session_record, "status", "initialized") or "initialized")

    @staticmethod
    def _fallback_option_summary(option_index: int | None) -> str:
        if option_index is None:
            return ""
        return f"\u9009\u9879 {int(option_index) + 1}"

    @staticmethod
    def _isoformat(value) -> str | None:
        return value.isoformat() if value is not None else None
