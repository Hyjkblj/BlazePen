"""TTS语音合成API路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from api.response import success_response, error_response
from api.services.tts_service import TTSService
from api.dependencies import get_tts_service
from fastapi import Depends
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/tts", tags=["TTS语音合成"])


def _tts_error_response(exc: Exception, provider: str = 'volcengine') -> tuple[int, str]:
    """将 TTS 异常转为对前端的 (code, message)。鉴权/计费错误返回 503 与友好提示。
    
    Args:
        exc: 异常对象
        provider: TTS 提供商名称（volcengine, dashscope, edge-tts）
    """
    msg = str(exc)
    
    # 根据提供商生成对应的错误提示
    provider_messages = {
        'volcengine': '语音服务暂不可用，请检查火山引擎（VolcEngine）账号状态与计费。',
        'dashscope': '语音服务暂不可用，请检查阿里云百炼（DashScope）账号状态与计费。',
        'edge-tts': '语音服务暂不可用，请检查网络连接或 Edge TTS 服务状态。',
    }
    default_message = provider_messages.get(provider, '语音服务暂不可用，请检查服务配置。')
    
    if (
        "Access denied" in msg or "account is in good standing" in msg or "overdue" in msg.lower()
        or "websocket closed" in msg.lower() or "closed due to" in msg.lower()
        or "未返回音频数据" in msg or "语音服务暂不可用" in msg
        or "TTS服务未启用" in msg or "enabled" in msg.lower() and "false" in msg.lower()
    ):
        return 503, default_message
    return 500, f"语音服务异常: {msg}"


class TTSGenerateRequest(BaseModel):
    """TTS生成请求"""
    text: str
    character_id: int
    emotion_params: Optional[Dict[str, Any]] = None
    use_cache: bool = True


class VoiceDesignRequest(BaseModel):
    """Voice Design请求"""
    description: str  # 音色描述文本（不超过2048字符）
    character_id: Optional[int] = None  # 可选，用于关联角色


class VoiceConfigRequest(BaseModel):
    """音色配置请求"""
    character_id: int
    voice_type: str  # preset, custom, voice_design
    preset_voice_id: Optional[str] = None
    voice_design_description: Optional[str] = None
    voice_params: Optional[Dict[str, Any]] = {}


@router.post("/generate")
async def generate_speech(
    request: TTSGenerateRequest,
    tts_service: TTSService = Depends(get_tts_service)
):
    """生成语音
    
    根据文本和角色ID生成语音，支持情绪参数和缓存。
    """
    try:
        if not tts_service.enabled:
            return error_response(
                code=503,
                message="TTS服务未启用，请检查配置"
            )
        
        audio_info = tts_service.generate_speech(
            text=request.text,
            character_id=request.character_id,
            emotion_params=request.emotion_params,
            use_cache=request.use_cache
        )
        
        return success_response(data={
            'audio_url': audio_info['audio_url'],
            'audio_path': audio_info['audio_path'],
            'duration': audio_info.get('duration', 0),
            'cached': audio_info.get('cached', False)
        })
    
    except ValueError as e:
        return error_response(code=400, message=str(e))
    except Exception as e:
        logger.error(f"TTS API错误: {e}", exc_info=True)
        code, message = _tts_error_response(e, provider=tts_service.provider)
        return error_response(code=code, message=message)


@router.post("/voice-design/create")
async def create_voice_design(
    request: VoiceDesignRequest,
    tts_service: TTSService = Depends(get_tts_service)
):
    """创建自定义音色（Voice Design）
    
    通过文本描述生成自定义音色。
    """
    try:
        if not tts_service.voice_design_enabled:
            return error_response(
                code=503,
                message="Voice Design功能未启用"
            )
        
        result = tts_service.create_voice_from_description(
            description=request.description,
            character_id=request.character_id
        )
        
        if result['success']:
            return success_response(data={
                'voice_id': result['voice_id'],
                'message': result['message']
            })
        else:
            return error_response(
                code=500,
                message=result['message']
            )
    
    except Exception as e:
        logger.error(f"Voice Design API错误: {e}", exc_info=True)
        return error_response(code=500, message=f"创建自定义音色失败: {str(e)}")


@router.post("/voice/config")
async def set_voice_config(
    request: VoiceConfigRequest,
    tts_service: TTSService = Depends(get_tts_service)
):
    """设置角色音色配置
    
    设置角色的音色类型、预设音色ID或Voice Design描述。
    """
    try:
        # 获取角色音色配置
        voice_config = tts_service.get_character_voice_config(request.character_id)
        
        # 更新配置
        voice_config['voice_type'] = request.voice_type
        voice_config['preset_voice_id'] = request.preset_voice_id
        voice_config['voice_design_description'] = request.voice_design_description
        voice_config['voice_params'] = request.voice_params or {}
        
        # 保存配置（实际应该保存到数据库）
        tts_service.voice_configs[request.character_id] = voice_config
        
        return success_response(data={
            'character_id': request.character_id,
            'voice_config': voice_config,
            'message': '音色配置已保存'
        })
    
    except Exception as e:
        logger.error(f"音色配置API错误: {e}", exc_info=True)
        return error_response(code=500, message=f"保存音色配置失败: {str(e)}")


@router.get("/voice/config/{character_id}")
async def get_voice_config(
    character_id: int,
    tts_service: TTSService = Depends(get_tts_service)
):
    """获取角色音色配置"""
    try:
        voice_config = tts_service.get_character_voice_config(character_id)
        return success_response(data={
            'character_id': character_id,
            'voice_config': voice_config
        })
    except Exception as e:
        return error_response(code=500, message=f"获取音色配置失败: {str(e)}")


@router.get("/status")
async def get_tts_status(
    tts_service: TTSService = Depends(get_tts_service)
):
    """获取 TTS 服务状态
    
    返回 TTS 服务的启用状态、提供商、模型等信息。
    """
    return success_response(data={
        'enabled': tts_service.enabled,
        'provider': tts_service.provider,
        'model': tts_service.voice_model.get_model() if hasattr(tts_service.voice_model, 'get_model') else None,
        'voice_design_enabled': tts_service.voice_design_enabled,
        'message': 'TTS服务已启用' if tts_service.enabled else 'TTS服务未启用，请检查配置'
    })


@router.get("/presets")
async def get_preset_voices(
    gender: Optional[str] = None,
    tts_service: TTSService = Depends(get_tts_service)
):
    """获取预设音色列表
    
    Args:
        gender: 性别筛选（male, female, neutral），不传则返回所有
    """
    try:
        from data.preset_voices import get_preset_voices_by_gender, get_all_preset_voices
        
        if gender:
            voices = get_preset_voices_by_gender(gender)
            return success_response(data={
                'gender': gender,
                'voices': voices
            })
        else:
            all_voices = get_all_preset_voices()
            return success_response(data={
                'voices': all_voices
            })
    except Exception as e:
        return error_response(code=500, message=f"获取预设音色列表失败: {str(e)}")


class TTSPreviewRequest(BaseModel):
    """TTS 试听请求"""
    preset_voice_id: str  # 预设音色 ID（如 female_001）
    text: Optional[str] = None  # 不传则使用该音色的 preview_text


@router.post("/preview")
async def preview_voice(
    request: TTSPreviewRequest,
    tts_service: TTSService = Depends(get_tts_service)
):
    """试听预设音色：根据 preset_voice_id 合成一段语音并返回 audio_url"""
    try:
        from data.preset_voices import get_preset_voice
        voice = get_preset_voice(request.preset_voice_id)
        if not voice:
            return error_response(code=404, message="音色不存在")
        text = (request.text or voice.get("preview_text") or "你好，这是试听。")[:600]
        bailian_voice_id = voice.get("voice_id") or "Cherry"
        if not tts_service.enabled:
            provider_name = {
                'volcengine': '火山引擎（VolcEngine）',
                'dashscope': '阿里云百炼（DashScope）',
                'edge-tts': 'Edge TTS',
            }.get(tts_service.provider, 'TTS服务')
            return error_response(
                code=503,
                message=f"TTS服务未启用，请检查{provider_name}配置"
            )
        audio_info = tts_service.generate_speech(
            text=text,
            character_id=0,
            use_cache=True,
            override_voice_id=bailian_voice_id,
        )
        return success_response(data={
            "audio_url": audio_info["audio_url"],
            "duration": audio_info.get("duration", 0),
        })
    except Exception as e:
        logger.error(f"TTS Preview错误: {e}", exc_info=True)
        code, message = _tts_error_response(e, provider=tts_service.provider)
        return error_response(code=code, message=message)


@router.get("/presets/{voice_id}/preview")
async def get_voice_preview(
    voice_id: str,
    tts_service: TTSService = Depends(get_tts_service)
):
    """获取音色预览信息"""
    try:
        from data.preset_voices import get_preset_voice
        
        voice = get_preset_voice(voice_id)
        if not voice:
            return error_response(code=404, message="音色不存在")
        
        return success_response(data={
            'voice_id': voice_id,
            'name': voice.get('name'),
            'description': voice.get('description'),
            'preview_text': voice.get('preview_text'),
            'voice_id_bailian': voice.get('voice_id')
        })
    except Exception as e:
        return error_response(code=500, message=f"获取音色预览失败: {str(e)}")


@router.get("/voice-design/list")
async def list_voices(
    page_index: int = 0,
    page_size: int = 10,
    tts_service: TTSService = Depends(get_tts_service)
):
    """查询已创建的自定义音色列表（Voice Design）
    
    Args:
        page_index: 页码索引（0-200），默认0
        page_size: 每页包含数据条数，默认10
    """
    try:
        if not tts_service.voice_design_enabled:
            return error_response(
                code=503,
                message="Voice Design功能未启用"
            )
        
        result = tts_service.list_voices(
            page_index=page_index,
            page_size=page_size
        )
        
        if result['success']:
            return success_response(data={
                'voices': result['voices'],
                'total_count': result['total_count'],
                'page_index': result.get('page_index', page_index),
                'page_size': result.get('page_size', page_size),
                'message': result['message']
            })
        else:
            return error_response(
                code=500,
                message=result['message']
            )
    
    except Exception as e:
        logger.error(f"查询音色列表API错误: {e}", exc_info=True)
        return error_response(code=500, message=f"查询音色列表失败: {str(e)}")
