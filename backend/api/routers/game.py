"""游戏管理API路由"""
import re
from fastapi import APIRouter, HTTPException, Depends
from api.schemas import (
    GameInitRequest,
    GameInitResponse,
    GameInputRequest,
    GameInputResponse,
    CheckEndingResponse,
    TriggerEndingRequest
)
from api.response import success_response, error_response, not_found_response
from api.services.game_service import GameService
from api.dependencies import get_game_service
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/game", tags=["游戏管理"])


@router.post("/init", response_model=dict)
async def init_game(
    request: GameInitRequest,
    game_service: GameService = Depends(get_game_service)
):
    """初始化游戏"""
    try:
        logger.info(f"收到初始化请求: user_id={request.user_id}, character_id={request.character_id}, game_mode={request.game_mode}")
        
        character_id = None
        if request.character_id:
            character_id = int(request.character_id)
        else:
            logger.error("character_id is required")
            return error_response(code=400, message="character_id is required")
        
        logger.info("开始初始化游戏会话...")
        result = game_service.init_game(
            user_id=request.user_id,
            character_id=character_id,
            game_mode=request.game_mode
        )
        
        logger.info(f"游戏初始化成功: thread_id={result.get('thread_id')}, user_id={result.get('user_id')}")
        return success_response(data=result)
    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        return error_response(code=400, message=f"参数错误: {str(e)}")
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}", exc_info=True)
        return error_response(code=500, message=f"初始化游戏失败: {str(e)}")


@router.post("/input", response_model=dict)
async def process_input(
    request: GameInputRequest,
    game_service: GameService = Depends(get_game_service)
):
    """处理玩家输入"""
    try:
        # 尝试从user_input中解析option_id（仅接受严格格式: option:<number>）
        option_id = None
        user_input = (request.user_input or "").strip()

        option_match = re.fullmatch(r"option:(\d+)", user_input, flags=re.IGNORECASE)
        if option_match:
            option_id = int(option_match.group(1)) - 1  # 转换为0-based索引
            user_input = ""  # 清空user_input，使用选项
        elif user_input.lower().startswith("option:"):
            return error_response(code=400, message="无效的选项格式，应为 option:<number>")

        def _process_with_session_lock(target_thread_id: str, input_text: str, input_option_id):
            target_session = game_service.session_manager.get_session(target_thread_id)
            if target_session and hasattr(target_session, "lock"):
                with target_session.lock:
                    return game_service.process_input(
                        thread_id=target_thread_id,
                        user_input=input_text,
                        option_id=input_option_id
                    )
            return game_service.process_input(
                thread_id=target_thread_id,
                user_input=input_text,
                option_id=input_option_id
            )
        
        try:
            result = _process_with_session_lock(
                target_thread_id=request.thread_id,
                input_text=user_input,
                input_option_id=option_id
            )
        except ValueError as e:
            # 如果会话不存在，尝试自动恢复
            if "not found" in str(e).lower() and request.character_id:
                try:
                    # 重新初始化游戏会话
                    character_id_int = int(request.character_id)
                    init_result = game_service.init_game(
                        user_id=request.user_id,
                        character_id=character_id_int,
                        game_mode='solo'
                    )
                    new_thread_id = init_result['thread_id']
                    
                    # 初始化故事
                    restored_story = game_service.initialize_story(new_thread_id, character_id_int)

                    # 关键修复：旧会话的选项不重放到新会话，避免“点了A却执行新会话的A”错配
                    if option_id is not None:
                        restored_story['thread_id'] = new_thread_id
                        restored_story['session_restored'] = True
                        restored_story['need_reselect_option'] = True
                        restored_story['restored_from_thread_id'] = request.thread_id
                        return success_response(
                            data=restored_story,
                            message="会话已恢复，请重新选择选项"
                        )

                    # 非选项输入可在新会话中继续处理
                    result = _process_with_session_lock(
                        target_thread_id=new_thread_id,
                        input_text=user_input,
                        input_option_id=option_id
                    )
                    
                    # 在响应中返回新的thread_id，让前端更新
                    result['thread_id'] = new_thread_id
                    result['session_restored'] = True
                except Exception as restore_error:
                    return error_response(
                        code=400, 
                        message=f"会话已过期且无法恢复: {str(e)}。请重新开始游戏。"
                    )
            else:
                raise
        
        return success_response(data=result)
    except ValueError as e:
        logger.error(f"参数错误: {str(e)}", exc_info=True)
        return error_response(code=400, message=f"参数错误: {str(e)}")
    except Exception as e:
        logger.error(f"处理输入失败: {str(e)}", exc_info=True)
        import traceback
        error_trace = traceback.format_exc()
        return error_response(code=500, message=f"处理输入失败: {str(e)}", error={"traceback": error_trace})


@router.get("/check-ending/{thread_id}", response_model=dict)
async def check_ending(thread_id: str):
    """检查是否满足结局条件"""
    try:
        result = game_service.check_ending(thread_id)
        return success_response(data=result)
    except ValueError as e:
        return not_found_response(message=str(e))
    except Exception as e:
        return error_response(code=500, message=f"检查结局失败: {str(e)}")


@router.post("/trigger-ending", response_model=dict)
async def trigger_ending(
    request: TriggerEndingRequest,
    game_service: GameService = Depends(get_game_service)
):
    """触发结局"""
    try:
        result = game_service.trigger_ending(request.thread_id)
        return success_response(data=result)
    except ValueError as e:
        return not_found_response(message=str(e))
    except Exception as e:
        return error_response(code=500, message=f"触发结局失败: {str(e)}")

