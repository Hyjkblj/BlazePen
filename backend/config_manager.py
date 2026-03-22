"""配置管理器（配置对象化）"""
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from model_config import get_text_llm_model
from api.cors_config import build_allowed_origins

load_dotenv()

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT_DIR = os.path.dirname(_BACKEND_DIR)


def _resolve_config_path(env_name: str, default_value: str, relative_base_dir: str) -> str:
    """解析配置路径并统一为绝对路径。"""
    raw_value = os.getenv(env_name, default_value) or default_value
    if os.path.isabs(raw_value):
        return os.path.normpath(raw_value)
    return os.path.normpath(os.path.abspath(os.path.join(relative_base_dir, raw_value)))


class Config:
    """应用配置类（支持多环境）"""
    
    def __init__(self, env: Optional[str] = None):
        """初始化配置
        
        Args:
            env: 环境名称（dev/prod/test），如果为None则从环境变量读取
        """
        self.env = env or os.getenv('ENV', 'dev')
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        # PostgreSQL配置
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'noendstory'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        
        # 向量数据库配置
        default_vector_db_path = os.path.join(_PROJECT_ROOT_DIR, 'vector_db')
        self.vector_db_path = _resolve_config_path('VECTOR_DB_PATH', default_vector_db_path, _BACKEND_DIR)
        
        # Embedding模型配置
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text2vec-chinese')
        
        # OpenAI配置
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        
        # DashScope配置
        self.dashscope_api_key = os.getenv('DASHSCOPE_API_KEY', '')
        self.dashscope_model = os.getenv('DASHSCOPE_MODEL', 'qwen-flash')
        self.dashscope_tts_model = os.getenv('DASHSCOPE_TTS_MODEL', 'sambert-zhichu-v1')
        
        # 火山引擎配置
        self.volcengine_ark_api_key = os.getenv('VOLCENGINE_ARK_API_KEY', '').strip()
        self.volcengine_region = os.getenv('VOLCENGINE_REGION', 'cn-beijing')
        self.volcengine_text_model = get_text_llm_model()
        self.volcengine_text_api_url = os.getenv('VOLCENGINE_TEXT_API_URL', '')
        self.volcengine_image_model = os.getenv('VOLCENGINE_IMAGE_MODEL', 'doubao-seedream-4-0-250828')
        self.volcengine_image_size = os.getenv('VOLCENGINE_IMAGE_SIZE', '2K')
        
        # 火山引擎TTS配置（敏感信息，必须从环境变量读取）
        self.volcengine_tts_app_id = os.getenv('VOLCENGINE_TTS_APP_ID', '')
        self.volcengine_tts_access_token = os.getenv('VOLCENGINE_TTS_ACCESS_TOKEN', '')
        self.volcengine_tts_secret_key = os.getenv('VOLCENGINE_TTS_SECRET_KEY', '')
        self.volcengine_tts_model = os.getenv('VOLCENGINE_TTS_MODEL', 'seed-tts-2.0')
        self.volcengine_tts_resource_id = os.getenv('VOLCENGINE_TTS_RESOURCE_ID', 'volc.tts.default')
        self.volcengine_tts_websocket_url = os.getenv('VOLCENGINE_TTS_WEBSOCKET_URL', 'wss://openspeech.bytedance.com/api/v3/tts/bidirection')
        self.volcengine_tts_use_websocket = os.getenv('VOLCENGINE_TTS_USE_WEBSOCKET', 'false').lower() == 'true'
        self.volcengine_tts_enable_timestamp = os.getenv('VOLCENGINE_TTS_ENABLE_TIMESTAMP', 'false').lower() == 'true'
        self.volcengine_tts_enable_cache = os.getenv('VOLCENGINE_TTS_ENABLE_CACHE', 'true').lower() == 'true'
        self.volcengine_tts_enable_emotion = os.getenv('VOLCENGINE_TTS_ENABLE_EMOTION', 'true').lower() == 'true'
        
        # TTS提供商配置
        self.tts_provider = os.getenv('TTS_PROVIDER', 'volcengine')
        
        # 其他AI模型配置
        self.zhipu_api_key = os.getenv('ZHIPU_API_KEY', '')
        self.baidu_api_key = os.getenv('BAIDU_API_KEY', '')
        self.baidu_secret_key = os.getenv('BAIDU_SECRET_KEY', '')
        
        # Ollama配置
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'qwen:7b')
        
        # 游戏配置
        self.game_config = {
            'max_events': int(os.getenv('GAME_MAX_EVENTS', '3')),
            'total_events': int(os.getenv('GAME_TOTAL_EVENTS', '5'))
        }
        
        # 图片保存配置
        self.image_save_dir = _resolve_config_path('IMAGE_SAVE_DIR', './images/characters', _BACKEND_DIR)
        self.scene_image_save_dir = _resolve_config_path('SCENE_IMAGE_SAVE_DIR', './images/scenes', _BACKEND_DIR)
        self.small_scene_image_save_dir = _resolve_config_path('SMALL_SCENE_IMAGE_SAVE_DIR', './images/smallscenes', _BACKEND_DIR)
        self.composite_image_save_dir = _resolve_config_path('COMPOSITE_IMAGE_SAVE_DIR', './images/composite', _BACKEND_DIR)
        self.image_save_enabled = os.getenv('IMAGE_SAVE_ENABLED', 'true').lower() == 'true'
        
        # CORS配置（单一事实源：api.cors_config）
        self.story_allowed_origins = build_allowed_origins(
            service_scope='story',
            env_name=self.env,
        )
        self.training_allowed_origins = build_allowed_origins(
            service_scope='training',
            env_name=self.env,
        )
        # 向后兼容：旧代码读取 allowed_origins 时，返回 story 入口 allowlist。
        self.allowed_origins = list(self.story_allowed_origins)
    
    def get_absolute_path(self, relative_path: str) -> str:
        """将相对路径转换为绝对路径
        
        Args:
            relative_path: 相对路径
            
        Returns:
            绝对路径
        """
        if os.path.isabs(relative_path):
            return os.path.normpath(relative_path)
        return os.path.normpath(os.path.abspath(os.path.join(_BACKEND_DIR, relative_path)))


