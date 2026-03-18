"""配置验证工具"""
import os
from typing import List, Tuple, Dict
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigValidator:
    """配置验证器"""
    
    # 必需配置项（生产环境）
    REQUIRED_PROD_CONFIGS = {
        'VOLCENGINE_TTS_APP_ID': '火山引擎TTS应用ID',
        'VOLCENGINE_TTS_ACCESS_TOKEN': '火山引擎TTS访问令牌',
        'VOLCENGINE_TTS_SECRET_KEY': '火山引擎TTS密钥',
        'ALLOWED_ORIGINS': 'CORS允许的来源（生产环境必需）',
    }
    
    # 推荐配置项
    RECOMMENDED_CONFIGS = {
        'VOLCENGINE_ARK_API_KEY': '火山引擎ARK API Key（用于文本和图片生成）',
        'DASHSCOPE_API_KEY': '阿里云DashScope API Key（可选）',
    }
    
    @classmethod
    def validate(cls, env: str = None) -> Tuple[bool, List[str], List[str]]:
        """验证配置
        
        Args:
            env: 环境名称（dev/prod），如果为None则从环境变量读取
            
        Returns:
            (is_valid, errors, warnings): 
            - is_valid: 是否通过验证（生产环境必须全部通过）
            - errors: 错误列表（生产环境必需但未设置的配置）
            - warnings: 警告列表（推荐但未设置的配置）
        """
        if env is None:
            env = os.getenv('ENV', 'dev').lower()
        
        errors = []
        warnings = []
        
        # 检查必需配置（生产环境）
        if env == 'prod':
            for key, description in cls.REQUIRED_PROD_CONFIGS.items():
                value = os.getenv(key, '').strip()
                if not value:
                    errors.append(f"{key} ({description}) 未设置")
        
        # 检查推荐配置
        for key, description in cls.RECOMMENDED_CONFIGS.items():
            value = os.getenv(key, '').strip()
            if not value:
                warnings.append(f"{key} ({description}) 未设置，相关功能可能不可用")
        
        # 检查至少配置了一个AI模型提供商
        ai_providers = [
            'VOLCENGINE_ARK_API_KEY',
            'DASHSCOPE_API_KEY',
            'OPENAI_API_KEY',
            'ZHIPU_API_KEY',
            'BAIDU_API_KEY'
        ]
        has_ai_provider = any(os.getenv(key, '').strip() for key in ai_providers)
        if not has_ai_provider:
            warnings.append("未配置任何AI模型提供商，文本生成功能将不可用")
        
        # 检查TTS提供商配置
        tts_provider = os.getenv('TTS_PROVIDER', 'volcengine')
        if tts_provider == 'volcengine':
            tts_keys = ['VOLCENGINE_TTS_APP_ID', 'VOLCENGINE_TTS_ACCESS_TOKEN', 'VOLCENGINE_TTS_SECRET_KEY']
            has_tts_config = all(os.getenv(key, '').strip() for key in tts_keys)
            if not has_tts_config:
                if env == 'prod':
                    errors.append("TTS提供商设置为volcengine，但未配置完整的火山引擎TTS密钥")
                else:
                    warnings.append("TTS提供商设置为volcengine，但未配置完整的火山引擎TTS密钥，TTS功能将不可用")
        
        is_valid = len(errors) == 0
        
        return is_valid, errors, warnings
    
    @classmethod
    def print_validation_report(cls, env: str = None):
        """打印验证报告"""
        is_valid, errors, warnings = cls.validate(env)
        
        if env is None:
            env = os.getenv('ENV', 'dev').lower()
        
        logger.info(f"配置验证报告（环境: {env}）")
        logger.info("=" * 60)
        
        if errors:
            logger.error(f"发现 {len(errors)} 个错误（生产环境必须修复）：")
            for error in errors:
                logger.error(f"  ❌ {error}")
        
        if warnings:
            logger.warning(f"发现 {len(warnings)} 个警告（建议修复）：")
            for warning in warnings:
                logger.warning(f"  ⚠️  {warning}")
        
        if not errors and not warnings:
            logger.info("✅ 配置验证通过，所有必需和推荐配置都已设置")
        elif not errors:
            logger.info("✅ 配置验证通过（存在警告但不影响基本功能）")
        else:
            logger.error("❌ 配置验证失败，请修复上述错误后重试")
        
        logger.info("=" * 60)
        
        return is_valid


def validate_config_on_startup():
    """应用启动时验证配置"""
    env = os.getenv('ENV', 'dev').lower()
    is_valid, errors, warnings = ConfigValidator.validate(env)
    
    if env == 'prod' and not is_valid:
        # 生产环境：有错误则抛出异常
        error_msg = "生产环境配置验证失败：\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)
    else:
        # 开发/测试环境：只打印警告
        ConfigValidator.print_validation_report(env)
