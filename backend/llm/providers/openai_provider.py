"""OpenAI提供商适配器（使用OpenAI SDK）"""

from typing import List, Dict, Optional, Any
from openai import OpenAI
from openai.types.chat import ChatCompletion

from .base import ProviderAdapter, LLMResponse
from ..exceptions import LLMProviderError, LLMAccountError, LLMNetworkError, LLMTimeoutError


class OpenAIProvider(ProviderAdapter):
    """OpenAI提供商适配器（支持OpenAI官方API和兼容OpenAI格式的API）"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化OpenAI适配器
        
        Args:
            config: 配置字典，包含：
                - api_key: API密钥
                - base_url: API基础URL（可选，默认OpenAI官方）
                - model: 模型名称
        """
        super().__init__(config)
        
        self.base_url = config.get('base_url', 'https://api.openai.com/v1')
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
    
    def call(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """调用OpenAI API
        
        Args:
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数（stream, top_p等）
            
        Returns:
            LLMResponse对象
        """
        try:
            # 构建请求参数
            params = {
                "model": self.model,
                "messages": messages,
            }
            
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            if temperature is not None:
                params["temperature"] = temperature
            
            # 添加其他参数
            params.update(kwargs)
            
            # 调用API
            response: ChatCompletion = self.client.chat.completions.create(**params)
            
            # 解析响应
            choice = response.choices[0]
            message = choice.message
            
            return LLMResponse(
                text=message.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                } if response.usage else None,
                finish_reason=choice.finish_reason,
                raw_response=response
            )
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # 根据错误类型抛出相应的异常
            if "401" in error_msg or "unauthorized" in error_msg.lower() or "invalid_api_key" in error_msg.lower():
                raise LLMAccountError(f"OpenAI API密钥无效: {error_msg}")
            elif "429" in error_msg or "rate_limit" in error_msg.lower():
                raise LLMProviderError(f"OpenAI API请求频率限制: {error_msg}")
            elif "timeout" in error_msg.lower() or "Timeout" in error_type:
                raise LLMTimeoutError(f"OpenAI API请求超时: {error_msg}")
            elif "connection" in error_msg.lower() or "network" in error_msg.lower():
                raise LLMNetworkError(f"OpenAI API网络错误: {error_msg}")
            else:
                raise LLMProviderError(f"OpenAI API调用失败: {error_msg}")