# 默认配置实例（向后兼容）
_default_config = Config()

# 向后兼容：导出常用配置项（保持现有代码可用）
DB_CONFIG = _default_config.db_config
VECTOR_DB_PATH = _default_config.vector_db_path
EMBEDDING_MODEL = _default_config.embedding_model
OPENAI_API_KEY = _default_config.openai_api_key
DASHSCOPE_API_KEY = _default_config.dashscope_api_key
DASHSCOPE_MODEL = _default_config.dashscope_model
DASHSCOPE_TTS_MODEL = _default_config.dashscope_tts_model
VOLCENGINE_ARK_API_KEY = _default_config.volcengine_ark_api_key
VOLCENGINE_REGION = _default_config.volcengine_region
VOLCENGINE_TEXT_MODEL = _default_config.volcengine_text_model
VOLCENGINE_TEXT_API_URL = _default_config.volcengine_text_api_url
VOLCENGINE_IMAGE_MODEL = _default_config.volcengine_image_model
VOLCENGINE_IMAGE_SIZE = _default_config.volcengine_image_size
VOLCENGINE_TTS_APP_ID = _default_config.volcengine_tts_app_id
VOLCENGINE_TTS_ACCESS_TOKEN = _default_config.volcengine_tts_access_token
VOLCENGINE_TTS_SECRET_KEY = _default_config.volcengine_tts_secret_key
VOLCENGINE_TTS_MODEL = _default_config.volcengine_tts_model
VOLCENGINE_TTS_RESOURCE_ID = _default_config.volcengine_tts_resource_id
VOLCENGINE_TTS_WEBSOCKET_URL = _default_config.volcengine_tts_websocket_url
VOLCENGINE_TTS_USE_WEBSOCKET = _default_config.volcengine_tts_use_websocket
VOLCENGINE_TTS_ENABLE_TIMESTAMP = _default_config.volcengine_tts_enable_timestamp
VOLCENGINE_TTS_ENABLE_CACHE = _default_config.volcengine_tts_enable_cache
VOLCENGINE_TTS_ENABLE_EMOTION = _default_config.volcengine_tts_enable_emotion
TTS_PROVIDER = _default_config.tts_provider
ZHIPU_API_KEY = _default_config.zhipu_api_key
BAIDU_API_KEY = _default_config.baidu_api_key
BAIDU_SECRET_KEY = _default_config.baidu_secret_key
OLLAMA_BASE_URL = _default_config.ollama_base_url
OLLAMA_MODEL = _default_config.ollama_model
GAME_CONFIG = _default_config.game_config
IMAGE_SAVE_DIR = _default_config.image_save_dir
SCENE_IMAGE_SAVE_DIR = _default_config.scene_image_save_dir
SMALL_SCENE_IMAGE_SAVE_DIR = _default_config.small_scene_image_save_dir
COMPOSITE_IMAGE_SAVE_DIR = _default_config.composite_image_save_dir
IMAGE_SAVE_ENABLED = _default_config.image_save_enabled
ALLOWED_ORIGINS = _default_config.allowed_origins
STORY_ALLOWED_ORIGINS = _default_config.story_allowed_origins
TRAINING_ALLOWED_ORIGINS = _default_config.training_allowed_origins
