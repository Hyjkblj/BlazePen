"""Story API facade service.

PR-BE-04 transitional role:
1. keep router-facing methods stable
2. delegate story domain work to focused story services
3. avoid embedding story runtime composition inside this compatibility facade
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from api.story_contract_utils import normalize_story_turn_payload
from story.story_asset_service import StoryAssetService
from story.story_ending_service import StoryEndingService
from story.story_history_service import StoryHistoryService
from story.story_session_service import StorySessionService
from story.story_turn_service import StoryTurnService

if TYPE_CHECKING:
    from story.story_service_bundle import StoryServiceBundle


class GameService:
    """Thin facade kept for router compatibility during the story-domain split."""

    _COMPATIBILITY_FACADE_METHODS = frozenset(
        {
            "from_story_service_bundle",
            "compatibility_facade_methods",
            "compatibility_exit_conditions",
            "init_game",
            "initialize_story",
            "submit_story_turn",
            "check_ending",
            "get_story_session_snapshot",
            "list_story_sessions",
            "get_story_history",
            "get_story_ending_summary",
            "trigger_ending",
            "normalize_story_turn_payload",
        }
    )
    _REMOVE_AFTER_STORY_ROUTER_CUTOVER = frozenset(
        {
            "init_game",
            "initialize_story",
            "submit_story_turn",
            "check_ending",
            "get_story_session_snapshot",
            "list_story_sessions",
            "get_story_history",
            "get_story_ending_summary",
            "trigger_ending",
            "normalize_story_turn_payload",
        }
    )

    def __init__(
        self,
        *,
        story_asset_service: StoryAssetService | None,
        story_session_service: StorySessionService | None,
        story_turn_service: StoryTurnService | None,
        story_ending_service: StoryEndingService | None,
        story_history_service: StoryHistoryService | None,
    ):
        self._story_asset_service = self._require_collaborator(
            collaborator=story_asset_service,
            collaborator_name="story_asset_service",
        )
        self._story_session_service = self._require_collaborator(
            collaborator=story_session_service,
            collaborator_name="story_session_service",
        )
        self._story_turn_service = self._require_collaborator(
            collaborator=story_turn_service,
            collaborator_name="story_turn_service",
        )
        self._story_ending_service = self._require_collaborator(
            collaborator=story_ending_service,
            collaborator_name="story_ending_service",
        )
        self._story_history_service = self._require_collaborator(
            collaborator=story_history_service,
            collaborator_name="story_history_service",
        )

    @classmethod
    def from_story_service_bundle(cls, bundle: StoryServiceBundle) -> GameService:
        """Build facade from one assembled story bundle."""

        return cls(
            story_asset_service=bundle.story_asset_service,
            story_session_service=bundle.story_session_service,
            story_turn_service=bundle.story_turn_service,
            story_ending_service=bundle.story_ending_service,
            story_history_service=bundle.story_history_service,
        )

    @classmethod
    def compatibility_facade_methods(cls) -> set[str]:
        """Return the allowed compatibility facade surface during PR-BE-SPLIT-04."""

        return set(cls._COMPATIBILITY_FACADE_METHODS)

    @classmethod
    def compatibility_exit_conditions(cls) -> dict[str, object]:
        """Return GameService removal contract for PR-BE-SPLIT-04 closeout.

        Exit trigger:
        - story routers no longer call GameService facade methods
        - story routers call story domain services directly via dependency wiring
        """

        return {
            "migration_trigger": "story_routers_direct_story_domain_services",
            "retain_during_split": set(cls._COMPATIBILITY_FACADE_METHODS),
            "remove_after_router_cutover": set(cls._REMOVE_AFTER_STORY_ROUTER_CUTOVER),
        }

    def init_game(
        self,
        user_id: str | None,
        character_id: int | None,
        game_mode: str,
    ) -> Dict[str, str]:
        return self._story_session_service.init_game(
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
        return self._story_turn_service.initialize_story(
            thread_id=thread_id,
            character_id=character_id,
            scene_id=scene_id,
            character_image_url=character_image_url,
            opening_event_id=opening_event_id,
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
        return self._story_turn_service.submit_turn(
            thread_id=thread_id,
            user_input=user_input,
            option_id=option_id,
            user_id=user_id,
            character_id=character_id,
        )

    def check_ending(self, thread_id: str) -> Dict[str, Any]:
        return self._story_ending_service.check_ending(thread_id)

    def get_story_session_snapshot(self, thread_id: str) -> Dict[str, Any]:
        return self._story_session_service.get_session_snapshot(thread_id)

    def list_story_sessions(
        self,
        *,
        user_id: str,
        limit: int = 10,
        actor_user_id: str | None = None,
    ) -> Dict[str, Any]:
        return self._story_session_service.list_recent_sessions(
            user_id=user_id,
            limit=limit,
            actor_user_id=actor_user_id,
        )

    def get_story_history(self, thread_id: str) -> Dict[str, Any]:
        return self._story_history_service.get_story_history(thread_id)

    def get_story_ending_summary(self, thread_id: str) -> Dict[str, Any]:
        return self._story_ending_service.get_ending_summary(thread_id)

    def trigger_ending(self, thread_id: str) -> Dict[str, Any]:
        return self._story_ending_service.trigger_ending(thread_id)

    def normalize_story_turn_payload(
        self,
        result: Dict[str, Any],
        *,
        thread_id: str,
    ) -> Dict[str, Any]:
        """Normalize story turn payload using the story-domain asset orchestrator."""

        return normalize_story_turn_payload(
            result,
            thread_id=thread_id,
            story_asset_service=self._story_asset_service,
        )

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
