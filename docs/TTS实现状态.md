# TTS功能实现状态

## ✅ 已完成

### 1. TTS服务基础功能 ✅

- ✅ DashScope TTS API集成（HTTP：MultiModalConversation）
- ✅ 音频下载和保存
- ✅ 缓存机制
- ✅ API路由创建
- ✅ 游戏内角色对话自动播放（Game.tsx 调用 generateSpeech，使用玩家所选音色）

### 2. 已验证的功能 ✅

**基础TTS调用（HTTP/WebSocket）**：
- ✅ 默认模型：`qwen3-tts-flash-realtime`（统一使用）
- ✅ 音色：`Cherry`（已验证可用）
- ✅ API调用成功
- ✅ 音频下载成功

**响应格式**：
```python
response.output.audio.url  # OSS URL（需要下载）
response.output.audio.data  # base64字符串（通常为空）
```

### 3. WebSocket 实现状态 ✅

**当前实现**：
- ✅ 后端通过 **DashScope WebSocket（QwenTtsRealtime）** 进行语音合成
- ✅ 使用方式：环境变量 `TTS_USE_WEBSOCKET=1` 时启用 WebSocket；或当角色使用 **Voice Design 音色** 时自动走 WebSocket（因 HTTP 对 VD 音色返回 403）
- ✅ WebSocket 地址（北京）：`wss://dashscope.aliyuncs.com/api-ws/v1/realtime`
- ✅ 支持模型：`qwen3-tts-flash-realtime`（预设音色）、`qwen3-tts-vd-realtime-2025-12-16`（Voice Design 音色）
- ✅ 流程：连接 → update_session(voice, response_format=PCM) → append_text → finish → 收集 response.audio.delta → 转 WAV 写缓存 → 返回与 HTTP 相同的 audio_url

**与 HTTP 的对比**：
| 能力           | HTTP (qwen3-tts-flash-realtime) | WebSocket (QwenTtsRealtime)        |
|----------------|----------------------------|-------------------------------------|
| 预设音色       | ✅ 支持                     | ✅ 支持                             |
| Voice Design 音色 | ❌ 403                      | ✅ 支持（需用 VD-Realtime 模型）    |
| 首包延迟       | 较高                       | 较低（流式）                        |
| 实现位置       | `_generate_dashscope_speech` | `_generate_dashscope_speech_websocket` |

**参考文档**：
- [实时语音合成 - Python SDK](https://help.aliyun.com/zh/model-studio/qwen-tts-realtime-python-sdk)
- DashScope SDK 需 ≥ 1.25.2，`from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat`

**本地测试**：
```bash
cd backend
set TTS_USE_WEBSOCKET=1   # Windows
# export TTS_USE_WEBSOCKET=1  # Linux/macOS
python test_tts_websocket.py
```

---

## ⚠️ 待确认

### 1. 音色列表 ✅

**状态**：已更新 ✅

**当前状态**：
- ✅ qwen3-tts-flash-realtime 支持17种高表现力音色
- ✅ 已更新 `preset_voices.py` 中的音色配置
- ✅ 包含女声、男声、方言特色音色

**已配置的音色**：

**女声**：
- `Cherry` (千悦) - 阳光少女 ✅ 已验证可用
- `Jada` (上海阿珍) - 沪味小姐姐
- `Sunny` (四川清儿) - 甜妹川话
- `Chelsie` - 标准女声
- `Serena` - 优雅女声

**男声**：
- `Ethan` (尘旭) - 标准男播
- `Elias` (莫僵尸) - 学院派
- `Dylan` (北京小东) - 胡同小伙
- `Rocky` (粤语阿强) - 懒音港男

**参考文档**：
- 官方音色列表：https://help.aliyun.com/zh/model-studio/multimodal-timbre-list
- 支持9大方言：普通话、北京、上海、四川、南京、陕西、闽南、天津、粤语

### 2. Voice Design API ✅

**状态**：已修复 ✅

**当前状态**：
- ✅ 已确认正确的API端点：`https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization`
- ✅ 已修复请求参数格式（根据DashScope官方文档）
- ✅ 支持创建自定义音色（action: create）
- ✅ 支持查询音色列表（action: list）
- ✅ 支持查询特定音色（action: query）
- ✅ 支持删除音色（action: delete）

**API调用方式**：
```python
# 创建音色
POST https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization
{
    "model": "qwen-voice-design",
    "input": {
        "action": "create",
        "target_model": "qwen3-tts-vd-realtime-2025-12-16",
        "voice_prompt": "音色描述文本",
        "preview_text": "预览文本",
        "preferred_name": "音色名称",
        "language": "zh"
    },
    "parameters": {
        "sample_rate": 24000,
        "response_format": "wav"
    }
}
```

**已实现功能**：
- ✅ `_generate_voice_design()` - 创建自定义音色
- ✅ `list_voices()` - 查询音色列表
- ✅ API路由：`/v1/tts/voice-design/list` - 查询音色列表

### 3. 使用 Voice Design 音色做 TTS（Realtime 模型）

**测试结果**（2026-01-29）：
- ✅ **Voice Design 创建音色**：成功，返回 `voice_id`，预览音频已保存
- ❌ **HTTP 调用 TTS（自定义音色）**：返回 **403 Access denied**
- **原因**：使用 Voice Design 生成的音色进行合成时，需通过 **WebSocket**（`QwenTtsRealtime`）调用 `qwen3-tts-vd-realtime-2025-12-16`，HTTP `MultiModalConversation` 不支持或需单独权限

**正确约定**：
- 创建音色时的 `target_model` 必须为：`qwen3-tts-vd-realtime-2025-12-16`（与文档一致）
- 后续 TTS 使用的模型必须与 `target_model` 一致，且需使用 **WebSocket** 接口

**当前状态**：
- 测试脚本已改为使用模型 `qwen3-tts-vd-realtime-2025-12-16`（原误用 2026-01-15）
- 若需在游戏内使用自定义音色，需实现 WebSocket 客户端（参考 DashScope 实时语音合成文档）

---

## 🔧 当前配置

### 默认模型

```python
DASHSCOPE_TTS_MODEL=qwen3-tts-flash-realtime  # 统一使用（默认）
```

### 默认音色

```python
voice='Cherry'  # 已验证可用
```

---

## 📝 下一步操作

### 高优先级

1. **WebSocket 已接入**
   - 设置 `TTS_USE_WEBSOCKET=1` 或使用 Voice Design 音色时走 WebSocket
   - 确保 `dashscope>=1.25.2`，可选：单独测试 `backend/test_tts_websocket.py`

2. **测试更多音色**
   - 尝试不同的音色ID（预设 + Voice Design）
   - 确认 WebSocket 下 VD 音色可用

### 中优先级

3. **游戏内 TTS**
   - 已集成：Game 组件在角色对话更新时调用 `generateSpeech` 并自动播放
   - 音色来自角色选择页的预设音色配置

4. **可选：前端直连 WebSocket**
   - 若需流式边播边放，可增加后端 WebSocket 代理或前端直连 DashScope（需妥善保管 API Key）

---

## 📚 参考文档

- DashScope TTS API：https://help.aliyun.com/zh/model-studio/qwen-tts-api
- 测试脚本：`backend/test_tts_simple.py`
- API调用说明：`docs/TTS_API调用说明.md`
