"""火山引擎提供商适配器（兼容OpenAI SDK格式）"""

from typing import List, Dict, Optional, Any
import json
import requests

from .base import ProviderAdapter, LLMResponse
from ..exceptions import LLMProviderError, LLMAccountError, LLMNetworkError, LLMTimeoutError


class VolcEngineProvider(ProviderAdapter):
    """火山引擎提供商适配器（兼容OpenAI格式）"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化火山引擎适配器
        
        Args:
            config: 配置字典，包含：
                - api_key: Bearer Token (ARK API Key)
                - region: 区域（cn-beijing等）
                - base_url: API端点（可选，默认根据region构建）
                - model: 模型名称
        """
        super().__init__(config)
        
        self.region = config.get('region', 'cn-beijing')
        
        # 构建API端点
        if config.get('base_url'):
            self.api_url = config['base_url']
        else:
            # 根据region自动构建
            region_map = {
                'cn-beijing': 'ark.cn-beijing.volces.com',
                'cn-north-1': 'ark.cn-beijing.volces.com',
            }
            host = region_map.get(self.region, 'ark.cn-beijing.volces.com')
            self.api_url = f"https://{host}/api/v3/chat/completions"
    
    def call(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """调用火山引擎API（兼容OpenAI格式）
        
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
            
            # 构建请求体（兼容OpenAI格式）
            payload = {
                "model": self.model,
                "messages": messages,
            }
            
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            if temperature is not None:
                payload["temperature"] = temperature
            
            # 添加其他参数
            payload.update(kwargs)
            
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
                
                # 解析响应（兼容OpenAI格式）
                if 'choices' in result and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    message = choice.get('message', {})
                    content = message.get('content', '')
                    
                    return LLMResponse(
                        text=content.strip() if content else "",
                        model=result.get('model', self.model),
                        usage=result.get('usage'),
                        finish_reason=choice.get('finish_reason'),
                        raw_response=result
                    )
                else:
                    raise LLMProviderError(f"火山引擎API响应格式错误: {result}")
            else:
                error_msg = response.text
                status_code = response.status_code
                error_code = ""
                error_type = ""
                error_detail = error_msg

                # Parse structured error payload if available.
                try:
                    error_json = response.json()
                    if isinstance(error_json, dict) and isinstance(error_json.get("error"), dict):
                        err = error_json["error"]
                        error_code = str(err.get("code", "")).strip()
                        error_type = str(err.get("type", "")).strip()
                        if err.get("message"):
                            error_detail = str(err["message"])
                except (ValueError, json.JSONDecodeError, TypeError):
                    pass

                error_lower = error_msg.lower()
                code_lower = error_code.lower()
                type_lower = error_type.lower()

                # 根据状态码判断错误类型
                if status_code == 401:
                    raise LLMAccountError(f"火山引擎API密钥无效: {error_msg}")
                elif status_code == 403:
                    raise LLMAccountError(f"火山引擎API无权限访问当前模型: {error_msg}")
                elif status_code == 429:
                    # Account/model quota or safety-limit pause: do not retry.
                    if (
                        code_lower == "setlimitexceeded"
                        or "setlimitexceeded" in error_lower
                        or "safe experience mode" in error_lower
                        or "has reached the set inference limit" in error_lower
                        or type_lower == "toomanyrequests"
                    ):
                        raise LLMAccountError(f"火山引擎模型调用受限（账号额度/安全模式）: {error_detail}")
                    raise LLMProviderError(f"火山引擎API请求频率限制: {error_msg}")
                elif status_code >= 500:
                    raise LLMProviderError(f"火山引擎API服务器错误 ({status_code}): {error_msg}")
                else:
                    raise LLMProviderError(f"火山引擎API调用失败 ({status_code}): {error_msg}")
                    
        except requests.exceptions.Timeout:
            raise LLMTimeoutError("火山引擎API请求超时")
        except requests.exceptions.ConnectionError as e:
            raise LLMNetworkError(f"火山引擎API网络连接错误: {e}")
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"火山引擎API调用异常: {e}")
