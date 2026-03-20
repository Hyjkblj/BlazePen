"""Story-ending domain service."""

from __future__ import annotations

from typing import Any, Dict

from story.exceptions import StorySessionExpiredError, StorySessionNotFoundError
from story.story_asset_service import StoryAssetService
from story.story_response_utils import attach_snapshot_metadata, states_to_payload


class StoryEndingService:
    """Own story ending detection and completion payloads."""

    _ENDING_DESCRIPTIONS = {
        "good_ending": "\u7ecf\u8fc7\u4e00\u7cfb\u5217\u4e8b\u4ef6\uff0c\u4f60\u4eec\u7684\u5173\u7cfb\u53d8\u5f97\u66f4\u52a0\u4eb2\u5bc6\u3002",
        "bad_ending": "\u5173\u7cfb\u8d70\u5411\u4e86\u4e0d\u597d\u7684\u65b9\u5411\uff0c\u5f7c\u6b64\u8ddd\u79bb\u8d8a\u6765\u8d8a\u8fdc\u3002",
        "neutral_ending": "\u5173\u7cfb\u4fdd\u6301\u7a33\u5b9a\uff0c\u672a\u6765\u4ecd\u6709\u66f4\u591a\u53ef\u80fd\u3002",
        "open_ending": "\u6545\u4e8b\u4ecd\u5728\u5ef6\u5c55\uff0c\u6700\u7ec8\u7ed3\u5c40\u5c1a\u672a\u5b8c\u5168\u786e\u5b9a\u3002",
        "completed": "\u6545\u4e8b\u5df2\u5b8c\u6210\u3002",
    }

    def __init__(self, *, session_manager, story_asset_service: StoryAssetService | None = None):
        self.session_manager = session_manager
        self.story_asset_service = story_asset_service or StoryAssetService()

    def check_ending(self, thread_id: str) -> Dict[str, Any]:
        """Legacy compatibility read backed by persisted ending facts."""

        ending_summary = self.get_ending_summary(thread_id)
        if ending_summary.get("status") == "expired" and not ending_summary.get("has_ending", False):
            raise StorySessionExpiredError(thread_id=thread_id)

        ending_payload = dict(ending_summary.get("ending") or {})
        if not ending_summary.get("has_ending") or not ending_payload:
            return {
                "has_ending": False,
                "ending": None,
            }

        key_states = dict(ending_payload.get("key_states") or {})
        return {
            "has_ending": True,
            "ending": {
                "type": ending_payload.get("type"),
                "description": ending_payload.get("description"),
                "favorability": key_states.get("favorability"),
                "trust": key_states.get("trust"),
                "hostility": key_states.get("hostility"),
            },
        }

    def get_ending_summary(self, thread_id: str) -> Dict[str, Any]:
        session_record = self.session_manager.get_session_record(thread_id)
        if session_record is None:
            raise StorySessionNotFoundError(thread_id=thread_id)

        latest_snapshot = self.session_manager.get_latest_snapshot(thread_id)
        snapshot_summary = latest_snapshot.to_summary() if latest_snapshot is not None else {}
        response_payload = dict(getattr(latest_snapshot, "response_payload", {}) or {})
        current_states = dict(
            snapshot_summary.get("current_states")
            or response_payload.get("current_states")
            or {}
        )
        effective_status = self._resolve_effective_status(session_record)
        has_ending = bool(response_payload.get("is_game_finished", False) or effective_status == "completed")

        ending = None
        if has_ending:
            ending = self._build_ending_payload(
                ending_type=response_payload.get("ending_type"),
                current_states=current_states,
                scene=response_payload.get("scene")
                or snapshot_summary.get("scene")
                or getattr(session_record, "current_scene_id", None),
                event_title=response_payload.get("event_title"),
            )

        return {
            "thread_id": thread_id,
            "status": effective_status,
            "round_no": int(
                getattr(latest_snapshot, "round_no", None)
                if latest_snapshot is not None
                else getattr(session_record, "current_round_no", 0)
                or 0
            ),
            "has_ending": has_ending,
            "ending": ending,
            "updated_at": snapshot_summary.get("updated_at")
            or self._isoformat(getattr(session_record, "updated_at", None)),
            "expires_at": self._isoformat(getattr(session_record, "expires_at", None)),
        }

    def trigger_ending(self, thread_id: str) -> Dict[str, Any]:
        session = self.session_manager.get_session(thread_id)
        if not session:
            raise StorySessionNotFoundError(thread_id=thread_id)

        character_id = session.character_id
        session_record = self.session_manager.get_session_record(thread_id)
        current_round_no = int(getattr(session_record, "current_round_no", 0) or 0)

        ending_event = session.story_engine.get_ending_event(character_id)
        dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
        session.current_dialogue_round = dialogue_data
        session.story_engine.record_character_dialogue(dialogue_data["character_dialogue"])

        scene_id = ending_event.get("scene")
        response_payload = {
            "event_title": ending_event.get("title", "\u7ed3\u5c40"),
            "story_background": ending_event.get("story_background", ""),
            "scene": scene_id,
            "ending_type": ending_event.get("ending_type"),
            "character_dialogue": dialogue_data["character_dialogue"],
            "player_options": dialogue_data["player_options"],
            "scene_image_url": self.story_asset_service.resolve_scene_image_url(scene_id),
            "composite_image_url": self.story_asset_service.find_latest_composite_image_url(
                character_id=character_id,
                scene_id=scene_id,
            ),
            "current_states": states_to_payload(
                session.db_manager.get_character_states(character_id)
            ),
            "is_game_finished": True,
        }
        response_payload = self.story_asset_service.merge_story_assets(response_payload)

        snapshot_record = self.session_manager.save_story_snapshot(
            session=session,
            round_no=current_round_no,
            response_payload=response_payload,
            status="completed",
        )
        return attach_snapshot_metadata(
            payload=response_payload,
            round_no=current_round_no,
            status="completed",
            snapshot_record=snapshot_record,
            thread_id=thread_id,
        )

    def _build_ending_payload(
        self,
        *,
        ending_type: str | None,
        current_states: Dict[str, Any],
        scene: str | None,
        event_title: str | None,
    ) -> Dict[str, Any]:
        resolved_type, description = self._resolve_ending_outcome(
            ending_type=ending_type,
            current_states=current_states,
        )
        return {
            "type": resolved_type,
            "description": description,
            "scene": scene,
            "event_title": event_title,
            "key_states": self._resolve_key_states(current_states),
        }

    def _resolve_ending_outcome(
        self,
        *,
        ending_type: str | None,
        current_states: Dict[str, Any],
    ) -> tuple[str, str]:
        if ending_type and ending_type in self._ENDING_DESCRIPTIONS:
            return ending_type, self._ENDING_DESCRIPTIONS[ending_type]
        if current_states:
            derived_type, description = self._derive_ending_outcome(current_states)
            if derived_type:
                return derived_type, description
        return "completed", self._ENDING_DESCRIPTIONS["completed"]

    def _derive_ending_outcome(self, current_states: Dict[str, Any]) -> tuple[str, str]:
        favorability = self._to_number(current_states.get("favorability"))
        trust = self._to_number(current_states.get("trust"))
        hostility = self._to_number(current_states.get("hostility"))

        if favorability > 60 and trust > 50:
            ending_type = "good_ending"
        elif favorability < 30 or hostility > 50:
            ending_type = "bad_ending"
        elif trust > 50 and favorability > 40:
            ending_type = "neutral_ending"
        else:
            ending_type = "open_ending"
        return ending_type, self._ENDING_DESCRIPTIONS[ending_type]

    @staticmethod
    def _resolve_key_states(current_states: Dict[str, Any]) -> Dict[str, float | None]:
        return {
            "favorability": StoryEndingService._to_number_or_none(current_states.get("favorability")),
            "trust": StoryEndingService._to_number_or_none(current_states.get("trust")),
            "hostility": StoryEndingService._to_number_or_none(current_states.get("hostility")),
            "dependence": StoryEndingService._to_number_or_none(current_states.get("dependence")),
        }

    @staticmethod
    def _resolve_effective_status(session_record) -> str:
        if session_record is None:
            return "missing"
        if session_record.is_expired():
            return "expired"
        return str(getattr(session_record, "status", "initialized") or "initialized")

    @staticmethod
    def _to_number(value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _to_number_or_none(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _isoformat(value) -> str | None:
        return value.isoformat() if value is not None else None
