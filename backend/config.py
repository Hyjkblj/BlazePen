"""配置文件"""
import os
from dotenv import load_dotenv
from model_config import get_text_llm_model

load_dotenv()

# 可选：应用启动时验证配置（开发环境只警告，生产环境会抛出异常）
# 取消注释以下行以启用配置验证
# from utils.config_validator import validate_config_on_startup
# validate_config_on_startup()

# PostgreSQL配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'noendstory'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

# 路径解析：统一转换为绝对路径，避免依赖当前工作目录。
_backend_dir = os.path.dirname(os.path.abspath(__file__))  # .../backend
_project_root_dir = os.path.dirname(_backend_dir)  # 项目根目录


def _resolve_config_path(env_name: str, default_value: str, relative_base_dir: str) -> str:
    """解析配置路径并统一为绝对路径。"""
    raw_value = os.getenv(env_name, default_value) or default_value
    if os.path.isabs(raw_value):
        return os.path.normpath(raw_value)
    return os.path.normpath(os.path.abspath(os.path.join(relative_base_dir, raw_value)))


# 向量数据库配置
# 默认仍指向“项目根目录/vector_db”，但如果环境变量里写的是相对路径，
# 则统一按 backend 目录解析，避免从不同工作目录启动时读到不同库。
_default_vector_db_path = os.path.join(_project_root_dir, 'vector_db')
VECTOR_DB_PATH = _resolve_config_path('VECTOR_DB_PATH', _default_vector_db_path, _backend_dir)

# Embedding模型配置（用于向量数据库的长时记忆）
# 可选值：
# - 'default': ChromaDB默认模型（all-MiniLM-L6-v2，英文为主）
# - 'text2vec-chinese': 中文优化模型（推荐用于中文游戏）
# - 'm3e-base': 中文embedding模型
# - 'bge-small-zh-v1.5': 百度开源中文embedding模型
# - 'paraphrase-multilingual': 多语言模型（支持中英文）
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text2vec-chinese')

# AI模型配置（可选，当前代码未使用）
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# 国内AI模型配置（替代方案）
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')  # 阿里云百炼 API Key（通义/灵积/DashScope）
# 通义千问模型选择：qwen-turbo（快速，成本低）、qwen-plus（平衡）、qwen-max（最强，成本高）、qwen-flash（极速，成本最低）
DASHSCOPE_MODEL = os.getenv('DASHSCOPE_MODEL', 'qwen-flash')  # 默认使用qwen-flash（极速模型）
ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY', '')  # 智谱AI
BAIDU_API_KEY = os.getenv('BAIDU_API_KEY', '')  # 百度文心一言
BAIDU_SECRET_KEY = os.getenv('BAIDU_SECRET_KEY', '')

# DashScope TTS配置
# 使用最新的VD-Realtime模型（支持Voice Design和实时合成）
DASHSCOPE_TTS_MODEL = os.getenv('DASHSCOPE_TTS_MODEL', 'sambert-zhichu-v1')  # 百炼 TTS：基础模型

# 火山引擎配置
# 注意：从.env读取时去除首尾空格，避免配置格式错误
VOLCENGINE_ARK_API_KEY = os.getenv('VOLCENGINE_ARK_API_KEY', '').strip()  # Bearer Token (ARK API Key)
VOLCENGINE_REGION = os.getenv('VOLCENGINE_REGION', 'cn-beijing')  # 区域，默认：cn-beijing

# 火山引擎 TTS 语音合成配置（双向流式WebSocket API）
# ⚠️ 安全警告：敏感信息必须从环境变量读取，不允许硬编码默认值
# 开发环境：如果未设置，会显示警告但不会阻止启动
# 生产环境：必须设置，否则会抛出异常
_env = os.getenv('ENV', 'dev').lower()

VOLCENGINE_TTS_APP_ID = os.getenv('VOLCENGINE_TTS_APP_ID', '').strip()
VOLCENGINE_TTS_ACCESS_TOKEN = os.getenv('VOLCENGINE_TTS_ACCESS_TOKEN', '').strip()
VOLCENGINE_TTS_SECRET_KEY = os.getenv('VOLCENGINE_TTS_SECRET_KEY', '').strip()

# 验证必需的敏感配置
if _env == 'prod':
    # 生产环境：必须设置，否则抛出异常
    if not VOLCENGINE_TTS_APP_ID:
        raise ValueError(
            "生产环境必须设置 VOLCENGINE_TTS_APP_ID 环境变量。"
            "请参考 .env.example 文件配置。"
        )
    if not VOLCENGINE_TTS_ACCESS_TOKEN:
        raise ValueError(
            "生产环境必须设置 VOLCENGINE_TTS_ACCESS_TOKEN 环境变量。"
            "请参考 .env.example 文件配置。"
        )
    if not VOLCENGINE_TTS_SECRET_KEY:
        raise ValueError(
            "生产环境必须设置 VOLCENGINE_TTS_SECRET_KEY 环境变量。"
            "请参考 .env.example 文件配置。"
        )
