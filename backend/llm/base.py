"""LLM服务基类"""

from typing import Optional, List, Dict, Any
import time
from .config import LLMConfig
from .exceptions import LLMException, LLMProviderError
from .providers import (
    ProviderAdapter,
    OpenAIProvider,
    VolcEngineProvider,
    DashScopeProvider,
    LLMResponse
)


class LLMService:
    """通用LLM服务（统一接口，支持多种提供商）"""
    
    def __init__(self, provider: Optional[str] = None, config: Optional[LLMConfig] = None):
        """初始化LLM服务
        
        Args:
            provider: 提供商名称（'openai', 'volcengine', 'dashscope'），如果为None则自动检测
            config: LLMConfig配置对象，如果为None则使用默认配置
        """
        self.config = config or LLMConfig()
        
        # 确定使用的提供商
        if provider is None or provider == 'auto':
            provider = self.config.auto_detect_provider()
            if provider is None:
                raise LLMException("未找到可用的LLM提供商，请检查配置")
        
        self.provider_name = provider
        
        # 创建提供商适配器
        self.adapter = self._create_adapter(provider)
        
        print(f"[LLM服务] 已初始化 - 提供商: {provider}, 模型: {self.adapter.model}")
    
    def _create_adapter(self, provider: str) -> ProviderAdapter:
        """创建提供商适配器
        
        Args:
            provider: 提供商名称
            
        Returns:
            ProviderAdapter实例
            
        Raises:
            LLMException: 如果提供商不支持或配置错误
        """
        try:
            provider_config = self.config.get_provider_config(provider)
        except Exception as e:
            raise LLMException(f"获取提供商配置失败: {e}")
        
        # 根据提供商类型创建适配器
        if provider == 'openai':
            return OpenAIProvider(provider_config)
        elif provider == 'volcengine':
            return VolcEngineProvider(provider_config)
        elif provider == 'dashscope':
            return DashScopeProvider(provider_config)
        else:
            raise LLMException(f"不支持的提供商: {provider}")
    
    def call(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """调用LLM API（OpenAI SDK兼容格式）
        
        Args:
            messages: 消息列表，格式：[{"role": "user", "content": "..."}]
            max_tokens: 最大token数
            temperature: 温度参数（0-2）
            **kwargs: 其他参数
            
        Returns:
            LLMResponse对象
        """
        return self.adapter.call(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
    
    def call_with_retry(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
    ) -> LLMResponse:
        """带重试机制的LLM调用
        
        Args:
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度参数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            **kwargs: 其他参数
            
        Returns:
            LLMResponse对象
            
        Raises:
            LLMException: 如果所有重试都失败
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return self.call(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            except LLMException as e:
                last_exception = e
                
                # 账户错误不重试
                from .exceptions import LLMAccountError
                if isinstance(e, LLMAccountError):
                    raise
                
                # 如果是最后一次尝试，直接抛出异常
                if attempt == max_retries - 1:
                    break
                
                # 等待后重试（指数退避）
                wait_time = retry_delay * (attempt + 1)
                print(f"[LLM服务] 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                print(f"[LLM服务] {wait_time:.1f}秒后重试...")
                time.sleep(wait_time)
        
        # 所有重试都失败
        raise LLMProviderError(f"LLM调用失败，已重试{max_retries}次: {last_exception}")
    
    def chat_completion(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        use_retry: bool = True,
        **kwargs
    ) -> str:
        """便捷方法：单轮对话（兼容旧代码）
        
        Args:
            prompt: 用户提示词
            max_tokens: 最大token数
            temperature: 温度参数
            system_message: 可选的系统消息
            use_retry: 是否使用重试机制
            **kwargs: 其他参数
            
        Returns:
            生成的文本字符串
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        if use_retry:
            response = self.call_with_retry(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
        else:
            response = self.call(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
        
        return response.text
    
    def get_provider(self) -> str:
        """获取当前使用的提供商名称"""
        return self.provider_name
    
    def get_model(self) -> str:
        """获取当前使用的模型名称"""
        return self.adapter.model
