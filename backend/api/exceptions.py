"""API异常定义"""
from typing import Optional, Dict, Any


class ServiceException(Exception):
    """服务层异常基类"""
    
    def __init__(
        self,
        message: str,
        code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化异常
        
        Args:
            message: 错误消息
            code: HTTP状态码
            details: 详细信息字典
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ImageGenerationException(ServiceException):
    """图片生成异常"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=500, details=details)


class ImageProcessingException(ServiceException):
    """图片处理异常"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=500, details=details)


class CharacterNotFoundException(ServiceException):
    """角色不存在异常"""
    def __init__(self, character_id: int):
        super().__init__(
            f"角色不存在: {character_id}",
            code=404,
            details={"character_id": character_id}
        )


class GameSessionNotFoundException(ServiceException):
    """游戏会话不存在异常"""
    def __init__(self, thread_id: str):
        super().__init__(
            f"游戏会话不存在: {thread_id}",
            code=404,
            details={"thread_id": thread_id}
        )


class LLMServiceException(ServiceException):
    """LLM服务异常"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=503, details=details)


class TTSServiceException(ServiceException):
    """TTS服务异常"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=503, details=details)


class ConfigurationException(ServiceException):
    """配置异常"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=500, details=details)
