# LLM框架快速开始

## 5分钟上手

### 1. 配置环境变量

在 `.env` 文件中配置至少一个提供商的API密钥：

```env
# 选项1：火山引擎（推荐）
VOLCENGINE_ARK_API_KEY=your-key
VOLCENGINE_TEXT_MODEL=deepseek-v3-1-terminus

# 选项2：通义千问
DASHSCOPE_API_KEY=your-key
DASHSCOPE_MODEL=qwen-flash

# 选项3：OpenAI
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o
```

### 2. 基本使用

```python
from llm import LLMService

# 自动检测并使用可用的提供商
llm = LLMService()

# 调用LLM
text = llm.chat_completion("你好", max_tokens=100)
print(text)
```

### 3. 在业务代码中使用

```python
from game.ai_generator import AIGenerator

# 使用方式完全不变（向后兼容）
ai_gen = AIGenerator()
text = ai_gen._call_text_generation("生成故事", max_tokens=200)
```

## 常用操作

### 切换提供商

```python
# 方式1：初始化时指定
llm = LLMService(provider='volcengine')

# 方式2：通过环境变量
# LLM_DEFAULT_PROVIDER=volcengine
```

### 多轮对话

```python
messages = [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！"},
    {"role": "user", "content": "继续对话"}
]

response = llm.call(messages=messages)
print(response.text)
```

### 错误处理

```python
from llm.exceptions import LLMAccountError, LLMNetworkError

try:
    text = llm.chat_completion("你好")
except LLMAccountError:
    print("账户问题，请检查API密钥")
except LLMNetworkError:
    print("网络问题，请检查连接")
```

## 支持的提供商

| 提供商 | 配置项 | 状态 |
|--------|--------|------|
| OpenAI | `OPENAI_API_KEY` | ✅ 已实现 |
| 火山引擎 | `VOLCENGINE_ARK_API_KEY` | ✅ 已实现 |
| 通义千问 | `DASHSCOPE_API_KEY` | ✅ 已实现 |
| OpenRouter | `OPENAI_BASE_URL` + `OPENAI_API_KEY` | ✅ 兼容 |
| 其他OpenAI兼容API | `OPENAI_BASE_URL` + `OPENAI_API_KEY` | ✅ 兼容 |

## 更多信息

- 详细文档：[README.md](README.md)
- 使用示例：[../../docs/LLM框架使用示例.md](../../docs/LLM框架使用示例.md)
- 重构说明：[../../docs/LLM框架重构说明.md](../../docs/LLM框架重构说明.md)
