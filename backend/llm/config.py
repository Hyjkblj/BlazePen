"""LLM配置管理"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from .exceptions import LLMConfigError
from model_config import get_text_llm_model

load_dotenv()


class LLMConfig:
    """LLM配置管理器"""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """初始化配置
        
        Args:
            config_dict: 可选的配置字典，用于覆盖环境变量
        """
        self.config = config_dict or {}
        self._load_from_env()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        # OpenAI配置
        self.config.setdefault('openai', {
            'api_key': os.getenv('OPENAI_API_KEY', ''),
            'base_url': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
            'model': os.getenv('OPENAI_MODEL', 'gpt-4o'),
        })
        
        # 火山引擎配置
        self.config.setdefault('volcengine', {
            'api_key': os.getenv('VOLCENGINE_ARK_API_KEY', '').strip(),
            'region': os.getenv('VOLCENGINE_REGION', 'cn-beijing'),
            'base_url': os.getenv('VOLCENGINE_TEXT_API_URL', ''),
            'model': get_text_llm_model(),
        })
        
        # 通义千问配置
        self.config.setdefault('dashscope', {
            'api_key': os.getenv('DASHSCOPE_API_KEY', ''),
            'model': os.getenv('DASHSCOPE_MODEL', 'qwen-flash'),
        })
        
        # 默认提供商（优先级顺序）
        self.config.setdefault('default_provider', os.getenv('LLM_DEFAULT_PROVIDER', 'auto'))
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """获取指定提供商的配置
        
        Args:
            provider: 提供商名称（'openai', 'volcengine', 'dashscope'）
            
        Returns:
            提供商配置字典
            
        Raises:
            LLMConfigError: 如果提供商配置不存在
        """
        if provider not in self.config:
            raise LLMConfigError(f"提供商 '{provider}' 的配置不存在")
        return self.config[provider]
    
    def get_default_provider(self) -> str:
        """获取默认提供商
        
        Returns:
            提供商名称，如果为'auto'则自动检测
        """
        return self.config.get('default_provider', 'auto')
    
    def is_provider_available(self, provider: str) -> bool:
        """检查提供商是否可用（有API密钥）
        
        Args:
            provider: 提供商名称
            
        Returns:
            如果提供商可用返回True，否则返回False
        """
        try:
            config = self.get_provider_config(provider)
            api_key = config.get('api_key', '').strip()
            return bool(api_key)
        except LLMConfigError:
            return False
    
    def auto_detect_provider(self) -> Optional[str]:
        """自动检测可用的提供商（按优先级）
        
        Returns:
            可用的提供商名称，如果没有可用则返回None
        """
        # 优先级顺序
        providers = ['volcengine', 'dashscope', 'openai']
        
        for provider in providers:
            if self.is_provider_available(provider):
                return provider
        
        return None
    
    def update_config(self, provider: str, config: Dict[str, Any]):
        """更新提供商配置
        
        Args:
            provider: 提供商名称
            config: 配置字典
        """
        if provider not in self.config:
            self.config[provider] = {}
        self.config[provider].update(config)
