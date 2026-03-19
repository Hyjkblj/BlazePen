"""Story-ending domain service."""

from __future__ import annotations

from typing import Any, Dict

from story.exceptions import StorySessionNotFoundError
from story.story_asset_service import StoryAssetService
from story.story_response_utils import attach_snapshot_metadata, states_to_payload


class StoryEndingService:
    """Own story ending detection and completion payloads."""

    def __init__(self, *, session_manager, story_asset_service: StoryAssetService | None = None):
        self.session_manager = session_manager
        self.story_asset_service = story_asset_service or StoryAssetService()

    def check_ending(self, thread_id: str) -> Dict[str, Any]:
        session = self.session_manager.get_session(thread_id)
        if not session:
            raise StorySessionNotFoundError(thread_id=thread_id)

        if not session.story_engine.is_game_finished():
            return {
                "has_ending": False,
                "ending": None,
            }

        states = session.db_manager.get_character_states(session.character_id)
        if states is None:
            return {
                "has_ending": False,
                "ending": None,
            }

        favorability = states.favorability
        trust = states.trust
        hostility = states.hostility

        if favorability > 60 and trust > 50:
            ending_type = "good_ending"
            ending_desc = "经过一系列事件，你们的关系变得更加亲密。"
        elif favorability < 30 or hostility > 50:
            ending_type = "bad_ending"
            ending_desc = "关系走向了不好的方向，彼此距离越来越远。"
        elif trust > 50 and favorability > 40:
            ending_type = "neutral_ending"
            ending_desc = "关系保持稳定，未来仍有更多可能。"
        else:
            ending_type = "open_ending"
            ending_desc = "故事仍在延展，最终结局尚未完全确定。"

        return {
            "has_ending": True,
            "ending": {
                "type": ending_type,
                "description": ending_desc,
                "favorability": favorability,
                "trust": trust,
                "hostility": hostility,
            },
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
            "event_title": ending_event.get("title", "结局"),
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
