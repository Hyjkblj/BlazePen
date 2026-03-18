"""阿里云百炼（DashScope）提供商适配器"""

from typing import List, Dict, Optional, Any
import requests

from .base import ProviderAdapter, LLMResponse
from ..exceptions import LLMProviderError, LLMAccountError, LLMNetworkError, LLMTimeoutError


class DashScopeProvider(ProviderAdapter):
    """阿里云百炼（DashScope）提供商适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化DashScope适配器
        
        Args:
            config: 配置字典，包含：
                - api_key: DashScope API Key
                - model: 模型名称（qwen-turbo, qwen-plus, qwen-max, qwen-flash等）
                - base_url: API端点（可选，默认使用官方端点）
        """
        super().__init__(config)
        
        # DashScope API端点
        self.api_url = config.get('base_url', 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation')
    
    def call(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """调用DashScope API
        
        Args:
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            LLMResponse对象
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建请求体（DashScope格式）
            payload = {
                "model": self.model,
                "input": {
                    "messages": messages
                },
                "parameters": {}
            }
            
            # 添加参数
            if max_tokens is not None:
                payload["parameters"]["max_tokens"] = max_tokens
            if temperature is not None:
                payload["parameters"]["temperature"] = temperature
            
            # 添加其他参数
            if kwargs:
                payload["parameters"].update(kwargs)
            
            # 调用API
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            # 检查HTTP状态码
            if response.status_code == 200:
                result = response.json()
                
                # 解析DashScope响应格式
                if result.get('status_code') == 200:
                    output = result.get('output', {})
                    choices = output.get('choices', [])
                    
                    if choices and len(choices) > 0:
                        choice = choices[0]
                        message = choice.get('message', {})
                        content = message.get('content', '')
                        
                        return LLMResponse(
                            text=content.strip() if content else "",
                            model=self.model,
                            usage=result.get('usage'),
                            finish_reason=choice.get('finish_reason'),
                            raw_response=result
                        )
                    else:
                        raise LLMProviderError(f"DashScope API响应中没有choices: {result}")
                else:
                    # DashScope错误响应
                    error_code = result.get('code', 'unknown')
                    error_msg = result.get('message', '未知错误')
                    
                    if error_code in ['InvalidApiKey', 'Forbidden']:
                        raise LLMAccountError(f"DashScope API密钥无效: {error_msg}")
                    elif error_code == 'Throttling':
                        raise LLMProviderError(f"DashScope API请求频率限制: {error_msg}")
                    else:
                        raise LLMProviderError(f"DashScope API错误 ({error_code}): {error_msg}")
            else:
                error_msg = response.text
                status_code = response.status_code
                
                # 根据状态码判断错误类型
                if status_code == 401:
                    raise LLMAccountError(f"DashScope API密钥无效: {error_msg}")
                elif status_code == 429:
                    raise LLMProviderError(f"DashScope API请求频率限制: {error_msg}")
                elif status_code >= 500:
                    raise LLMProviderError(f"DashScope API服务器错误 ({status_code}): {error_msg}")
                else:
                    raise LLMProviderError(f"DashScope API调用失败 ({status_code}): {error_msg}")
                    
        except requests.exceptions.Timeout:
            raise LLMTimeoutError("DashScope API请求超时")
        except requests.exceptions.ConnectionError as e:
            raise LLMNetworkError(f"DashScope API网络连接错误: {e}")
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"DashScope API调用异常: {e}")