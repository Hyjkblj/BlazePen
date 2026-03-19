"""Story API facade service.

PR-BE-04 transitional role:
1. keep router-facing methods stable
2. delegate story domain responsibilities into focused story services
3. preserve one shared session manager and asset contract across delegates
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from api.services.character_service import CharacterService
from api.services.game_session import GameSessionManager
from api.services.image_service import ImageService
from story.story_asset_service import StoryAssetService
from story.story_ending_service import StoryEndingService
from story.story_session_service import StorySessionService
from story.story_turn_service import StoryTurnService


class GameService:
    """Thin facade kept for router compatibility during the story-domain split."""

    def __init__(
        self,
        character_service: Optional[CharacterService] = None,
        image_service: Optional[ImageService] = None,
        session_manager: Optional[GameSessionManager] = None,
        story_asset_service: Optional[StoryAssetService] = None,
        story_session_service: Optional[StorySessionService] = None,
        story_turn_service: Optional[StoryTurnService] = None,
        story_ending_service: Optional[StoryEndingService] = None,
    ):
        self.session_manager = session_manager or GameSessionManager()
        self.image_service = image_service or ImageService()
        self.character_service = character_service or CharacterService(
            image_service=self.image_service
        )
        self.story_asset_service = story_asset_service or StoryAssetService(
            image_service=self.image_service
        )
        self.image_executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="image_gen",
        )
        self.story_session_service = story_session_service or StorySessionService(
            session_manager=self.session_manager,
            story_asset_service=self.story_asset_service,
        )
        self.story_turn_service = story_turn_service or StoryTurnService(
            session_manager=self.session_manager,
            character_service=self.character_service,
            story_session_service=self.story_session_service,
            story_asset_service=self.story_asset_service,
            image_executor=self.image_executor,
        )
        self.story_ending_service = story_ending_service or StoryEndingService(
            session_manager=self.session_manager,
            story_asset_service=self.story_asset_service,
        )

    def init_game(
        self,
        user_id: Optional[str],
        character_id: Optional[int],
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
        character_image_url: Optional[str] = None,
        opening_event_id: Optional[str] = None,
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
        option_id: Optional[int] = None,
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
        option_id: Optional[int],
        user_id: Optional[str],
        character_id: Optional[str],
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

    def trigger_ending(self, thread_id: str) -> Dict[str, Any]:
        return self.story_ending_service.trigger_ending(thread_id)
