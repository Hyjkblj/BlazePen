"""FastAPI dependency wiring.

This module keeps backend singleton caches in one place and lazily creates
services so training-only processes do not eagerly import story/media/TTS
dependencies. PR-BE-04 also centralizes the story-domain service bundle here,
so routers and the GameService facade always reuse the same story collaborators.
"""

from __future__ import annotations

from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from api.services.character_service import CharacterService
    from api.services.game_service import GameService
    from api.services.game_session import GameSessionManager
    from api.services.image_service import ImageService
    from api.services.training_service import TrainingService
    from api.services.tts_service import TTSService
    from story.story_asset_service import StoryAssetService
    from story.story_ending_service import StoryEndingService
    from story.story_history_service import StoryHistoryService
    from story.story_session_service import StorySessionService
    from story.story_turn_service import StoryTurnService


@dataclass(frozen=True)
class _StoryServiceBundle:
    """One shared story-domain wiring bundle."""

    image_executor: Executor
    story_asset_service: StoryAssetService
    story_session_service: StorySessionService
    story_turn_service: StoryTurnService
    story_ending_service: StoryEndingService
    story_history_service: StoryHistoryService


_game_service: Optional[GameService] = None
_character_service: Optional[CharacterService] = None
_image_service: Optional[ImageService] = None
_tts_service: Optional[TTSService] = None
_session_manager: Optional[GameSessionManager] = None
_training_service: Optional[TrainingService] = None
_story_image_executor: Optional[Executor] = None
_story_service_bundle: Optional[_StoryServiceBundle] = None


def get_image_service() -> ImageService:
    global _image_service
    if _image_service is None:
        from api.services.image_service import ImageService

        _image_service = ImageService()
    return _image_service


def get_character_service() -> CharacterService:
    global _character_service
    if _character_service is None:
        from api.services.character_service import CharacterService

        _character_service = CharacterService(image_service=get_image_service())
    return _character_service


def get_story_image_executor() -> Executor:
    global _story_image_executor
    if _story_image_executor is None:
        _story_image_executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="image_gen",
        )
    return _story_image_executor


def get_story_service_bundle() -> _StoryServiceBundle:
    global _story_service_bundle
    if _story_service_bundle is None:
        from story.story_asset_service import StoryAssetService
        from story.story_ending_service import StoryEndingService
        from story.story_history_service import StoryHistoryService
        from story.story_session_service import StorySessionService
        from story.story_turn_service import StoryTurnService

        session_manager = get_session_manager()
        image_service = get_image_service()
        character_service = get_character_service()
        image_executor = get_story_image_executor()

        story_asset_service = StoryAssetService(image_service=image_service)
        story_session_service = StorySessionService(
            session_manager=session_manager,
            story_asset_service=story_asset_service,
        )
        story_turn_service = StoryTurnService(
            session_manager=session_manager,
            character_service=character_service,
            story_session_service=story_session_service,
            story_asset_service=story_asset_service,
            image_executor=image_executor,
        )
        story_ending_service = StoryEndingService(
            session_manager=session_manager,
            story_asset_service=story_asset_service,
        )
        story_history_service = StoryHistoryService(
            session_manager=session_manager,
        )
        _story_service_bundle = _StoryServiceBundle(
            image_executor=image_executor,
            story_asset_service=story_asset_service,
            story_session_service=story_session_service,
            story_turn_service=story_turn_service,
            story_ending_service=story_ending_service,
            story_history_service=story_history_service,
        )
    return _story_service_bundle


def get_story_asset_service() -> StoryAssetService:
    return get_story_service_bundle().story_asset_service


def get_story_session_service() -> StorySessionService:
    return get_story_service_bundle().story_session_service


def get_story_turn_service() -> StoryTurnService:
    return get_story_service_bundle().story_turn_service


def get_story_ending_service() -> StoryEndingService:
    return get_story_service_bundle().story_ending_service


def get_story_history_service() -> StoryHistoryService:
    return get_story_service_bundle().story_history_service


def get_game_service() -> GameService:
    global _game_service
    if _game_service is None:
        from api.services.game_service import GameService

        bundle = get_story_service_bundle()
        _game_service = GameService(
            character_service=get_character_service(),
            image_service=get_image_service(),
            session_manager=get_session_manager(),
            story_asset_service=bundle.story_asset_service,
            story_session_service=bundle.story_session_service,
            story_turn_service=bundle.story_turn_service,
            story_ending_service=bundle.story_ending_service,
            story_history_service=bundle.story_history_service,
            image_executor=bundle.image_executor,
        )
    return _game_service


def get_tts_service() -> TTSService:
    global _tts_service
    if _tts_service is None:
        from api.services.tts_service import TTSService

        _tts_service = TTSService()
    return _tts_service


def get_session_manager() -> GameSessionManager:
    global _session_manager
    if _session_manager is None:
        from api.services.game_session import GameSessionManager

        _session_manager = GameSessionManager()
    return _session_manager


def get_training_service() -> TrainingService:
    global _training_service
    if _training_service is None:
        from api.services.training_service import TrainingService

        _training_service = TrainingService()
    return _training_service
