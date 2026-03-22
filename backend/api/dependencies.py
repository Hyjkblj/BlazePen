"""FastAPI dependency wiring.

This module keeps backend singleton caches in one place and lazily creates
services so training-only processes do not eagerly import story/media/TTS
dependencies. Story-domain collaborator composition is delegated to
`story.story_service_bundle` so API wiring remains a thin dependency entrypoint.
"""

from __future__ import annotations

from concurrent.futures import Executor, ThreadPoolExecutor
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
    from story.story_service_bundle import StoryServiceBundle
    from story.story_session_query_policy import StorySessionQueryPolicy
    from story.story_session_service import StorySessionService
    from story.story_turn_service import StoryTurnService
    from training.training_query_service import TrainingQueryService


_game_service: Optional[GameService] = None
_character_service: Optional[CharacterService] = None
_image_service: Optional[ImageService] = None
_tts_service: Optional[TTSService] = None
_session_manager: Optional[GameSessionManager] = None
_training_service: Optional[TrainingService] = None
_training_query_service: Optional[TrainingQueryService] = None
_story_image_executor: Optional[Executor] = None
_story_session_query_policy: Optional[StorySessionQueryPolicy] = None
_story_service_bundle: Optional[StoryServiceBundle] = None


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


def get_story_session_query_policy() -> StorySessionQueryPolicy:
    global _story_session_query_policy
    if _story_session_query_policy is None:
        from story.story_session_query_policy import StorySessionQueryPolicy

        _story_session_query_policy = StorySessionQueryPolicy.from_environment()
    return _story_session_query_policy


def get_story_service_bundle() -> StoryServiceBundle:
    global _story_service_bundle
    if _story_service_bundle is None:
        from story.story_service_bundle import build_story_service_bundle

        _story_service_bundle = build_story_service_bundle(
            session_manager=get_session_manager(),
            image_service=get_image_service(),
            character_service=get_character_service(),
            image_executor=get_story_image_executor(),
            story_session_query_policy=get_story_session_query_policy(),
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
            story_asset_service=bundle.story_asset_service,
            story_session_service=bundle.story_session_service,
            story_turn_service=bundle.story_turn_service,
            story_ending_service=bundle.story_ending_service,
            story_history_service=bundle.story_history_service,
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


def get_training_query_service() -> TrainingQueryService:
    global _training_query_service
    if _training_query_service is None:
        from training.training_query_service import TrainingQueryService

        _training_query_service = TrainingQueryService.from_runtime(get_training_service())
    return _training_query_service