else:
    # 开发环境：显示警告但不阻止启动
    # 注意：如果TTS_PROVIDER不是volcengine，则不需要配置火山引擎TTS密钥
    tts_provider = os.getenv('TTS_PROVIDER', 'volcengine').lower()
    
    missing_keys = []
    # 只有当TTS提供商是volcengine时才检查火山引擎TTS配置
    if tts_provider == 'volcengine':
        if not VOLCENGINE_TTS_APP_ID:
            missing_keys.append('VOLCENGINE_TTS_APP_ID')
        if not VOLCENGINE_TTS_ACCESS_TOKEN:
            missing_keys.append('VOLCENGINE_TTS_ACCESS_TOKEN')
        if not VOLCENGINE_TTS_SECRET_KEY:
            missing_keys.append('VOLCENGINE_TTS_SECRET_KEY')
    
    if missing_keys:
        import warnings
        warnings.warn(
            f"开发环境警告：以下TTS配置项未设置，TTS功能将不可用：{', '.join(missing_keys)}。"
            f"请编辑 backend/.env 文件并填写相应配置。"
            f"如果使用其他TTS提供商（如DashScope），请设置 TTS_PROVIDER=dashscope。",
            UserWarning
        )

# TTS模型配置
VOLCENGINE_TTS_MODEL = os.getenv('VOLCENGINE_TTS_MODEL', 'seed-tts-2.0')  # TTS模型：seed-tts-2.0（豆包语音合成模型2.0）
VOLCENGINE_TTS_RESOURCE_ID = os.getenv('VOLCENGINE_TTS_RESOURCE_ID', 'volc.tts.default')  # 使用有权限的资源ID
TTS_PROVIDER = os.getenv('TTS_PROVIDER', 'volcengine')  # 切换回火山引擎检查权限

# WebSocket TTS配置
VOLCENGINE_TTS_WEBSOCKET_URL = os.getenv('VOLCENGINE_TTS_WEBSOCKET_URL', 'wss://openspeech.bytedance.com/api/v3/tts/bidirection')
VOLCENGINE_TTS_USE_WEBSOCKET = os.getenv('VOLCENGINE_TTS_USE_WEBSOCKET', 'false').lower() == 'true'  # 暂时禁用WebSocket模式

# TTS高级功能配置
VOLCENGINE_TTS_ENABLE_TIMESTAMP = os.getenv('VOLCENGINE_TTS_ENABLE_TIMESTAMP', 'false').lower() == 'true'  # 是否启用时间戳
VOLCENGINE_TTS_ENABLE_CACHE = os.getenv('VOLCENGINE_TTS_ENABLE_CACHE', 'true').lower() == 'true'  # 是否启用缓存
VOLCENGINE_TTS_ENABLE_EMOTION = os.getenv('VOLCENGINE_TTS_ENABLE_EMOTION', 'true').lower() == 'true'  # 是否启用情感控制

# 文本生成配置（火山引擎）
VOLCENGINE_TEXT_MODEL = get_text_llm_model()  # 统一模型开关：优先读取 LLM_TEXT_MODEL
VOLCENGINE_TEXT_API_URL = os.getenv('VOLCENGINE_TEXT_API_URL', '')  # 文本生成API端点（可选，默认根据region自动构建）

# 图片生成配置（火山引擎 Seedream）
VOLCENGINE_IMAGE_MODEL = os.getenv('VOLCENGINE_IMAGE_MODEL', 'doubao-seedream-4-0-250828')  # 图片生成模型：doubao-seedream-4-0-250828（默认）或 doubao-seedream-4-5-251128
VOLCENGINE_IMAGE_SIZE = os.getenv('VOLCENGINE_IMAGE_SIZE', '2K')  # 图片尺寸：2K, 4K, 1024x1024等

# 本地模型配置（Ollama）
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen:7b')  # 或 chatglm3:6b

# 游戏配置
GAME_CONFIG = {
    'max_events': 3,  # 中间事件数量
    'total_events': 5,  # 总事件数（开头1 + 中间3 + 结尾1）
}

# 图片保存配置（统一解析为 backend 下的绝对路径）
IMAGE_SAVE_DIR = _resolve_config_path('IMAGE_SAVE_DIR', './images/characters', _backend_dir)  # 角色图片保存目录
SCENE_IMAGE_SAVE_DIR = _resolve_config_path('SCENE_IMAGE_SAVE_DIR', './images/scenes', _backend_dir)  # 场景图片保存目录（大场景）
SMALL_SCENE_IMAGE_SAVE_DIR = _resolve_config_path('SMALL_SCENE_IMAGE_SAVE_DIR', './images/smallscenes', _backend_dir)  # 小场景图片保存目录
COMPOSITE_IMAGE_SAVE_DIR = _resolve_config_path('COMPOSITE_IMAGE_SAVE_DIR', './images/composite', _backend_dir)  # 合成图片保存目录（场景+人物）
IMAGE_SAVE_ENABLED = os.getenv('IMAGE_SAVE_ENABLED', 'true').lower() == 'true'  # 是否启用本地保存
