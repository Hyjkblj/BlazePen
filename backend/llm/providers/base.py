"""LLM提供商适配器基类"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM响应对象（统一格式）"""
    text: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


class ProviderAdapter(ABC):
    """LLM提供商适配器基类
    
    所有提供商适配器都应该继承此类，实现OpenAI SDK兼容的接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化适配器
        
        Args:
            config: 提供商配置字典
        """
        self.config = config
        self.api_key = config.get('api_key', '').strip()
        self.model = config.get('model', '')
        
        if not self.api_key:
            raise ValueError(f"{self.__class__.__name__}: API密钥未配置")
        if not self.model:
            raise ValueError(f"{self.__class__.__name__}: 模型名称未配置")
    
    @abstractmethod
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
            
        Raises:
            LLMException: 调用失败时抛出异常
        """
        pass
    
    def chat_completion(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """便捷方法：单轮对话（兼容旧代码）
        
        Args:
            prompt: 用户提示词
            max_tokens: 最大token数
            temperature: 温度参数
            system_message: 可选的系统消息
            **kwargs: 其他参数
            
        Returns:
            LLMResponse对象
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        return self.call(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
