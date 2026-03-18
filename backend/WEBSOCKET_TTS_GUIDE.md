# 火山引擎双向流式WebSocket TTS 集成指南

## 🚀 概述

基于火山引擎双向流式WebSocket TTS API，我们已经实现了一个功能完整的语音合成服务，支持：

- **双向流式通信** - WebSocket实时传输，低延迟
- **声音复刻** - 支持自定义音色训练和使用
- **混音功能** - 多音色混合，创造独特声音
- **情感控制** - 丰富的情感表达和语音参数调节
- **多语言支持** - 中文、英文、日文等多语种
- **缓存优化** - 智能缓存，提升响应速度

## 📋 功能特性

### ✅ 已实现功能

1. **WebSocket连接管理**
   - 自动连接建立和断开
   - 连接复用和会话管理
   - 错误处理和重连机制

2. **流式语音合成**
   - 实时音频数据流传输
   - 边发边收，降低延迟
   - 支持长文本自动分句

3. **高级音色功能**
   - 豆包语音合成模型1.0/2.0
   - 声音复刻ICL 1.0/2.0
   - 多音色混音（最多3个音色）

4. **情感和语音控制**
   - 情感类型设置（开心、悲伤、愤怒等）
   - 语速调节（0.5-2.0倍）
   - 音量控制（0.5-2.0倍）
   - 音调调节（0.5-2.0倍）

5. **多语言支持**
   - 中文（中国）
   - 英语、日语、德语、法语
   - 西班牙语、葡萄牙语、印尼语

6. **缓存和优化**
   - 文本级缓存
   - 分句级缓存
   - 音频时长计算

## 🔧 配置说明

### 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# 火山引擎 TTS 配置
VOLCENGINE_TTS_APP_ID=6212235312
VOLCENGINE_TTS_ACCESS_TOKEN=VOHZ2ZChGyPbFxGmfNmOByFZBafHL_Ns
VOLCENGINE_TTS_SECRET_KEY=eHGxzFH0d_QrYxhSzNuNSGxdt0ZXTlbH
VOLCENGINE_REGION=cn-beijing
VOLCENGINE_TTS_MODEL=seed-tts-2.0
VOLCENGINE_TTS_RESOURCE_ID=seed-tts-2.0
TTS_PROVIDER=volcengine

# WebSocket 配置
VOLCENGINE_TTS_WEBSOCKET_URL=wss://openspeech.bytedance.com/api/v3/tts/bidirection
VOLCENGINE_TTS_USE_WEBSOCKET=true

