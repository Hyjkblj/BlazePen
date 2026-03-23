"""Shared story-route handlers.

Transitional compatibility:
1. story init lives under `/v1/game/*`
2. legacy `/v1/characters/initialize-story` stays as a thin wrapper
3. the handler keeps one request/response/error contract
"""

from __future__ import annotations

from api.error_codes import (
    INTERNAL_ERROR,
    STORY_SESSION_EXPIRED,
    STORY_SESSION_NOT_FOUND,
    VALIDATION_ERROR,
    infer_story_error_code,
)
from api.response import build_success_payload, error_response, not_found_response
from api.schemas import InitializeStoryRequest
from api.services.game_service import GameService
from story.exceptions import StorySessionExpiredError, StorySessionNotFoundError
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_initialize_story_request(
    request: InitializeStoryRequest,
    game_service: GameService,
    *,
    route_name: str,
):
    """Handle story initialization for canonical and compatibility routes."""

    try:
        if not request.thread_id:
            logger.error("thread_id is required: route=%s", route_name)
            return error_response(
                code=422,
                message="thread_id is required",
                error_code=VALIDATION_ERROR,
                details={"route": route_name},
            )
        if not request.character_id:
            logger.error("character_id is required: route=%s thread_id=%s", route_name, request.thread_id)
            return error_response(
                code=422,
                message="character_id is required",
                error_code=VALIDATION_ERROR,
                details={"route": route_name, "thread_id": request.thread_id},
            )

        try:
            character_id = int(request.character_id)
        except (TypeError, ValueError):
            return error_response(
                code=422,
                message=f"character_id must be an integer: {request.character_id}",
                error_code=VALIDATION_ERROR,
                details={
                    "route": route_name,
                    "thread_id": request.thread_id,
                    "character_id": request.character_id,
                },
            )

        result = game_service.initialize_story(
            request.thread_id,
            character_id,
            request.scene_id or "school",
            request.character_image_url,
            request.opening_event_id,
        )
        payload = game_service.normalize_story_turn_payload(
            result,
            thread_id=request.thread_id,
        )
        return build_success_payload(data=payload)
    except StorySessionExpiredError as exc:
        return error_response(
            code=410,
            message=str(exc),
            error_code=STORY_SESSION_EXPIRED,
            details={"route": route_name, "thread_id": request.thread_id},
        )
    except StorySessionNotFoundError as exc:
        return not_found_response(
            message=str(exc),
            error_code=STORY_SESSION_NOT_FOUND,
            details={"route": route_name, "thread_id": request.thread_id},
        )
    except ValueError as exc:
        message = f"invalid story initialize request: {str(exc)}"
        logger.error(message, exc_info=True)
        return error_response(
            code=400,
            message=message,
            error_code=infer_story_error_code(str(exc), default=VALIDATION_ERROR),
            details={"route": route_name, "thread_id": request.thread_id},
        )
    except Exception as exc:
        logger.error("failed to initialize story: route=%s error=%s", route_name, str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"failed to initialize story: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": route_name, "thread_id": request.thread_id},
        )
