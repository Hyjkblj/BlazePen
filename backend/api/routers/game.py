"""Story gameplay API routes."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends

from api.dependencies import get_game_service
from api.error_codes import (
    INTERNAL_ERROR,
    STORY_SESSION_EXPIRED,
    STORY_SESSION_NOT_FOUND,
    STORY_SESSION_RESTORE_FAILED,
    VALIDATION_ERROR,
    infer_story_error_code,
)
from api.response import build_success_payload, error_response, not_found_response
from api.schemas import GameInitRequest, GameInputRequest, InitializeStoryRequest, TriggerEndingRequest
from api.services.game_service import GameService
from api.story_contract_utils import normalize_story_session_init_payload, normalize_story_turn_payload
from api.story_route_handlers import handle_initialize_story_request
from api.story_schemas import (
    StoryEndingCheckApiResponse,
    StorySessionInitApiResponse,
    StorySessionSnapshotApiResponse,
    StoryTurnApiResponse,
)
from story.exceptions import (
    StorySessionExpiredError,
    StorySessionNotFoundError,
    StorySessionRestoreFailedError,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/game", tags=["story"])


@router.post("/init", response_model=StorySessionInitApiResponse)
async def init_game(
    request: GameInitRequest,
    game_service: GameService = Depends(get_game_service),
):
    """Initialize a story session."""

    try:
        logger.info(
            "story init requested: user_id=%s character_id=%s game_mode=%s",
            request.user_id,
            request.character_id,
            request.game_mode,
        )
        if not request.character_id:
            logger.error("character_id is required")
            return error_response(
                code=400,
                message="character_id is required",
                error_code=VALIDATION_ERROR,
                details={"route": "story.init"},
            )

        result = game_service.init_game(
            user_id=request.user_id,
            character_id=int(request.character_id),
            game_mode=request.game_mode,
        )
        payload = normalize_story_session_init_payload(result)
        logger.info(
            "story init succeeded: thread_id=%s user_id=%s",
            payload.get("thread_id"),
            payload.get("user_id"),
        )
        return build_success_payload(data=payload)
    except ValueError as exc:
        message = f"参数错误: {str(exc)}"
        logger.error(message)
        return error_response(
            code=400,
            message=message,
            error_code=infer_story_error_code(str(exc), default=VALIDATION_ERROR),
            details={"route": "story.init"},
        )
    except Exception as exc:
        logger.error("failed to initialize story session: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"初始化游戏失败: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "story.init"},
        )


@router.post("/input", response_model=StoryTurnApiResponse)
async def process_input(
    request: GameInputRequest,
    game_service: GameService = Depends(get_game_service),
):
    """Process player input for the current story session."""

    option_id = None
    user_input = (request.user_input or "").strip()

    option_match = re.fullmatch(r"option:(\d+)", user_input, flags=re.IGNORECASE)
    if option_match:
        option_id = int(option_match.group(1)) - 1
        user_input = ""
    elif user_input.lower().startswith("option:"):
        return error_response(
            code=400,
            message="无效的选项格式，应为 option:<number>",
            error_code=VALIDATION_ERROR,
            details={"route": "story.submit_round", "thread_id": request.thread_id},
        )

    try:
        result = game_service.submit_story_turn(
            thread_id=request.thread_id,
            user_input=user_input,
            option_id=option_id,
            user_id=request.user_id,
            character_id=request.character_id,
        )
        payload = normalize_story_turn_payload(result, thread_id=request.thread_id)
        if payload.get("need_reselect_option"):
            return build_success_payload(
                data=payload,
                message="会话已恢复，请重新选择选项",
            )
        return build_success_payload(data=payload)
    except StorySessionRestoreFailedError as exc:
        return error_response(
            code=400,
            message=str(exc),
            error_code=STORY_SESSION_RESTORE_FAILED,
            details={
                "route": "story.submit_round",
                "thread_id": request.thread_id,
                "character_id": request.character_id,
            },
        )
    except StorySessionNotFoundError as exc:
        return not_found_response(
            message=str(exc),
            error_code=STORY_SESSION_NOT_FOUND,
            details={"route": "story.submit_round", "thread_id": request.thread_id},
        )
    except StorySessionExpiredError as exc:
        return error_response(
            code=410,
            message=str(exc),
            error_code=STORY_SESSION_EXPIRED,
            details={"route": "story.submit_round", "thread_id": request.thread_id},
        )
    except ValueError as exc:
        message = f"参数错误: {str(exc)}"
        logger.error(message, exc_info=True)
        return error_response(
            code=400,
            message=message,
            error_code=infer_story_error_code(str(exc), default=VALIDATION_ERROR),
            details={"route": "story.submit_round", "thread_id": request.thread_id},
        )
    except Exception as exc:
        logger.error("failed to process story input: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"处理输入失败: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "story.submit_round", "thread_id": request.thread_id},
        )


@router.post("/initialize-story", response_model=StoryTurnApiResponse)
async def initialize_story(
    request: InitializeStoryRequest,
    game_service: GameService = Depends(get_game_service),
):
    """Canonical story-domain route for story initialization."""

    return await handle_initialize_story_request(
        request=request,
        game_service=game_service,
        route_name="story.initialize",
    )


@router.get("/sessions/{thread_id}", response_model=StorySessionSnapshotApiResponse)
async def get_session_snapshot(
    thread_id: str,
    game_service: GameService = Depends(get_game_service),
):
    """Return the latest restorable story snapshot."""

    try:
        result = game_service.get_story_session_snapshot(thread_id)
        payload = normalize_story_turn_payload(result, thread_id=thread_id)
        payload["updated_at"] = result.get("updated_at")
        payload["expires_at"] = result.get("expires_at")
        return build_success_payload(data=payload)
    except StorySessionNotFoundError as exc:
        return not_found_response(
            message=str(exc),
            error_code=STORY_SESSION_NOT_FOUND,
            details={"route": "story.snapshot", "thread_id": thread_id},
        )
    except StorySessionExpiredError as exc:
        return error_response(
            code=410,
            message=str(exc),
            error_code=STORY_SESSION_EXPIRED,
            details={"route": "story.snapshot", "thread_id": thread_id},
        )
    except Exception as exc:
        logger.error("failed to get story snapshot: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"获取故事快照失败: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "story.snapshot", "thread_id": thread_id},
        )


@router.get("/check-ending/{thread_id}", response_model=StoryEndingCheckApiResponse)
async def check_ending(
    thread_id: str,
    game_service: GameService = Depends(get_game_service),
):
    """Check whether the story session has reached an ending."""

    try:
        result = game_service.check_ending(thread_id)
        return build_success_payload(data=result)
    except StorySessionExpiredError as exc:
        return error_response(
            code=410,
            message=str(exc),
            error_code=STORY_SESSION_EXPIRED,
            details={"route": "story.check_ending", "thread_id": thread_id},
        )
    except StorySessionNotFoundError as exc:
        return not_found_response(
            message=str(exc),
            error_code=STORY_SESSION_NOT_FOUND,
            details={"route": "story.check_ending", "thread_id": thread_id},
        )
    except ValueError as exc:
        message = str(exc)
        return not_found_response(
            message=message,
            error_code=infer_story_error_code(message),
            details={"route": "story.check_ending", "thread_id": thread_id},
        )
    except Exception as exc:
        logger.error("failed to check story ending: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"检查结局失败: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "story.check_ending", "thread_id": thread_id},
        )


@router.post("/trigger-ending", response_model=StoryTurnApiResponse)
async def trigger_ending(
    request: TriggerEndingRequest,
    game_service: GameService = Depends(get_game_service),
):
    """Trigger the ending flow for a story session."""

    try:
        result = game_service.trigger_ending(request.thread_id)
        payload = normalize_story_turn_payload(result, thread_id=request.thread_id)
        payload["status"] = "completed"
        return build_success_payload(data=payload)
    except StorySessionExpiredError as exc:
        return error_response(
            code=410,
            message=str(exc),
            error_code=STORY_SESSION_EXPIRED,
            details={"route": "story.trigger_ending", "thread_id": request.thread_id},
        )
    except StorySessionNotFoundError as exc:
        return not_found_response(
            message=str(exc),
            error_code=STORY_SESSION_NOT_FOUND,
            details={"route": "story.trigger_ending", "thread_id": request.thread_id},
        )
    except ValueError as exc:
        message = str(exc)
        return not_found_response(
            message=message,
            error_code=infer_story_error_code(message),
            details={"route": "story.trigger_ending", "thread_id": request.thread_id},
        )
    except Exception as exc:
        logger.error("failed to trigger story ending: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"触发结局失败: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "story.trigger_ending", "thread_id": request.thread_id},
        )