# 高级功能配置
VOLCENGINE_TTS_ENABLE_TIMESTAMP=false
VOLCENGINE_TTS_ENABLE_CACHE=true
VOLCENGINE_TTS_ENABLE_EMOTION=true
```

### 配置参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `VOLCENGINE_TTS_APP_ID` | 火山引擎应用ID | 必填 |
| `VOLCENGINE_TTS_ACCESS_TOKEN` | 访问令牌 | 必填 |
| `VOLCENGINE_TTS_SECRET_KEY` | 密钥 | 必填 |
| `VOLCENGINE_TTS_MODEL` | TTS模型版本 | `seed-tts-2.0` |
| `VOLCENGINE_TTS_RESOURCE_ID` | 资源ID | `seed-tts-2.0` |
| `VOLCENGINE_TTS_USE_WEBSOCKET` | 是否使用WebSocket | `true` |
| `VOLCENGINE_TTS_ENABLE_CACHE` | 是否启用缓存 | `true` |
| `VOLCENGINE_TTS_ENABLE_EMOTION` | 是否启用情感控制 | `true` |

## 🎵 音色库

### 豆包语音合成模型2.0音色

| 音色ID | 名称 | 风格 | 支持情感 | 支持混音 |
|--------|------|------|----------|----------|
| `BV001_streaming` | 通用女声 | 标准 | ✅ | ✅ |
| `BV002_streaming` | 温柔女声 | 温柔甜美 | ✅ | ✅ |
| `BV003_streaming` | 活泼女声 | 活泼开朗 | ✅ | ✅ |
| `BV004_streaming` | 情感女声 | 情感丰富 | ✅ | ✅ |
| `BV005_streaming` | 优雅女声 | 优雅 | ✅ | ✅ |
| `BV006_streaming` | 标准男声 | 标准播音 | ✅ | ✅ |
| `BV007_streaming` | 情感男声 | 情感丰富 | ✅ | ✅ |
| `BV008_streaming` | 成熟男声 | 成熟稳重 | ✅ | ✅ |
| `BV009_streaming` | 年轻男声 | 年轻活力 | ✅ | ✅ |

### 豆包语音合成模型1.0音色

| 音色ID | 名称 | 风格 | 支持情感 | 支持混音 |
|--------|------|------|----------|----------|
| `zh_female_shuangkuaisisi_moon_bigtts` | 双快思思（月亮版） | 温柔甜美 | ✅ | ✅ |
| `zh_female_shuangkuaisisi_sun_bigtts` | 双快思思（太阳版） | 活泼开朗 | ✅ | ✅ |
| `zh_male_aida_bigtts` | 艾达（标准版） | 标准播音 | ✅ | ✅ |
| `zh_male_aida_emotion_bigtts` | 艾达（情感版） | 情感丰富 | ✅ | ✅ |

### 支持的情感类型

| 情感代码 | 中文名称 | 适用场景 |
|----------|----------|----------|
| `happy` | 开心 | 欢乐、庆祝场景 |
| `sad` | 悲伤 | 感人、悲伤情节 |
| `angry` | 愤怒 | 激烈、冲突场景 |
| `surprised` | 惊讶 | 意外、震惊情节 |
| `confident` | 自信 | 坚定、决断场景 |
| `gentle` | 温柔 | 温馨、关怀情节 |
| `serious` | 严肃 | 正式、庄重场景 |
| `cheerful` | 愉快 | 轻松、快乐情节 |

## 💻 使用示例

### 基本语音合成

```python
from api.services.tts_service import TTSService

# 初始化TTS服务（自动选择WebSocket或HTTP模式）
tts_service = TTSService()

# 基本语音合成
result = tts_service.generate_speech(
    text="你好，欢迎使用火山引擎语音合成服务！",
    character_id=1
)

print(f"音频URL: {result['audio_url']}")
print(f"音频路径: {result['audio_path']}")
print(f"服务模式: {tts_service.service_mode}")
```

### WebSocket流式合成

```python
import asyncio
from api.services.websocket_tts_service import WebSocketTTSService

async def stream_tts_example():
    service = WebSocketTTSService()
    
    async with service:
        # 流式接收音频数据
        async for audio_chunk in service.generate_speech_stream(
            text="这是一个流式语音合成的示例。",
            speaker="BV001_streaming"
        ):
            print(f"接收音频块: {len(audio_chunk)} bytes")
            # 可以实时播放或处理音频数据

# 运行异步函数
asyncio.run(stream_tts_example())
```

### 情感语音合成

```python
# 使用情感参数
result = tts_service.generate_speech(
    text="今天真是太开心了！",
    character_id=1,
    override_voice_id="female_004",  # 情感女声
    emotion_params={
        'emotion': 'happy',      # 开心情感
        'emotion_scale': 4,      # 情感强度（1-5）
        'speech_rate': 20,       # 语速+20%
        'loudness_rate': 10      # 音量+10%
    }
)
```

### 混音语音合成

```python
import asyncio
from api.services.websocket_tts_service import WebSocketTTSService

async def mix_tts_example():
    service = WebSocketTTSService()
    
    # 定义混音配置
    mix_speakers = [
        {'source_speaker': 'BV001_streaming', 'mix_factor': 0.6},  # 女声60%
        {'source_speaker': 'BV006_streaming', 'mix_factor': 0.4}   # 男声40%
    ]
    
    async with service:
        result = await service.generate_speech(
            text="这是一个混音语音的示例。",
            character_id=1,
            speaker="custom_mix_bigtts",
            mix_speakers=mix_speakers
        )
    
    print(f"混音语音生成成功: {result['audio_url']}")

