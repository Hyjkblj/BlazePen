"""Story API facade service.

PR-BE-04 transitional role:
1. keep router-facing methods stable
2. delegate story domain work to focused story services
3. reuse one shared set of story collaborators
"""

from __future__ import annotations

from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Any, Dict, Optional

from api.services.character_service import CharacterService
from api.services.game_session import GameSessionManager
from api.services.image_service import ImageService
from story.story_asset_service import StoryAssetService
from story.story_ending_service import StoryEndingService
from story.story_history_service import StoryHistoryService
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
        story_history_service: Optional[StoryHistoryService] = None,
        image_executor: Optional[Executor] = None,
    ):
        self.session_manager = self._pick_first(
            session_manager,
            getattr(story_session_service, "session_manager", None),
            getattr(story_turn_service, "session_manager", None),
            getattr(story_ending_service, "session_manager", None),
            getattr(story_history_service, "session_manager", None),
        ) or GameSessionManager()

        self.image_service = self._pick_first(
            image_service,
            getattr(story_asset_service, "image_service", None),
        ) or ImageService()

        self.character_service = self._pick_first(
            character_service,
            getattr(story_turn_service, "character_service", None),
        ) or CharacterService(image_service=self.image_service)

        self.story_asset_service = self._pick_first(
            story_asset_service,
            getattr(story_session_service, "story_asset_service", None),
            getattr(story_turn_service, "story_asset_service", None),
            getattr(story_ending_service, "story_asset_service", None),
        ) or StoryAssetService(image_service=self.image_service)

        self.story_session_service = self._pick_first(
            story_session_service,
            getattr(story_turn_service, "story_session_service", None),
        ) or StorySessionService(
            session_manager=self.session_manager,
            story_asset_service=self.story_asset_service,
        )

        self.image_executor = self._pick_first(
            image_executor,
            getattr(story_turn_service, "image_executor", None),
        )
        if self.image_executor is None and story_turn_service is None:
            self.image_executor = ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="image_gen",
            )

        self.story_turn_service = story_turn_service or StoryTurnService(
            session_manager=self.session_manager,
            character_service=self.character_service,
            story_session_service=self.story_session_service,
            story_asset_service=self.story_asset_service,
            image_executor=self.image_executor,
        )

        if self.image_executor is None:
            self.image_executor = getattr(self.story_turn_service, "image_executor", None)

        self.story_ending_service = story_ending_service or StoryEndingService(
            session_manager=self.session_manager,
            story_asset_service=self.story_asset_service,
        )

        self.story_history_service = story_history_service or StoryHistoryService(
            session_manager=self.session_manager,
        )

        self._validate_story_dependencies()

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
    def _pick_first(*values):
        for value in values:
            if value is not None:
                return value
        return None

    def _validate_story_dependencies(self):
        self._ensure_shared_dependency(
            service_name="story_asset_service",
            service=self.story_asset_service,
            dependency_name="image_service",
            expected=self.image_service,
        )
        self._ensure_shared_dependency(
            service_name="story_session_service",
            service=self.story_session_service,
            dependency_name="session_manager",
            expected=self.session_manager,
        )
        self._ensure_shared_dependency(
            service_name="story_session_service",
            service=self.story_session_service,
            dependency_name="story_asset_service",
            expected=self.story_asset_service,
        )
        self._ensure_shared_dependency(
            service_name="story_turn_service",
            service=self.story_turn_service,
            dependency_name="session_manager",
            expected=self.session_manager,
        )
        self._ensure_shared_dependency(
            service_name="story_turn_service",
            service=self.story_turn_service,
            dependency_name="character_service",
            expected=self.character_service,
        )
        self._ensure_shared_dependency(
            service_name="story_turn_service",
            service=self.story_turn_service,
            dependency_name="story_session_service",
            expected=self.story_session_service,
        )
        self._ensure_shared_dependency(
            service_name="story_turn_service",
            service=self.story_turn_service,
            dependency_name="story_asset_service",
            expected=self.story_asset_service,
        )
        self._ensure_shared_dependency(
            service_name="story_turn_service",
            service=self.story_turn_service,
            dependency_name="image_executor",
            expected=self.image_executor,
        )
        self._ensure_shared_dependency(
            service_name="story_ending_service",
            service=self.story_ending_service,
            dependency_name="session_manager",
            expected=self.session_manager,
        )
        self._ensure_shared_dependency(
            service_name="story_ending_service",
            service=self.story_ending_service,
            dependency_name="story_asset_service",
            expected=self.story_asset_service,
        )
        self._ensure_shared_dependency(
            service_name="story_history_service",
            service=self.story_history_service,
            dependency_name="session_manager",
            expected=self.session_manager,
        )

    @staticmethod
    def _ensure_shared_dependency(
        *,
        service_name: str,
        service: object,
        dependency_name: str,
        expected: object,
    ):
        actual = getattr(service, dependency_name, None)
        if actual is not None and expected is not None and actual is not expected:
            raise ValueError(
                f"{service_name}.{dependency_name} must reuse the shared {dependency_name} instance"
            )
