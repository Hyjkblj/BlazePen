# DashScope TTS API调用说明

## ✅ 已验证的API调用方式

### 基础TTS调用（qwen3-tts-flash-realtime）

**已验证成功** ✅

```python
import dashscope
from dashscope import MultiModalConversation

dashscope.api_key = 'your-api-key'
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

response = MultiModalConversation.call(
    model='qwen3-tts-flash-realtime',
    text='你好，这是一个测试。',
    voice='Cherry',  # 必须指定voice参数
    language_type='Chinese'
)

# 响应结构
# response.status_code = 200
# response.output.audio.url = "http://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/..."
# response.output.audio.data = ""  # 通常为空
```

### 音频获取方式

DashScope返回的音频在 `response.output.audio` 对象中：

```python
audio_obj = response.output.audio

# 方式1：使用data字段（如果存在且不为空）
if audio_obj.data:
    import base64
    audio_bytes = base64.b64decode(audio_obj.data)
else:
    # 方式2：从URL下载（推荐，因为data通常为空）
    import requests
    audio_response = requests.get(audio_obj.url, timeout=30)
    audio_bytes = audio_response.content
```

---

## ⚠️ 注意事项

### 1. voice参数是必需的

`qwen3-tts-flash-realtime` **必须指定 voice 参数**，否则会报错。

**可用的音色**（需要查看DashScope文档确认）：
- `Cherry` - 女声（已验证可用）
- 其他音色需要查看官方文档

### 2. 音频URL有效期

返回的音频URL有有效期（`expires_at`字段），需要及时下载。

### 3. qwen3-tts-vd-realtime模型

`qwen3-tts-vd-realtime-2026-01-15` 可能需要：
- 不同的API端点（WebSocket）
- 不同的调用方式
- 需要进一步测试

**当前**：项目统一使用 `qwen3-tts-flash-realtime`。

---

## 🔧 已修正的代码

### TTS服务 (`backend/api/services/tts_service.py`)

已修正：
- ✅ 支持从URL下载音频
- ✅ 优先使用data字段，如果为空则从URL下载
- ✅ 默认使用 `qwen3-tts-flash-realtime` 模型
- ✅ 默认音色设置为 `Cherry`

---

## 🧪 测试结果

### 测试1: 基础TTS ✅

```bash
python test_tts_simple.py
```

**结果**：
- ✅ API调用成功（状态码200）
- ✅ 音频URL获取成功
- ✅ 音频下载成功（76844 bytes）
- ✅ 音频文件保存成功

### 测试2: Voice Design API ⚠️

**状态**：需要进一步测试

**问题**：
- 400错误（url error）
- 可能需要不同的API端点或参数格式

**建议**：
- 查看DashScope官方文档确认Voice Design API的正确调用方式
- 可能需要使用专门的Voice Design端点

---

## 📝 下一步

1. **确认所有可用音色**：查看DashScope文档获取完整的音色列表
2. **测试Voice Design API**：确认正确的调用方式
3. **测试realtime模型**：如果需要实时合成功能
4. **集成到游戏流程**：在生成对话时自动生成语音

---

## 📚 参考

- DashScope TTS API文档：https://help.aliyun.com/zh/model-studio/qwen-tts-api
- 测试脚本：`backend/test_tts_simple.py`