asyncio.run(mix_tts_example())
```

### 多语言合成

```python
# 英文语音合成
result = tts_service.generate_speech(
    text="Hello, welcome to our service!",
    character_id=1,
    override_voice_id="male_001",
    emotion_params={
        'explicit_language': 'en'  # 指定英文
    }
)

# 日文语音合成
result = tts_service.generate_speech(
    text="こんにちは、サービスへようこそ！",
    character_id=1,
    override_voice_id="female_002",
    emotion_params={
        'explicit_language': 'ja'  # 指定日文
    }
)
```

## 🧪 测试验证

### 运行基本测试

```bash
cd backend
python test_doubao_tts.py
```

### 运行WebSocket专项测试

```bash
cd backend
python test_websocket_tts.py
```

### 测试项目

1. **配置检查** - 验证所有配置参数
2. **WebSocket连接** - 测试连接建立和断开
3. **基本TTS功能** - 测试语音生成
4. **流式TTS功能** - 测试实时音频流
5. **情感TTS功能** - 测试情感参数
6. **混音TTS功能** - 测试多音色混音
7. **同步包装器** - 测试兼容性接口

## 📊 性能优化

### 缓存策略

1. **文本级缓存** - 相同文本直接返回缓存音频
2. **分句级缓存** - 长文本分句缓存，提升首包速度
3. **智能缓存键** - 基于文本、音色、参数生成唯一键

### 连接管理

1. **连接复用** - 同一WebSocket连接支持多次会话
2. **自动重连** - 网络异常时自动重新建立连接
3. **优雅断开** - 正确的连接生命周期管理

### 错误处理

1. **分层错误处理** - 连接、会话、任务三级错误处理
2. **详细错误信息** - 提供具体的错误代码和描述
3. **降级策略** - WebSocket失败时自动降级到HTTP

## 🔄 服务模式切换

### 自动模式选择

系统会根据配置自动选择最佳服务模式：

1. **WebSocket优先** - 如果配置启用且依赖可用
2. **HTTP降级** - WebSocket不可用时自动使用HTTP
3. **兼容性保证** - 两种模式提供相同的接口

### 手动模式配置

```bash
# 强制使用WebSocket模式
VOLCENGINE_TTS_USE_WEBSOCKET=true

# 强制使用HTTP模式
VOLCENGINE_TTS_USE_WEBSOCKET=false
```

## 🚨 注意事项

### 权限要求

1. **TTS服务权限** - 需要在火山引擎控制台开通TTS服务
2. **模型权限** - 确保有对应模型的使用权限
3. **并发限制** - 注意API调用频率限制

### 依赖要求

```bash
# WebSocket功能依赖
pip install websockets

# 音频处理依赖（可选）
pip install pydub

# HTTP功能依赖
pip install requests
```

### 最佳实践

1. **连接复用** - 尽量复用WebSocket连接，避免频繁建连
2. **文本优化** - 长文本建议分段处理，提升用户体验
3. **错误处理** - 实现完善的错误处理和重试机制
4. **缓存利用** - 合理使用缓存，减少API调用

## 📞 故障排除

### 常见问题

1. **WebSocket连接失败**
   ```
   解决：检查网络连接、API Key、资源ID配置
   ```

2. **权限不足错误**
   ```
   解决：在火山引擎控制台开通TTS服务权限
   ```

3. **音色不支持**
   ```
   解决：使用预设音色库中的音色ID
   ```

4. **依赖包缺失**
   ```
   解决：pip install websockets requests pydub
   ```

### 调试模式

启用详细日志输出：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🎯 总结

火山引擎双向流式WebSocket TTS集成已经完成，提供了：

- ✅ **完整的WebSocket TTS实现**
- ✅ **丰富的音色和情感支持**
- ✅ **高级功能（混音、多语言）**
- ✅ **完善的测试和文档**
- ✅ **向后兼容的接口设计**

系统现在支持两种模式：
- **WebSocket模式** - 低延迟、流式传输、高级功能
- **HTTP模式** - 简单稳定、易于调试

用户可以根据需求选择合适的模式，系统会自动处理模式切换和降级，确保服务的稳定性和可用性。