"""Training media task API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_training_media_task_service
from api.error_codes import (
    INTERNAL_ERROR,
    TRAINING_STORAGE_UNAVAILABLE,
    TRAINING_MEDIA_TASK_CONFLICT,
    TRAINING_MEDIA_TASK_INVALID,
    TRAINING_MEDIA_TASK_NOT_FOUND,
    TRAINING_MEDIA_TASK_UNSUPPORTED,
    TRAINING_SESSION_NOT_FOUND,
)
from api.response import build_success_payload, error_response, not_found_response
from api.schemas import (
    TrainingMediaTaskApiResponse,
    TrainingMediaTaskCreateRequest,
    TrainingMediaTaskListApiResponse,
)
from api.services.training_media_task_service import TrainingMediaTaskService
from training.exceptions import (
    TrainingMediaTaskConflictError,
    TrainingMediaTaskInvalidError,
    TrainingMediaTaskNotFoundError,
    TrainingMediaTaskUnsupportedError,
    TrainingStorageUnavailableError,
    TrainingSessionNotFoundError,
)
from utils.logger import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix="/v1/training/media", tags=["training-media"])


def _build_training_media_error_response(
    exc: Exception,
    *,
    route_name: str,
    session_id: str | None = None,
    task_id: str | None = None,
    round_no: int | None = None,
):
    details: dict[str, object] = {"route": route_name}
    if session_id is not None:
        details["session_id"] = session_id
    if task_id is not None:
        details["task_id"] = task_id
    if round_no is not None:
        details["round_no"] = round_no

    if isinstance(exc, TrainingSessionNotFoundError):
        return not_found_response(
            message=str(exc),
            error_code=TRAINING_SESSION_NOT_FOUND,
            details=details,
        )

    if isinstance(exc, TrainingMediaTaskNotFoundError):
        return not_found_response(
            message=str(exc),
            error_code=TRAINING_MEDIA_TASK_NOT_FOUND,
            details=details,
        )

    if isinstance(exc, TrainingMediaTaskUnsupportedError):
        details["task_type"] = exc.task_type
        details["supported_task_types"] = list(exc.supported_task_types)
        return error_response(
            code=400,
            message=str(exc),
            error_code=TRAINING_MEDIA_TASK_UNSUPPORTED,
            details=details,
        )

    if isinstance(exc, TrainingMediaTaskInvalidError):
        if exc.details:
            details.update(dict(exc.details))
        return error_response(
            code=400,
            message=str(exc),
            error_code=TRAINING_MEDIA_TASK_INVALID,
            details=details,
        )

    if isinstance(exc, TrainingMediaTaskConflictError):
        if exc.details:
            details.update(dict(exc.details))
        return error_response(
            code=409,
            message=str(exc),
            error_code=TRAINING_MEDIA_TASK_CONFLICT,
            details=details,
        )

    if isinstance(exc, TrainingStorageUnavailableError):
        if exc.details:
            details.update(dict(exc.details))
        return error_response(
            code=503,
            message=str(exc),
            error_code=TRAINING_STORAGE_UNAVAILABLE,
            details=details,
        )

    raise TypeError(f"unsupported training media domain exception: {type(exc)!r}")


@router.post("/tasks", response_model=TrainingMediaTaskApiResponse)
async def create_media_task(
    request: TrainingMediaTaskCreateRequest,
    media_task_service: TrainingMediaTaskService = Depends(get_training_media_task_service),
):
    """Create an idempotent training media task."""

    try:
        result = media_task_service.create_task(
            session_id=request.session_id,
            round_no=request.round_no,
            task_type=request.task_type,
            payload=request.payload,
            idempotency_key=request.idempotency_key,
            max_retries=request.max_retries,
        )
        return build_success_payload(data=result)
    except (
        TrainingSessionNotFoundError,
        TrainingMediaTaskNotFoundError,
        TrainingMediaTaskInvalidError,
        TrainingMediaTaskConflictError,
        TrainingMediaTaskUnsupportedError,
        TrainingStorageUnavailableError,
    ) as exc:
        return _build_training_media_error_response(
            exc,
            route_name="training.media.create_task",
            session_id=request.session_id,
            round_no=request.round_no,
        )
    except Exception as exc:
        logger.error("failed to create training media task: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to create training media task",
            error_code=INTERNAL_ERROR,
            details={
                "route": "training.media.create_task",
                "session_id": request.session_id,
                "round_no": request.round_no,
            },
        )


@router.get("/tasks/{task_id}", response_model=TrainingMediaTaskApiResponse)
async def get_media_task(
    task_id: str,
    media_task_service: TrainingMediaTaskService = Depends(get_training_media_task_service),
):
    """Get a training media task by task_id."""

    try:
        result = media_task_service.get_task(task_id)
        return build_success_payload(data=result)
    except (
        TrainingSessionNotFoundError,
        TrainingMediaTaskNotFoundError,
        TrainingMediaTaskInvalidError,
        TrainingMediaTaskConflictError,
        TrainingMediaTaskUnsupportedError,
        TrainingStorageUnavailableError,
    ) as exc:
        return _build_training_media_error_response(
            exc,
            route_name="training.media.get_task",
            task_id=task_id,
        )
    except Exception as exc:
        logger.error("failed to get training media task: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to get training media task",
            error_code=INTERNAL_ERROR,
            details={
                "route": "training.media.get_task",
                "task_id": task_id,
            },
        )


@router.get("/sessions/{session_id}/tasks", response_model=TrainingMediaTaskListApiResponse)
async def list_media_tasks(
    session_id: str,
    round_no: int | None = Query(default=None, ge=0),
    media_task_service: TrainingMediaTaskService = Depends(get_training_media_task_service),
):
    """List training media tasks by session, optionally filtered by round."""

    try:
        result = media_task_service.list_tasks(session_id=session_id, round_no=round_no)
        return build_success_payload(data=result)
    except (
        TrainingSessionNotFoundError,
        TrainingMediaTaskNotFoundError,
        TrainingMediaTaskInvalidError,
        TrainingMediaTaskConflictError,
        TrainingMediaTaskUnsupportedError,
        TrainingStorageUnavailableError,
    ) as exc:
        return _build_training_media_error_response(
            exc,
            route_name="training.media.list_tasks",
            session_id=session_id,
            round_no=round_no,
        )
    except Exception as exc:
        logger.error("failed to list training media tasks: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to list training media tasks",
            error_code=INTERNAL_ERROR,
            details={
                "route": "training.media.list_tasks",
                "session_id": session_id,
                "round_no": round_no,
            },
        )
