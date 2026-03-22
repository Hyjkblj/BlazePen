"""Story API facade service.

PR-BE-04 transitional role:
1. keep router-facing methods stable
2. delegate story domain work to focused story services
3. avoid embedding story runtime composition inside this compatibility facade
"""

from __future__ import annotations

from typing import Any, Dict

from story.story_asset_service import StoryAssetService
from story.story_ending_service import StoryEndingService
from story.story_history_service import StoryHistoryService
from story.story_session_service import StorySessionService
from story.story_turn_service import StoryTurnService


class GameService:
    """Thin facade kept for router compatibility during the story-domain split."""

    def __init__(
        self,
        *,
        story_asset_service: StoryAssetService | None,
        story_session_service: StorySessionService | None,
        story_turn_service: StoryTurnService | None,
        story_ending_service: StoryEndingService | None,
        story_history_service: StoryHistoryService | None,
        # Transitional compatibility: keep legacy constructor args explicit so
        # old callsites fail less abruptly while composition lives in
        # `api.dependencies.get_story_service_bundle`.
        character_service: object | None = None,
        image_service: object | None = None,
        session_manager: object | None = None,
        image_executor: object | None = None,
    ):
        self.story_asset_service = self._require_collaborator(
            collaborator=story_asset_service,
            collaborator_name="story_asset_service",
        )
        self.story_session_service = self._require_collaborator(
            collaborator=story_session_service,
            collaborator_name="story_session_service",
        )
        self.story_turn_service = self._require_collaborator(
            collaborator=story_turn_service,
            collaborator_name="story_turn_service",
        )
        self.story_ending_service = self._require_collaborator(
            collaborator=story_ending_service,
            collaborator_name="story_ending_service",
        )
        self.story_history_service = self._require_collaborator(
            collaborator=story_history_service,
            collaborator_name="story_history_service",
        )

        self._legacy_character_service = character_service
        self._legacy_image_service = image_service
        self._legacy_session_manager = session_manager
        self._legacy_image_executor = image_executor

    def init_game(
        self,
        user_id: str | None,
        character_id: int | None,
        game_mode: str,
    ) -> Dict[str, str]:
        return self.story_session_service.init_game(
            user_id=user_id,
            character_id=character_id,
            game_mode=game_mode,
        )

    def initialize_story(
        self,
        thread_id: str,
        character_id: int,
        scene_id: str = "school",
        character_image_url: str | None = None,
        opening_event_id: str | None = None,
    ) -> Dict[str, Any]:
        return self.story_turn_service.initialize_story(
            thread_id=thread_id,
            character_id=character_id,
            scene_id=scene_id,
            character_image_url=character_image_url,
            opening_event_id=opening_event_id,
        )

    def process_input(
        self,
        thread_id: str,
        user_input: str,
        option_id: int | None = None,
    ) -> Dict[str, Any]:
        return self.story_turn_service.process_input(
            thread_id=thread_id,
            user_input=user_input,
            option_id=option_id,
        )

    def submit_story_turn(
        self,
        *,
        thread_id: str,
        user_input: str,
        option_id: int | None,
        user_id: str | None,
        character_id: str | None,
    ) -> Dict[str, Any]:
        return self.story_turn_service.submit_turn(
            thread_id=thread_id,
            user_input=user_input,
            option_id=option_id,
            user_id=user_id,
            character_id=character_id,
        )

    def check_ending(self, thread_id: str) -> Dict[str, Any]:
        return self.story_ending_service.check_ending(thread_id)

    def get_session_snapshot(self, thread_id: str) -> Dict[str, Any]:
        return self.story_session_service.get_session_snapshot(thread_id)

    def get_story_session_snapshot(self, thread_id: str) -> Dict[str, Any]:
        return self.story_session_service.get_session_snapshot(thread_id)

    def list_story_sessions(
        self,
        *,
        user_id: str,
        limit: int = 10,
        actor_user_id: str | None = None,
    ) -> Dict[str, Any]:
        return self.story_session_service.list_recent_sessions(
            user_id=user_id,
            limit=limit,
            actor_user_id=actor_user_id,
        )

    def get_story_history(self, thread_id: str) -> Dict[str, Any]:
        return self.story_history_service.get_story_history(thread_id)

    def get_story_ending_summary(self, thread_id: str) -> Dict[str, Any]:
        return self.story_ending_service.get_ending_summary(thread_id)

    def trigger_ending(self, thread_id: str) -> Dict[str, Any]:
        return self.story_ending_service.trigger_ending(thread_id)

    @staticmethod
    def _require_collaborator(
        *,
        collaborator: object | None,
        collaborator_name: str,
    ) -> object:
        if collaborator is None:
            raise ValueError(
                "GameService compatibility facade requires explicit "
                f"{collaborator_name} injection"
            )
        return collaborator
