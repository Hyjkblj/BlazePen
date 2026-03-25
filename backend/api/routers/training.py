"""Training API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import get_training_media_task_executor, get_training_query_service, get_training_service
from api.error_codes import (
    INTERNAL_ERROR,
    TRAINING_MODE_UNSUPPORTED,
    TRAINING_MEDIA_TASK_INVALID,
    TRAINING_MEDIA_TASK_UNSUPPORTED,
    TRAINING_ROUND_DUPLICATE,
    TRAINING_SCENARIO_MISMATCH,
    TRAINING_SESSION_COMPLETED,
    TRAINING_SESSION_NOT_FOUND,
    TRAINING_SESSION_RECOVERY_STATE_CORRUPTED,
)
from api.response import build_success_payload, error_response, not_found_response
from api.schemas import (
    TrainingDiagnosticsApiResponse,
    TrainingHistoryApiResponse,
    TrainingInitApiResponse,
    TrainingInitRequest,
    TrainingProgressApiResponse,
    TrainingReportApiResponse,
    TrainingRoundSubmitApiResponse,
    TrainingRoundSubmitRequest,
    TrainingScenarioNextApiResponse,
    TrainingScenarioNextRequest,
    TrainingSessionSummaryApiResponse,
)
from api.services.training_service import TrainingService
from training.training_query_service import TrainingQueryService
from training.exceptions import (
    DuplicateRoundSubmissionError,
    TrainingMediaTaskInvalidError,
    TrainingMediaTaskUnsupportedError,
    TrainingModeUnsupportedError,
    TrainingScenarioMismatchError,
    TrainingSessionCompletedError,
    TrainingSessionNotFoundError,
    TrainingSessionRecoveryStateError,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/training", tags=["training"])


def _serialize_player_profile_request(request: TrainingInitRequest) -> dict | None:
    """Support both Pydantic v1 and v2 request objects."""

    if request.player_profile is None:
        return None
    if hasattr(request.player_profile, "model_dump"):
        return request.player_profile.model_dump(exclude_none=True)
    return request.player_profile.dict(exclude_none=True)


def _serialize_submit_round_media_tasks_request(request: TrainingRoundSubmitRequest) -> list[dict] | None:
    media_tasks = request.media_tasks or []
    if not media_tasks:
        return None

    serialized_items: list[dict] = []
    for item in media_tasks:
        if hasattr(item, "model_dump"):
            serialized_items.append(item.model_dump(exclude_none=True))
        else:
            serialized_items.append(item.dict(exclude_none=True))
    return serialized_items


def _dispatch_submit_round_media_tasks(result: dict) -> None:
    media_tasks = result.get("media_tasks")
    if not isinstance(media_tasks, list) or not media_tasks:
        return

    try:
        executor = get_training_media_task_executor()
    except Exception as exc:
        logger.warning("failed to resolve training media executor during submit dispatch: %s", str(exc))
        return

    for task in media_tasks:
        task_payload = task if isinstance(task, dict) else {}
        task_id = str(task_payload.get("task_id") or "").strip()
        status = str(task_payload.get("status") or "").strip().lower()
        if not task_id or status not in {"pending", "running"}:
            continue
        try:
            executor.submit_task(task_id)
        except Exception as exc:
            logger.warning("failed to dispatch training media task from submit: task_id=%s error=%s", task_id, str(exc))


def _build_training_domain_error_response(
    exc: Exception,
    *,
    route_name: str,
    session_id: str | None = None,
    scenario_id: str | None = None,
):
    """Map typed training-domain exceptions to stable HTTP/error-code contracts."""

    details = {"route": route_name}
    if session_id is not None:
        details["session_id"] = session_id
    if scenario_id is not None:
        details["scenario_id"] = scenario_id

    if isinstance(exc, TrainingSessionNotFoundError):
        return not_found_response(
            message=str(exc),
            error_code=TRAINING_SESSION_NOT_FOUND,
            details=details,
        )

    if isinstance(exc, TrainingSessionCompletedError):
        return error_response(
            code=409,
            message="training session already completed",
            error_code=TRAINING_SESSION_COMPLETED,
            details=details,
        )

    if isinstance(exc, DuplicateRoundSubmissionError):
        return error_response(
            code=409,
            message="duplicate round submission",
            error_code=TRAINING_ROUND_DUPLICATE,
            details=details,
        )

    if isinstance(exc, TrainingModeUnsupportedError):
        details["provided_mode"] = exc.raw_mode or None
        details["supported_modes"] = list(exc.supported_modes)
        return error_response(
            code=400,
            message=str(exc),
            error_code=TRAINING_MODE_UNSUPPORTED,
            details=details,
        )

    if isinstance(exc, TrainingScenarioMismatchError):
        details["round_no"] = exc.round_no
        if exc.expected_scenario_id is not None:
            details["expected_scenario_id"] = exc.expected_scenario_id
        if exc.allowed_scenario_ids:
            details["allowed_scenario_ids"] = list(exc.allowed_scenario_ids)
        return error_response(
            code=409,
            message=str(exc),
            error_code=TRAINING_SCENARIO_MISMATCH,
            details=details,
        )

    if isinstance(exc, TrainingMediaTaskUnsupportedError):
        details["task_type"] = exc.task_type
        if exc.supported_task_types:
            details["supported_task_types"] = list(exc.supported_task_types)
        return error_response(
            code=400,
            message=str(exc),
            error_code=TRAINING_MEDIA_TASK_UNSUPPORTED,
            details=details,
        )

    if isinstance(exc, TrainingMediaTaskInvalidError):
        if exc.details:
            details.update(exc.details)
        return error_response(
            code=400,
            message=str(exc),
            error_code=TRAINING_MEDIA_TASK_INVALID,
            details=details,
        )

    if isinstance(exc, TrainingSessionRecoveryStateError):
        details["recovery_reason"] = exc.reason
        if exc.details:
            details["recovery_details"] = dict(exc.details)
        return error_response(
            code=409,
            message="training session recovery state corrupted",
            error_code=TRAINING_SESSION_RECOVERY_STATE_CORRUPTED,
            details=details,
        )

    raise TypeError(f"unsupported training domain exception: {type(exc)!r}")


@router.post("/init", response_model=TrainingInitApiResponse)
async def init_training(
    request: TrainingInitRequest,
    training_service: TrainingService = Depends(get_training_service),
):
    """Initialize a training session."""

    try:
        result = training_service.init_training(
            user_id=request.user_id,
            character_id=request.character_id,
            training_mode=request.training_mode,
            player_profile=_serialize_player_profile_request(request),
        )
        return build_success_payload(data=result)
    except TrainingModeUnsupportedError as exc:
        return _build_training_domain_error_response(
            exc,
            route_name="training.init",
        )
    except Exception as exc:
        logger.error("failed to initialize training: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to initialize training session",
            error_code=INTERNAL_ERROR,
            details={"route": "training.init"},
        )


@router.post("/scenario/next", response_model=TrainingScenarioNextApiResponse)
async def get_next_scenario(
    request: TrainingScenarioNextRequest,
    training_service: TrainingService = Depends(get_training_service),
):
    """Fetch the next training scenario."""

    try:
        result = training_service.get_next_scenario(request.session_id)
        return build_success_payload(data=result)
    except (TrainingSessionNotFoundError, TrainingSessionRecoveryStateError) as exc:
        return _build_training_domain_error_response(
            exc,
            route_name="training.next",
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.error("failed to get next training scenario: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to get next training scenario",
            error_code=INTERNAL_ERROR,
            details={"route": "training.next", "session_id": request.session_id},
        )


@router.post("/round/submit", response_model=TrainingRoundSubmitApiResponse)
async def submit_round(
    request: TrainingRoundSubmitRequest,
    training_service: TrainingService = Depends(get_training_service),
):
    """Submit a training round."""

    try:
        result = training_service.submit_round(
            session_id=request.session_id,
            scenario_id=request.scenario_id,
            user_input=request.user_input,
            selected_option=request.selected_option,
            media_tasks=_serialize_submit_round_media_tasks_request(request),
        )
        _dispatch_submit_round_media_tasks(result)
        return build_success_payload(data=result)
    except (
        DuplicateRoundSubmissionError,
        TrainingMediaTaskInvalidError,
        TrainingMediaTaskUnsupportedError,
        TrainingScenarioMismatchError,
        TrainingSessionCompletedError,
        TrainingSessionNotFoundError,
        TrainingSessionRecoveryStateError,
    ) as exc:
        return _build_training_domain_error_response(
            exc,
            route_name="training.submit_round",
            session_id=request.session_id,
            scenario_id=request.scenario_id,
        )
    except Exception as exc:
        logger.error("failed to submit training round: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to submit training round",
            error_code=INTERNAL_ERROR,
            details={
                "route": "training.submit_round",
                "session_id": request.session_id,
                "scenario_id": request.scenario_id,
            },
        )


@router.get("/sessions/{session_id}", response_model=TrainingSessionSummaryApiResponse)
async def get_session_summary(
    session_id: str,
    training_query_service: TrainingQueryService = Depends(get_training_query_service),
):
    """Get the recovery summary for a training session."""

    try:
        result = training_query_service.get_session_summary(session_id)
        return build_success_payload(data=result)
    except (TrainingSessionNotFoundError, TrainingSessionRecoveryStateError) as exc:
        return _build_training_domain_error_response(
            exc,
            route_name="training.session_summary",
            session_id=session_id,
        )
    except Exception as exc:
        logger.error("failed to get training session summary: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to get training session summary",
            error_code=INTERNAL_ERROR,
            details={"route": "training.session_summary", "session_id": session_id},
        )


@router.get("/progress/{session_id}", response_model=TrainingProgressApiResponse)
async def get_progress(
    session_id: str,
    training_query_service: TrainingQueryService = Depends(get_training_query_service),
):
    """Get training progress."""

    try:
        result = training_query_service.get_progress(session_id)
        return build_success_payload(data=result)
    except (TrainingSessionNotFoundError, TrainingSessionRecoveryStateError) as exc:
        return _build_training_domain_error_response(
            exc,
            route_name="training.progress",
            session_id=session_id,
        )
    except Exception as exc:
        logger.error("failed to get training progress: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to get training progress",
            error_code=INTERNAL_ERROR,
            details={"route": "training.progress", "session_id": session_id},
        )


@router.get("/sessions/{session_id}/history", response_model=TrainingHistoryApiResponse)
async def get_history(
    session_id: str,
    training_query_service: TrainingQueryService = Depends(get_training_query_service),
):
    """Get the canonical training history read model."""

    try:
        result = training_query_service.get_history(session_id)
        return build_success_payload(data=result)
    except (TrainingSessionNotFoundError, TrainingSessionRecoveryStateError) as exc:
        return _build_training_domain_error_response(
            exc,
            route_name="training.history",
            session_id=session_id,
        )
    except Exception as exc:
        logger.error("failed to get training history: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to get training history",
            error_code=INTERNAL_ERROR,
            details={"route": "training.history", "session_id": session_id},
        )


@router.get("/report/{session_id}", response_model=TrainingReportApiResponse)
async def get_report(
    session_id: str,
    training_query_service: TrainingQueryService = Depends(get_training_query_service),
):
    """Get training report."""

    try:
        result = training_query_service.get_report(session_id)
        return build_success_payload(data=result)
    except (TrainingSessionNotFoundError, TrainingSessionRecoveryStateError) as exc:
        return _build_training_domain_error_response(
            exc,
            route_name="training.report",
            session_id=session_id,
        )
    except Exception as exc:
        logger.error("failed to get training report: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to get training report",
            error_code=INTERNAL_ERROR,
            details={"route": "training.report", "session_id": session_id},
        )


@router.get("/diagnostics/{session_id}", response_model=TrainingDiagnosticsApiResponse)
async def get_diagnostics(
    session_id: str,
    training_query_service: TrainingQueryService = Depends(get_training_query_service),
):
    """Get training diagnostics."""

    try:
        result = training_query_service.get_diagnostics(session_id)
        return build_success_payload(data=result)
    except (TrainingSessionNotFoundError, TrainingSessionRecoveryStateError) as exc:
        return _build_training_domain_error_response(
            exc,
            route_name="training.diagnostics",
            session_id=session_id,
        )
    except Exception as exc:
        logger.error("failed to get training diagnostics: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to get training diagnostics",
            error_code=INTERNAL_ERROR,
            details={"route": "training.diagnostics", "session_id": session_id},
        )
