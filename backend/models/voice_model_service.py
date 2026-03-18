"""语音大模型服务（统一接口，支持多提供商）"""
from typing import Optional, Dict, Any
import os
import sys

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

# 尝试导入依赖
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    dashscope = None
    SpeechSynthesizer = None

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    edge_tts = None


class VoiceModelService:
    """语音大模型服务（用于语音合成：TTS、Voice Design等）
    
    职责：
    - 语音合成（TTS）
    - 支持多提供商（volcengine、dashscope、edge-tts）
    - 统一的接口和错误处理
    """
    
    def __init__(self, provider: Optional[str] = None):
        """初始化语音大模型服务
        
        Args:
            provider: 提供商名称（'volcengine', 'dashscope', 'edge-tts', 'auto'），如果为None则自动检测
        """
        self.provider = provider or self._auto_detect_provider()
        self.enabled = False
        self.model_name = None
        
        if self.provider == 'volcengine':
            self._init_volcengine()
        elif self.provider == 'dashscope':
            self._init_dashscope()
        elif self.provider == 'edge-tts':
            self._init_edge_tts()
        
        if self.enabled:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.info(f"语音大模型已启用 - 提供商: {self.provider}, 模型: {self.model_name}")
    
    def _auto_detect_provider(self) -> str:
        """自动检测可用的提供商"""
        # 优先检查配置的提供商
        configured_provider = getattr(config, 'TTS_PROVIDER', None)
        if configured_provider:
            return configured_provider
        
        # 按优先级检测
        # 1. 检查DashScope
        if DASHSCOPE_AVAILABLE and config.DASHSCOPE_API_KEY:
            return 'dashscope'
        # 2. 检查火山引擎
        if REQUESTS_AVAILABLE and config.VOLCENGINE_ARK_API_KEY and config.VOLCENGINE_ARK_API_KEY.strip():
            return 'volcengine'
        # 3. 检查Edge TTS（免费备选）
        if EDGE_TTS_AVAILABLE:
            return 'edge-tts'
        
        return 'dashscope'  # 默认
    
    def _init_volcengine(self):
        """初始化火山引擎语音服务"""
        if not REQUESTS_AVAILABLE:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.warning("requests未安装，火山引擎语音功能不可用")
            return
        
        volcengine_key = config.VOLCENGINE_ARK_API_KEY.strip() if config.VOLCENGINE_ARK_API_KEY else ''
        if not volcengine_key:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.warning("未配置VOLCENGINE_ARK_API_KEY，火山引擎语音功能不可用")
            return
        
        self.api_key = volcengine_key
        self.app_id = getattr(config, 'VOLCENGINE_TTS_APP_ID', '')
        self.access_token = getattr(config, 'VOLCENGINE_TTS_ACCESS_TOKEN', '')
        self.region = getattr(config, 'VOLCENGINE_REGION', 'cn-beijing')
        self.model_name = getattr(config, 'VOLCENGINE_TTS_MODEL', 'doubao-tts-streaming')
        self.resource_id = getattr(config, 'VOLCENGINE_TTS_RESOURCE_ID', '')
        
        # 构建API端点
        region_map = {
            'cn-beijing': 'openspeech.bytedance.com',
            'cn-north-1': 'openspeech.bytedance.com',
        }
        host = region_map.get(self.region, 'openspeech.bytedance.com')
        self.api_base_url = f"https://{host}/api/v1/tts"
        
        self.enabled = True
        self.voice_design_enabled = False  # 火山引擎不支持Voice Design
    
    def _init_dashscope(self):
        """初始化DashScope语音服务"""
        if not DASHSCOPE_AVAILABLE:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.warning("dashscope未安装，通义千问语音功能不可用")
            return
        
        if not config.DASHSCOPE_API_KEY:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.warning("未配置DASHSCOPE_API_KEY，通义千问语音功能不可用")
            return
        
        dashscope.api_key = config.DASHSCOPE_API_KEY
        self.api_key = config.DASHSCOPE_API_KEY
        self.model_name = getattr(config, 'DASHSCOPE_TTS_MODEL', 'qwen3-tts-vd-realtime')
        self.enabled = True
        self.voice_design_enabled = True  # DashScope支持Voice Design
    
    def _init_edge_tts(self):
        """初始化Edge TTS语音服务"""
        if not EDGE_TTS_AVAILABLE:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.warning("edge-tts未安装，Edge TTS功能不可用")
            return
        
        self.model_name = 'edge-tts'
        self.enabled = True
        self.voice_design_enabled = False  # Edge TTS不支持Voice Design
    
    def synthesize_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        **kwargs
    ) -> Optional[bytes]:
        """合成语音（统一接口）
        
        Args:
            text: 要合成的文本
            voice_id: 音色ID（可选，不同提供商格式不同）
            **kwargs: 其他参数（如emotion_params等）
            
        Returns:
            音频数据（bytes），如果失败返回None
        """
        if not self.enabled:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.warning("语音大模型服务未启用")
            return None
        
        try:
            if self.provider == 'volcengine':
                return self._synthesize_with_volcengine(text, voice_id, **kwargs)
            elif self.provider == 'dashscope':
                return self._synthesize_with_dashscope(text, voice_id, **kwargs)
            elif self.provider == 'edge-tts':
                return self._synthesize_with_edge_tts(text, voice_id, **kwargs)
            else:
                from utils.logger import get_logger
                logger = get_logger(__name__)
                logger.warning(f"未知的语音提供商: {self.provider}")
                return None
        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.error(f"语音大模型合成失败: {e}", exc_info=True)
            return None
    
    def _clean_text_for_volcengine(self, text: str) -> str:
        """清理文本以符合火山引擎TTS API要求
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            raise ValueError("文本不能为空")
        
        # 去除首尾空白字符
        text = text.strip()
        
        if not text:
            raise ValueError("文本不能为空或只包含空白字符")
        
        # 移除控制字符（保留换行符和制表符）
        import re
        # 保留常见的有用字符：换行符(\n)、制表符(\t)、回车符(\r)
        # 移除其他控制字符（ASCII 0-31中除了\n\t\r的字符）
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # 移除零宽字符（可能影响API解析）
        text = re.sub(r'[\u200b-\u200f\ufeff]', '', text)
        
        # 再次检查是否为空（清理后可能变空）
        text = text.strip()
        if not text:
            raise ValueError("文本清理后为空，可能包含不支持的字符")
        
        # 限制文本长度（火山引擎TTS通常限制在5000字符以内）
        max_length = 5000
        if len(text) > max_length:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.warning(f"文本长度超过{max_length}字符，已截断")
            text = text[:max_length]
        
        return text
    
    def _synthesize_with_volcengine(
        self,
        text: str,
        voice_id: Optional[str] = None,
        **kwargs
    ) -> Optional[bytes]:
        """使用火山引擎合成语音"""
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests未安装")
        
        import time
        import json
        import base64
        
        # 清理和验证文本
        try:
            cleaned_text = self._clean_text_for_volcengine(text)
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.debug(f"文本清理: 原始长度={len(text)}, 清理后长度={len(cleaned_text)}")
        except ValueError as e:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.error(f"文本验证失败: {e}, 原始文本: {repr(text[:100])}")
            raise ValueError(f"文本验证失败: {e}")
        
        # 构建请求参数
        request_data = {
            "app": {
                "appid": self.app_id,
                "token": self.access_token,
                "cluster": "volcano_tts"
            },
            "user": {
                "uid": "user_001"
            },
            "audio": {
                "voice_type": voice_id or "BV001_streaming",
                "encoding": "wav",
                "speed_ratio": kwargs.get('speed_ratio', 1.0),
                "volume_ratio": kwargs.get('volume_ratio', 1.0),
                "pitch_ratio": kwargs.get('pitch_ratio', 1.0)
            },
            "request": {
                "reqid": f"tts_{int(time.time())}_{hash(cleaned_text) % 10000}",
                "text": cleaned_text,
                "text_type": "plain",
                "operation": "query"
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer; {self.access_token}",
        }
        
        if self.resource_id:
            headers["X-Resource-Id"] = self.resource_id
        
        response = requests.post(
            self.api_base_url,
            headers=headers,
            json=request_data,
            timeout=30
        )
        
        # 解析响应（无论HTTP状态码如何，都尝试解析JSON）
        try:
            data = response.json()
        except Exception as e:
            # 如果无法解析JSON，使用HTTP状态码和原始文本
            error_msg = response.text[:500] if response.text else "未知错误"
            raise ValueError(f"火山引擎返回格式异常，无法解析JSON: {e}。HTTP {response.status_code}, {error_msg}")
        
        # 检查业务错误代码（火山引擎API在HTTP 200时也可能返回错误代码）
        error_code = data.get('code')
        if error_code != 3000:
            error_msg = data.get('message', '未知错误')
            error_operation = data.get('operation', 'unknown')
            
            # 特殊处理常见错误
            if error_code == 3011:
                # 3011: illegal input text
                from utils.logger import get_logger
                logger = get_logger(__name__)
                logger.error(f"文本格式错误（3011）: {error_msg}, 原始文本: {repr(text[:200])}, 清理后文本: {repr(cleaned_text[:200])}")
                raise ValueError(f"文本格式错误（错误代码3011）: {error_msg}。请检查文本是否包含非法字符或为空。原始文本长度: {len(text)}, 清理后长度: {len(cleaned_text)}")
            elif error_code == 3001:
                # 3001: 认证失败
                raise ValueError(f"认证失败（错误代码3001）: {error_msg}。请检查APP_ID、ACCESS_TOKEN和SECRET_KEY是否正确。")
            elif error_code == 3002:
                # 3002: 参数错误
                raise ValueError(f"参数错误（错误代码{error_code}）: {error_msg}。")
            else:
                raise ValueError(f"火山引擎语音合成失败（错误代码{error_code}）: {error_msg}")
        
        # 检查HTTP状态码（如果业务代码是3000但HTTP不是200，也报错）
        if response.status_code != 200:
            error_msg = response.text[:500] if response.text else "未知错误"
            raise ValueError(f"火山引擎语音合成失败: HTTP {response.status_code}, {error_msg}")
        
        # 成功响应
        audio_data = data.get('data', '')
        if audio_data:
            return base64.b64decode(audio_data)
        
        raise ValueError("火山引擎返回格式异常：data字段为空")
    
    def _synthesize_with_dashscope(
        self,
        text: str,
        voice_id: Optional[str] = None,
        **kwargs
    ) -> Optional[bytes]:
        """使用DashScope合成语音"""
        if not DASHSCOPE_AVAILABLE:
            raise ImportError("dashscope未安装")
        
        try:
            synthesizer = SpeechSynthesizer(
                model=self.model_name,
                voice=voice_id or 'zhichu'
            )
            
            result = synthesizer.call(text=text)
            
            if result and hasattr(result, 'get_audio_data'):
                return result.get_audio_data()
            
            raise ValueError("DashScope返回格式异常")
        except Exception as e:
            print(f"[DashScope语音错误] {e}")
            raise
    
    def _synthesize_with_edge_tts(
        self,
        text: str,
        voice_id: Optional[str] = None,
        **kwargs
    ) -> Optional[bytes]:
        """使用Edge TTS合成语音"""
        if not EDGE_TTS_AVAILABLE:
            raise ImportError("edge-tts未安装")
        
        import asyncio
        
        async def _generate():
            voice = voice_id or 'zh-CN-XiaoxiaoNeural'
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data
        
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(_generate())
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            return asyncio.run(_generate())
    
    def get_provider(self) -> str:
        """获取当前使用的提供商名称"""
        return self.provider if self.enabled else "none"
    
    def get_model(self) -> str:
        """获取当前使用的模型名称"""
        return self.model_name if self.enabled else "none"
    
    def is_voice_design_enabled(self) -> bool:
        """检查是否支持Voice Design功能"""
        return getattr(self, 'voice_design_enabled', False)
