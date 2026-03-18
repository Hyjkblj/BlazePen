"""TTS语音合成服务（业务层，使用VoiceModelService）"""
import os
import hashlib
import json
import time
from typing import Optional, Dict, Any
from pathlib import Path
import sys

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config
from utils.logger import get_logger

# 导入语音大模型服务
from models.voice_model_service import VoiceModelService

logger = get_logger(__name__)

# 尝试导入依赖
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests未安装，HTTP TTS功能将不可用。请运行: pip install requests")

try:
    from .websocket_tts_service import WebSocketTTSServiceSync
    WEBSOCKET_TTS_AVAILABLE = True
except ImportError:
    WEBSOCKET_TTS_AVAILABLE = False
    logger.warning("WebSocket TTS服务不可用")


class TTSService:
    """TTS语音合成服务（业务层，支持缓存、角色配置等功能）
    
    职责：
    - 业务层封装（缓存管理、角色音色配置等）
    - 使用VoiceModelService进行实际的语音合成
    - 支持WebSocket模式（火山引擎）
    """
    
    def __init__(self, voice_model_service: Optional[VoiceModelService] = None):
        """初始化TTS服务
        
        Args:
            voice_model_service: 语音大模型服务实例，如果为None则自动创建
        """
        # 使用传入的语音大模型服务，或创建新的实例
        self.voice_model = voice_model_service or VoiceModelService(provider=config.TTS_PROVIDER)
        
        self.provider = self.voice_model.get_provider()
        self.enabled = self.voice_model.enabled
        self.voice_design_enabled = self.voice_model.is_voice_design_enabled()
        
        self.cache_dir = Path(backend_dir) / 'audio' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存角色音色配置
        self.voice_configs = {}
        
        # 特殊处理：火山引擎的WebSocket模式
        if self.provider == 'volcengine':
            self._init_volcengine_tts()
        elif self.provider == 'dashscope':
            self._init_dashscope_tts()
        elif self.provider == 'edge-tts':
            self._init_edge_tts()
        
        if self.enabled:
            logger.info(f"TTS服务已初始化 - 提供商: {self.provider}, 模型: {self.voice_model.get_model()}")
    
    def _init_volcengine_tts(self):
        """初始化火山引擎TTS（特殊处理WebSocket模式）"""
        # 火山引擎TTS配置
        self.volcengine_app_id = config.VOLCENGINE_TTS_APP_ID
        self.volcengine_access_token = config.VOLCENGINE_TTS_ACCESS_TOKEN
        self.volcengine_secret_key = config.VOLCENGINE_TTS_SECRET_KEY
        self.volcengine_region = config.VOLCENGINE_REGION
        
        # TTS模型配置
        self.tts_model = config.VOLCENGINE_TTS_MODEL
        self.resource_id = config.VOLCENGINE_TTS_RESOURCE_ID
        self.use_websocket = config.VOLCENGINE_TTS_USE_WEBSOCKET
        
        # 初始化服务
        self.websocket_service = None
        self.http_service_enabled = False
        
        # 选择服务模式（优先WebSocket）
        if self.use_websocket and WEBSOCKET_TTS_AVAILABLE:
            try:
                self.websocket_service = WebSocketTTSServiceSync()
                if self.websocket_service.enabled:
                    self.service_mode = 'websocket'
                    logger.info(f"TTS服务已启用WebSocket模式 - 提供商: 火山引擎(Doubao), 模型: {self.tts_model}")
                else:
                    self.service_mode = 'http'
                    logger.warning("WebSocket TTS服务初始化失败，回退到HTTP模式")
            except Exception as e:
                logger.warning(f"WebSocket TTS服务初始化错误: {e}，回退到HTTP模式", exc_info=True)
                self.service_mode = 'http'
        else:
            self.service_mode = 'http'
        
        if self.service_mode == 'http':
            self.http_service_enabled = True
            logger.info(f"TTS服务使用HTTP模式 - 提供商: 火山引擎(Doubao), 模型: {self.tts_model}")
    
    def _init_dashscope_tts(self):
        """初始化DashScope TTS（使用VoiceModelService）"""
        self.service_mode = 'dashscope'
        self.tts_model = self.voice_model.get_model()
    
    def generate_speech(
        self,
        text: str,
        character_id: int,
        emotion_params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        override_voice_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成语音
        
        Args:
            text: 要合成的文本
            character_id: 角色ID（用于选择声音）
            emotion_params: 情绪参数
            override_voice_id: 若提供则优先使用该预设音色（用于试听）
            use_cache: 是否使用缓存
        
        Returns:
            {
                'audio_url': '/static/audio/xxx.wav',
                'audio_path': '/path/to/audio.wav',
                'duration': 3.5,  # 音频时长（秒）
                'cached': True     # 是否来自缓存
            }
        """
        if not self.enabled:
            raise ValueError("TTS服务未启用，请检查配置")
        
        # 根据提供商调用相应的方法
        if self.provider == 'volcengine':
            return self._generate_speech_volcengine(
                text=text,
                character_id=character_id,
                emotion_params=emotion_params,
                use_cache=use_cache,
                override_voice_id=override_voice_id
            )
        elif self.provider == 'dashscope':
            return self._generate_speech_dashscope(
                text=text,
                character_id=character_id,
                emotion_params=emotion_params,
                use_cache=use_cache,
                override_voice_id=override_voice_id
            )
        elif self.provider == 'edge-tts':
            return self._generate_speech_edge_tts(
                text=text,
                character_id=character_id,
                emotion_params=emotion_params,
                use_cache=use_cache,
                override_voice_id=override_voice_id
            )
        else:
            raise ValueError(f"不支持的TTS提供商: {self.provider}")
    
    def _generate_speech_edge_tts(
        self,
        text: str,
        character_id: int,
        emotion_params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        override_voice_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """使用Edge TTS生成语音（使用VoiceModelService）"""
        # 生成缓存键
        cache_key = self._generate_cache_key(text, character_id, override_voice_id, emotion_params)
        cache_path = self.cache_dir / f"{cache_key}.wav"
        
        # 检查缓存
        if use_cache and cache_path.exists():
            return {
                'audio_url': f'/static/audio/cache/{cache_key}.wav',
                'audio_path': str(cache_path),
                'cached': True,
                'duration': self._get_audio_duration(cache_path)
            }
        
        # 获取音色配置
        voice_id = override_voice_id or self._get_edge_voice(character_id)
        
        # 使用VoiceModelService合成语音
        audio_data = self.voice_model.synthesize_speech(
            text=text,
            voice_id=voice_id
        )
        
        if not audio_data:
            raise ValueError("Edge TTS调用失败: 未返回有效结果")
        
        # 保存音频数据
        cache_path.write_bytes(audio_data)
        
        return {
            'audio_url': f'/static/audio/cache/{cache_key}.wav',
            'audio_path': str(cache_path),
            'duration': self._get_audio_duration(cache_path),
            'cached': False
        }
    
    def _generate_speech_volcengine(
        self,
        text: str,
        character_id: int,
        emotion_params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        override_voice_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """使用火山引擎生成语音"""
        # 获取角色音色配置（试听时使用 override_voice_id）
        if override_voice_id:
            voice_id = self._resolve_preset_voice_id(override_voice_id) or override_voice_id
        else:
            voice_config = self.get_character_voice_config(character_id)
            raw_voice_id = voice_config.get('preset_voice_id') or self._get_default_voice(character_id)
            voice_id = self._resolve_preset_voice_id(raw_voice_id) if raw_voice_id else raw_voice_id
        
        # 根据服务模式调用相应的方法
        if self.service_mode == 'websocket' and self.websocket_service:
            return self.websocket_service.generate_speech(
                text=text,
                character_id=character_id,
                override_voice_id=voice_id,
                emotion_params=emotion_params,
                use_cache=use_cache
            )
        else:
            return self._generate_speech_http(
                text=text,
                character_id=character_id,
                voice_id=voice_id,
                emotion_params=emotion_params,
                use_cache=use_cache
            )
    
    def _generate_speech_dashscope(
        self,
        text: str,
        character_id: int,
        emotion_params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        override_voice_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """使用DashScope生成语音（使用VoiceModelService）"""
        # 生成缓存键
        cache_key = self._generate_cache_key(text, character_id, override_voice_id, emotion_params)
        cache_path = self.cache_dir / f"{cache_key}.wav"
        
        # 检查缓存
        if use_cache and cache_path.exists():
            return {
                'audio_url': f'/static/audio/cache/{cache_key}.wav',
                'audio_path': str(cache_path),
                'cached': True,
                'duration': self._get_audio_duration(cache_path)
            }
        
        # 获取音色配置
        voice_id = override_voice_id or self._get_dashscope_voice(character_id)
        
        # 使用VoiceModelService合成语音
        audio_data = self.voice_model.synthesize_speech(
            text=text,
            voice_id=voice_id
        )
        
        if not audio_data:
            raise ValueError("DashScope TTS调用失败: 未返回有效结果")
        
        # 保存音频数据
        cache_path.write_bytes(audio_data)
        
        return {
            'audio_url': f'/static/audio/cache/{cache_key}.wav',
            'audio_path': str(cache_path),
            'duration': self._get_audio_duration(cache_path),
            'cached': False
        }
    
    def _init_edge_tts(self):
        """初始化Edge TTS（使用VoiceModelService）"""
        self.service_mode = 'edge-tts'
        self.tts_model = self.voice_model.get_model()
    
    def _get_edge_voice(self, character_id: int) -> str:
        """获取Edge TTS音色"""
        # TODO: 根据角色ID选择合适的音色
        # 暂时返回中文女声
        return 'zh-CN-XiaoxiaoNeural'  # 微软Edge TTS的中文女声
    
    def _generate_speech_http(
        self,
        text: str,
        character_id: int,
        voice_id: Optional[str] = None,
        emotion_params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """使用HTTP模式生成语音（使用VoiceModelService）"""
        # 生成缓存键
        cache_key = self._generate_cache_key(text, character_id, voice_id, emotion_params)
        cache_path = self.cache_dir / f"{cache_key}.wav"
        
        # 检查缓存
        if use_cache and cache_path.exists():
            return {
                'audio_url': f'/static/audio/cache/{cache_key}.wav',
                'audio_path': str(cache_path),
                'cached': True,
                'duration': self._get_audio_duration(cache_path)
            }
        
        # 准备情绪参数
        kwargs = {}
        if emotion_params:
            if 'speed' in emotion_params:
                kwargs['speed_ratio'] = max(0.5, min(2.0, emotion_params['speed']))
            if 'volume' in emotion_params:
                kwargs['volume_ratio'] = max(0.1, min(2.0, emotion_params['volume']))
            if 'pitch' in emotion_params:
                kwargs['pitch_ratio'] = max(0.5, min(2.0, emotion_params['pitch']))
        
        # 使用VoiceModelService合成语音
        audio_data = self.voice_model.synthesize_speech(
            text=text,
            voice_id=voice_id,
            **kwargs
        )
        
        if not audio_data:
            raise ValueError("TTS 未返回音频数据")
        
        # 保存到缓存
        cache_path.write_bytes(audio_data)
        return {
            'audio_url': f'/static/audio/cache/{cache_key}.wav',
            'audio_path': str(cache_path),
            'duration': self._get_audio_duration(cache_path),
            'cached': False
        }
    
    def get_character_voice_config(self, character_id: int) -> Dict[str, Any]:
        """获取角色音色配置"""
        if character_id in self.voice_configs:
            return self.voice_configs[character_id]
        
        # 从数据库加载（如果实现了CharacterVoice表）
        # TODO: 实现从数据库加载角色音色配置
        # from database.db_manager import DatabaseManager
        # db_manager = DatabaseManager()
        # character_voice = db_manager.get_character_voice(character_id)
        
        # 默认配置
        default_config = {
            'voice_type': 'preset',
            'preset_voice_id': None,  # 使用默认音色
            'voice_params': {},
        }
        
        self.voice_configs[character_id] = default_config
        return default_config
    
    def _get_default_voice(self, character_id: int) -> str:
        """获取默认音色（根据角色性别等）"""
        # TODO: 从数据库获取角色性别，选择对应音色
        # 暂时返回None，使用模型默认音色
        return None

    def _resolve_preset_voice_id(self, preset_id: Optional[str]) -> Optional[str]:
        """将预设音色 ID（如 female_001）解析为火山引擎音色名"""
        if not preset_id:
            return None
        try:
            from data.preset_voices import get_preset_voice
            voice = get_preset_voice(preset_id)
            if voice and voice.get('voice_id'):
                return voice['voice_id']
        except Exception:
            pass
        return preset_id  # 已是火山引擎音色名则原样返回

    def _generate_cache_key(
        self,
        text: str,
        character_id: int,
        voice_id: Optional[str],
        emotion_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """生成缓存键"""
        key_data = {
            'text': text,
            'character_id': character_id,
            'voice_id': voice_id,
            'emotion_params': emotion_params or {},
            'model': self.tts_model
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长（秒）"""
        try:
            # 使用pydub获取音频时长
            from pydub import AudioSegment
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0  # 转换为秒
        except ImportError:
            logger.warning("pydub未安装，无法获取音频时长")
            return 0.0
        except Exception as e:
            logger.warning(f"获取音频时长失败: {e}", exc_info=True)
            return 0.0

    # 以下方法为了兼容性保留，但功能已禁用
    def list_voices(self, page_index: int = 0, page_size: int = 10) -> Dict[str, Any]:
        """查询音色列表（火山引擎不支持）"""
        return {
            'success': False,
            'message': '火山引擎TTS不支持音色列表查询',
            'voices': [],
            'total_count': 0
        }
    
    def create_voice_from_description(
        self,
        description: str,
        character_id: Optional[int] = None,
        preview_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建自定义音色（火山引擎不支持）"""
        return {
            'success': False,
            'message': '火山引擎TTS不支持Voice Design功能'
        }