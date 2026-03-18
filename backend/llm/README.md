# LLM框架使用指南

## 概述

这是一个通用的LLM调用框架，使用OpenAI SDK兼容格式，支持多种大模型提供商。

## 架构设计

```
backend/llm/
├── __init__.py          # 框架入口
├── base.py              # LLMService核心服务
├── config.py            # 配置管理
├── exceptions.py        # 异常定义
└── providers/          # 提供商适配器
    ├── base.py         # ProviderAdapter基类
    ├── openai_provider.py      # OpenAI适配器
    ├── volcengine_provider.py  # 火山引擎适配器
    └── dashscope_provider.py   # 通义千问适配器
```

## 特性

✅ **OpenAI SDK兼容格式**：所有提供商都使用统一的OpenAI格式接口  
✅ **多提供商支持**：支持OpenAI、火山引擎、通义千问，易于扩展  
✅ **自动检测**：自动检测可用的提供商  
✅ **统一异常处理**：统一的错误处理和重试机制  
✅ **配置灵活**：支持环境变量和配置字典  

## 快速开始

### 1. 基本使用

```python
from llm import LLMService

# 自动检测可用的提供商
llm = LLMService()

# 调用LLM
response = llm.chat_completion(
    prompt="你好，请介绍一下自己",
    max_tokens=200,
    temperature=0.7
)

print(response)  # 输出生成的文本
```

### 2. 指定提供商

```python
from llm import LLMService

# 使用OpenAI
llm = LLMService(provider='openai')

# 使用火山引擎
llm = LLMService(provider='volcengine')

# 使用通义千问
llm = LLMService(provider='dashscope')
```

### 3. 使用OpenAI SDK格式（多轮对话）

```python
from llm import LLMService

llm = LLMService()

messages = [
    {"role": "system", "content": "你是一个友好的助手"},
    {"role": "user", "content": "你好"}
]

response = llm.call(messages=messages, max_tokens=200)

print(response.text)  # 生成的文本
print(response.model)  # 使用的模型
print(response.usage)  # Token使用情况
```

### 4. 带重试的调用

```python
from llm import LLMService

llm = LLMService()

# 自动重试（默认3次）
response = llm.call_with_retry(
    messages=[{"role": "user", "content": "你好"}],
    max_tokens=200,
    max_retries=3,
    retry_delay=1.0
)
```

### 5. 自定义配置

```python
from llm import LLMService, LLMConfig

# 创建自定义配置
config = LLMConfig({
    'openai': {
        'api_key': 'your-key',
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4o'
    }
})

llm = LLMService(provider='openai', config=config)
```

## 配置说明

### 环境变量配置

在 `.env` 文件中配置：

```env
# OpenAI配置
OPENAI_API_KEY=your-openai-key
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选
OPENAI_MODEL=gpt-4o  # 可选

# 火山引擎配置
VOLCENGINE_ARK_API_KEY=your-volcengine-key
VOLCENGINE_REGION=cn-beijing
VOLCENGINE_TEXT_MODEL=deepseek-v3-1-terminus
VOLCENGINE_TEXT_API_URL=  # 可选，默认根据region构建

# 通义千问配置
DASHSCOPE_API_KEY=your-dashscope-key
DASHSCOPE_MODEL=qwen-flash

# 默认提供商（可选，auto表示自动检测）
LLM_DEFAULT_PROVIDER=auto
```

### 优先级顺序

1. 火山引擎（如果配置了VOLCENGINE_ARK_API_KEY）
2. 通义千问（如果配置了DASHSCOPE_API_KEY）
3. OpenAI（如果配置了OPENAI_API_KEY）

## 扩展新的提供商

### 1. 创建适配器

```python
# backend/llm/providers/custom_provider.py
from .base import ProviderAdapter, LLMResponse

class CustomProvider(ProviderAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 初始化你的客户端
    
    def call(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        # 实现调用逻辑
        # 返回LLMResponse对象
        pass
```

### 2. 注册到LLMService

在 `backend/llm/base.py` 的 `_create_adapter` 方法中添加：

```python
elif provider == 'custom':
    from .providers.custom_provider import CustomProvider
    return CustomProvider(provider_config)
```

### 3. 添加配置

在 `backend/llm/config.py` 的 `_load_from_env` 方法中添加：

```python
self.config.setdefault('custom', {
    'api_key': os.getenv('CUSTOM_API_KEY', ''),
    'model': os.getenv('CUSTOM_MODEL', 'default-model'),
})
```

## 异常处理

```python
from llm import LLMService
from llm.exceptions import (
    LLMException,
    LLMProviderError,
    LLMAccountError,
    LLMNetworkError,
    LLMTimeoutError
)

try:
    llm = LLMService()
    response = llm.chat_completion("你好")
except LLMAccountError as e:
    print(f"账户错误: {e}")
except LLMNetworkError as e:
    print(f"网络错误: {e}")
except LLMException as e:
    print(f"LLM错误: {e}")
```

## 在业务代码中使用

### AIGenerator（业务层）

```python
from game.ai_generator import AIGenerator

# 自动检测提供商
ai_gen = AIGenerator()

# 或指定提供商
ai_gen = AIGenerator(provider='volcengine')

# 生成文本
text = ai_gen._call_text_generation(
    prompt="生成一段故事",
    max_tokens=200,
    temperature=0.7
)
```

## 最佳实践

1. **使用自动检测**：让框架自动选择可用的提供商
2. **统一接口**：始终使用 `LLMService` 的统一接口，不要直接调用适配器
3. **错误处理**：捕获 `LLMException` 并处理各种错误类型
4. **配置管理**：使用环境变量管理配置，不要硬编码
5. **重试机制**：对于重要调用，使用 `call_with_retry` 方法

## 兼容性

- ✅ 完全兼容OpenAI SDK格式
- ✅ 支持所有OpenAI兼容的API（如OpenRouter、Together AI等）
- ✅ 向后兼容旧代码（AIGenerator保持不变）

## 迁移指南

### 从旧代码迁移

旧代码：
```python
ai_gen = AIGenerator()
result = ai_gen._call_text_generation(prompt, max_tokens=200)
```

新代码（无需修改）：
```python
ai_gen = AIGenerator()  # 自动使用新的LLM框架
result = ai_gen._call_text_generation(prompt, max_tokens=200)
```

### 直接使用LLM框架

```python
from llm import LLMService

llm = LLMService()
response = llm.chat_completion(prompt, max_tokens=200)
text = response  # 直接返回字符串
```
