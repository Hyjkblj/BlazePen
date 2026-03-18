"""LLM框架异常定义"""


class LLMException(Exception):
    """LLM调用异常基类"""
    pass


class LLMProviderError(LLMException):
    """提供商错误（API调用失败、模型不可用等）"""
    pass


class LLMAccountError(LLMException):
    """账户错误（API密钥无效、余额不足、权限不足等）"""
    pass


class LLMNetworkError(LLMException):
    """网络错误（连接失败、超时等）"""
    pass


class LLMTimeoutError(LLMException):
    """超时错误"""
    pass


class LLMConfigError(LLMException):
    """配置错误"""
    pass
