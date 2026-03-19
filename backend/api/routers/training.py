"""Training API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import get_training_service
from api.error_codes import INTERNAL_ERROR, VALIDATION_ERROR, infer_training_error_code
from api.response import build_success_payload, error_response, not_found_response
from api.schemas import (
    TrainingDiagnosticsApiResponse,
    TrainingInitApiResponse,
    TrainingInitRequest,
    TrainingProgressApiResponse,
    TrainingReportApiResponse,
    TrainingRoundSubmitApiResponse,
    TrainingRoundSubmitRequest,
    TrainingScenarioNextApiResponse,
    TrainingScenarioNextRequest,
)
from api.services.training_service import TrainingService
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
    except ValueError as exc:
        message = str(exc)
        return error_response(
            code=400,
            message=message,
            error_code=infer_training_error_code(message, default=VALIDATION_ERROR),
            details={"route": "training.init"},
        )
    except Exception as exc:
        logger.error("failed to initialize training: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"初始化训练失败: {str(exc)}",
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
    except ValueError as exc:
        message = str(exc)
        return not_found_response(
            message=message,
            error_code=infer_training_error_code(message),
            details={"route": "training.next", "session_id": request.session_id},
        )
    except Exception as exc:
        logger.error("failed to get next training scenario: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"获取下一场景失败: {str(exc)}",
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
        )
        return build_success_payload(data=result)
    except ValueError as exc:
        message = str(exc)
        return error_response(
            code=400,
            message=message,
            error_code=infer_training_error_code(message, default=VALIDATION_ERROR),
            details={
                "route": "training.submit_round",
                "session_id": request.session_id,
                "scenario_id": request.scenario_id,
            },
        )
    except Exception as exc:
        logger.error("failed to submit training round: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"提交训练回合失败: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={
                "route": "training.submit_round",
                "session_id": request.session_id,
                "scenario_id": request.scenario_id,
            },
        )


@router.get("/progress/{session_id}", response_model=TrainingProgressApiResponse)
async def get_progress(
    session_id: str,
    training_service: TrainingService = Depends(get_training_service),
):
    """Get training progress."""

    try:
        result = training_service.get_progress(session_id)
        return build_success_payload(data=result)
    except ValueError as exc:
        message = str(exc)
        return not_found_response(
            message=message,
            error_code=infer_training_error_code(message),
            details={"route": "training.progress", "session_id": session_id},
        )
    except Exception as exc:
        logger.error("failed to get training progress: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"获取训练进度失败: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "training.progress", "session_id": session_id},
        )


@router.get("/report/{session_id}", response_model=TrainingReportApiResponse)
async def get_report(
    session_id: str,
    training_service: TrainingService = Depends(get_training_service),
):
    """Get training report."""

    try:
        result = training_service.get_report(session_id)
        return build_success_payload(data=result)
    except ValueError as exc:
        message = str(exc)
        return not_found_response(
            message=message,
            error_code=infer_training_error_code(message),
            details={"route": "training.report", "session_id": session_id},
        )
    except Exception as exc:
        logger.error("failed to get training report: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"获取训练报告失败: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "training.report", "session_id": session_id},
        )


@router.get("/diagnostics/{session_id}", response_model=TrainingDiagnosticsApiResponse)
async def get_diagnostics(
    session_id: str,
    training_service: TrainingService = Depends(get_training_service),
):
    """Get training diagnostics."""

    try:
        result = training_service.get_diagnostics(session_id)
        return build_success_payload(data=result)
    except ValueError as exc:
        message = str(exc)
        return not_found_response(
            message=message,
            error_code=infer_training_error_code(message),
            details={"route": "training.diagnostics", "session_id": session_id},
        )
    except Exception as exc:
        logger.error("failed to get training diagnostics: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"获取训练诊断失败: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "training.diagnostics", "session_id": session_id},
        )
