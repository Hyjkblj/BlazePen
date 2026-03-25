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
    from api.services.training_media_task_service import TrainingMediaTaskService
    from training.media_task_executor import TrainingMediaTaskExecutor
    from api.services.tts_service import TTSService
    from story.story_service_bundle import StoryServiceBundle
    from story.story_session_query_policy import StorySessionQueryPolicy
    from training.training_query_service import TrainingQueryService


_game_service: Optional[GameService] = None
_character_service: Optional[CharacterService] = None
_image_service: Optional[ImageService] = None
_tts_service: Optional[TTSService] = None
_session_manager: Optional[GameSessionManager] = None
_training_service: Optional[TrainingService] = None
_training_media_task_service: Optional[TrainingMediaTaskService] = None
_training_media_task_executor: Optional[TrainingMediaTaskExecutor] = None
_training_media_task_executor_warmed_up: bool = False
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


def get_game_service() -> GameService:
    global _game_service
    if _game_service is None:
        from api.services.game_service import GameService

        bundle = get_story_service_bundle()
        _game_service = GameService.from_story_service_bundle(bundle)
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


def get_training_media_task_service() -> TrainingMediaTaskService:
    global _training_media_task_service
    if _training_media_task_service is None:
        from api.services.training_media_task_service import TrainingMediaTaskService

        _training_media_task_service = TrainingMediaTaskService(
            training_store=get_training_service().training_store,
            media_task_executor=get_training_media_task_executor(),
        )
    return _training_media_task_service


def get_training_media_task_executor() -> TrainingMediaTaskExecutor:
    global _training_media_task_executor
    if _training_media_task_executor is None:
        from models.text_model_service import TextModelService
        from training.media_task_executor import TrainingMediaTaskExecutor, TrainingMediaTaskProviderDispatcher

        _training_media_task_executor = TrainingMediaTaskExecutor(
            training_store=get_training_service().training_store,
            provider_dispatcher=TrainingMediaTaskProviderDispatcher(
                image_service=get_image_service(),
                tts_service=get_tts_service(),
                text_model_service=TextModelService(provider="auto"),
            ),
        )
    return _training_media_task_executor


def warmup_training_media_task_executor() -> dict[str, int]:
    """Initialize media executor and recover pending backlog once during startup."""

    global _training_media_task_executor_warmed_up

    if _training_media_task_executor_warmed_up:
        return {"recovered": 0, "timed_out": 0}

    executor = get_training_media_task_executor()
    result = executor.recover_pending_tasks()
    _training_media_task_executor_warmed_up = True
    return result


def get_training_query_service() -> TrainingQueryService:
    global _training_query_service
    if _training_query_service is None:
        from training.training_query_service import TrainingQueryService

        _training_query_service = TrainingQueryService.from_runtime(get_training_service())
    return _training_query_service
