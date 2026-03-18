"""文本大模型服务（统一接口，支持多提供商）"""
from typing import Optional, List, Dict, Any
from llm import LLMService, LLMException
from llm.config import LLMConfig


class TextModelService:
    """文本大模型服务（用于文本生成：对话、剧情、选项等）
    
    职责：
    - 文本生成（对话、剧情背景、玩家选项）
    - 支持多提供商（volcengine、dashscope、openai）
    - 统一的接口和错误处理
    """
    
    def __init__(self, provider: Optional[str] = None, config: Optional[LLMConfig] = None):
        """初始化文本大模型服务
        
        Args:
            provider: 提供商名称（'volcengine', 'dashscope', 'openai', 'auto'），如果为None则自动检测
            config: LLMConfig配置对象，如果为None则使用默认配置
        """
        self.llm_service = LLMService(provider=provider or 'auto', config=config)
        self.enabled = self.llm_service is not None
        if self.enabled:
            print(f"[文本大模型] 已启用 - 提供商: {self.llm_service.get_provider()}, 模型: {self.llm_service.get_model()}")
    
    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        use_retry: bool = True,
        **kwargs
    ) -> Optional[str]:
        """生成文本（统一接口）
        
        Args:
            prompt: 提示词
            max_tokens: 最大token数
            temperature: 温度参数（0-2）
            system_message: 可选的系统消息
            use_retry: 是否使用重试机制
            **kwargs: 其他参数
            
        Returns:
            生成的文本，如果失败返回None
        """
        if not self.enabled:
            return None
        
        try:
            if use_retry:
                response = self.llm_service.call_with_retry(
                    messages=self._build_messages(prompt, system_message),
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            else:
                response = self.llm_service.call(
                    messages=self._build_messages(prompt, system_message),
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            return response.text
        except LLMException as e:
            print(f"[文本大模型] 生成失败: {e}")
            return None
    
    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 200,
        temperature: float = 0.7,
        use_retry: bool = True,
        **kwargs
    ) -> Optional[str]:
        """使用消息列表生成文本
        
        Args:
            messages: 消息列表，格式：[{"role": "user", "content": "..."}]
            max_tokens: 最大token数
            temperature: 温度参数
            use_retry: 是否使用重试机制
            **kwargs: 其他参数
            
        Returns:
            生成的文本，如果失败返回None
        """
        if not self.enabled:
            return None
        
        try:
            if use_retry:
                response = self.llm_service.call_with_retry(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            else:
                response = self.llm_service.call(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            return response.text
        except LLMException as e:
            print(f"[文本大模型] 生成失败: {e}")
            return None
    
    def _build_messages(self, prompt: str, system_message: Optional[str] = None) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        return messages
    
    def get_provider(self) -> str:
        """获取当前使用的提供商名称"""
        return self.llm_service.get_provider() if self.enabled else "none"
    
    def get_model(self) -> str:
        """获取当前使用的模型名称"""
        return self.llm_service.get_model() if self.enabled else "none"
