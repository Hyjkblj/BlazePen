"""训练系统API路由"""
from fastapi import APIRouter, Depends

from api.dependencies import get_training_service
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

router = APIRouter(prefix="/v1/training", tags=["训练系统"])


def _serialize_player_profile_request(request: TrainingInitRequest) -> dict | None:
    """统一兼容 Pydantic v1/v2 的玩家档案导出方式。"""
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
    """初始化训练会话"""
    try:
        result = training_service.init_training(
            user_id=request.user_id,
            character_id=request.character_id,
            training_mode=request.training_mode,
            player_profile=_serialize_player_profile_request(request),
        )
        return build_success_payload(data=result)
    except ValueError as e:
        return error_response(code=400, message=str(e))
    except Exception as e:
        logger.error("初始化训练失败: %s", str(e), exc_info=True)
        return error_response(code=500, message=f"初始化训练失败: {str(e)}")


@router.post("/scenario/next", response_model=TrainingScenarioNextApiResponse)
async def get_next_scenario(
    request: TrainingScenarioNextRequest,
    training_service: TrainingService = Depends(get_training_service),
):
    """获取下一训练场景"""
    try:
        result = training_service.get_next_scenario(request.session_id)
        return build_success_payload(data=result)
    except ValueError as e:
        return not_found_response(message=str(e))
    except Exception as e:
        logger.error("获取下一场景失败: %s", str(e), exc_info=True)
        return error_response(code=500, message=f"获取下一场景失败: {str(e)}")


@router.post("/round/submit", response_model=TrainingRoundSubmitApiResponse)
async def submit_round(
    request: TrainingRoundSubmitRequest,
    training_service: TrainingService = Depends(get_training_service),
):
    """提交训练回合"""
    try:
        result = training_service.submit_round(
            session_id=request.session_id,
            scenario_id=request.scenario_id,
            user_input=request.user_input,
            selected_option=request.selected_option,
        )
        return build_success_payload(data=result)
    except ValueError as e:
        return error_response(code=400, message=str(e))
    except Exception as e:
        logger.error("提交训练回合失败: %s", str(e), exc_info=True)
        return error_response(code=500, message=f"提交训练回合失败: {str(e)}")


@router.get("/progress/{session_id}", response_model=TrainingProgressApiResponse)
async def get_progress(
    session_id: str,
    training_service: TrainingService = Depends(get_training_service),
):
    """获取训练进度"""
    try:
        result = training_service.get_progress(session_id)
        return build_success_payload(data=result)
    except ValueError as e:
        return not_found_response(message=str(e))
    except Exception as e:
        logger.error("获取训练进度失败: %s", str(e), exc_info=True)
        return error_response(code=500, message=f"获取训练进度失败: {str(e)}")


@router.get("/report/{session_id}", response_model=TrainingReportApiResponse)
async def get_report(
    session_id: str,
    training_service: TrainingService = Depends(get_training_service),
):
    """获取训练报告"""
    try:
        result = training_service.get_report(session_id)
        return build_success_payload(data=result)
    except ValueError as e:
        return not_found_response(message=str(e))
    except Exception as e:
        logger.error("获取训练报告失败: %s", str(e), exc_info=True)
        return error_response(code=500, message=f"获取训练报告失败: {str(e)}")


@router.get("/diagnostics/{session_id}", response_model=TrainingDiagnosticsApiResponse)
async def get_diagnostics(
    session_id: str,
    training_service: TrainingService = Depends(get_training_service),
):
    """获取训练诊断数据"""
    try:
        result = training_service.get_diagnostics(session_id)
        return build_success_payload(data=result)
    except ValueError as e:
        return not_found_response(message=str(e))
    except Exception as e:
        logger.error("获取训练诊断失败: %s", str(e), exc_info=True)
        return error_response(code=500, message=f"获取训练诊断失败: {str(e)}")
