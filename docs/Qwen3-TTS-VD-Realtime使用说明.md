# Qwen3-TTS-VD-Realtime 使用说明

## 📋 模型信息

- **模型名称**: `qwen3-tts-vd-realtime-2026-01-15`
- **核心特性**:
  - ✅ **Voice Design（语音设计）**：通过文本描述生成自定义音色
  - ✅ **实时合成**：低延迟，适合实时对话
  - ✅ **多语言支持**：支持中文、英文等多种语言
  - ✅ **高质量语音**：自然流畅，拟人化程度高

---

## 🎯 Voice Design 功能

### 什么是 Voice Design？

Voice Design 允许你通过**文本描述**来创建自定义音色，无需上传音频样本。

### 描述规范

- **长度限制**：不超过 2048 字符
- **语言**：仅支持中文或英文
- **原则**：
  - ✅ **具体而非模糊**：使用明确的描述词
  - ✅ **多维而非单维**：从多个维度描述（性别、年龄、音调、语速、情感等）
  - ✅ **客观而非主观**：使用客观的描述词
  - ✅ **原创而非模仿**：不要描述名人或声优

### 可描述的维度

- **性别**：男声、女声、中性
- **年龄**：幼年、少年、青年、中年、老年
- **音调**：低沉、中等、高亢
- **语速**：缓慢、适中、快速
- **情感**：温柔、活泼、沉稳、高冷、甜美等
- **其他**：音色厚度、亮度、清晰度等

### 描述示例

**好的描述**：
```
温柔的女声，音调中等偏高，语速适中，带有甜美的感觉，适合年轻女性角色
```

```
沉稳的男声，音调偏低，语速较慢，声音有磁性，适合成熟男性角色
```

**不好的描述**：
```
像周杰伦的声音（❌ 模仿名人）
很好听的声音（❌ 太模糊）
```

---

## 🔧 API 使用

### 1. 基础TTS调用（使用预设音色）

```python
from api.services.tts_service import TTSService

tts_service = TTSService()

# 使用预设音色生成语音
audio_info = tts_service.generate_speech(
    text="你好，很高兴认识你！",
    character_id=1,
    emotion_params={
        'emotion': 'happy',
        'speed': 1.0
    }
)
```

### 2. Voice Design创建自定义音色

```python
# 通过文本描述创建自定义音色
result = tts_service.create_voice_from_description(
    description="温柔的女声，音调中等偏高，语速适中，带有甜美的感觉",
    character_id=1
)

if result['success']:
    voice_id = result['voice_id']
    print(f"自定义音色创建成功: {voice_id}")
    
    # 使用自定义音色生成语音
    audio_info = tts_service.generate_speech(
        text="你好，很高兴认识你！",
        character_id=1  # 会自动使用刚创建的自定义音色
    )
```

### 3. 在角色创建时设置Voice Design

```python
# 获取角色音色配置
voice_config = tts_service.get_character_voice_config(character_id)

# 设置Voice Design描述
voice_config['voice_design_description'] = "温柔的女声，音调中等，语速适中"
voice_config['voice_type'] = 'voice_design'

# 保存配置（实际应该保存到数据库）
tts_service.voice_configs[character_id] = voice_config

# 生成语音时会自动使用Voice Design
audio_info = tts_service.generate_speech(
    text="你好！",
    character_id=character_id
)
```

---

## 📊 工作流程

### 方式一：预设音色库

```
角色创建
    ↓
选择预设音色（如：甜美女声）
    ↓
保存音色ID到角色配置
    ↓
生成语音时使用预设音色
```

### 方式二：Voice Design

```
角色创建
    ↓
输入音色描述文本
    ↓
调用Voice Design API生成自定义音色
    ↓
保存voice_id到角色配置
    ↓
生成语音时使用自定义音色
```

---

## ⚙️ 配置说明

### 环境变量

```env
# DashScope API密钥
DASHSCOPE_API_KEY=sk-972acd8d4be44cd497bc396f38a6a088

# TTS模型（默认统一使用 flash-realtime；VD 音色时自动用 vd-realtime）
DASHSCOPE_TTS_MODEL=qwen3-tts-flash-realtime

# TTS提供商
TTS_PROVIDER=dashscope
```

---

## 💰 成本说明

### Voice Design

- **创建音色**：可能需要额外费用（需要查看DashScope定价）
- **使用音色**：与普通TTS相同，0.8元/万字符

### TTS合成

- **单价**：0.8元/万字符（中国内地北京地域）
- **免费额度**：2000字符（2025年11月13日前开通）或1万字符（之后开通）

---

## 🎨 预设音色 vs Voice Design

| 特性 | 预设音色库 | Voice Design |
|------|-----------|--------------|
| **自由度** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **成本** | 低 | 中等 |
| **速度** | 快 | 中等（需要先创建音色） |
| **适用场景** | 快速上线，标准音色 | 个性化需求，自定义音色 |

**建议**：
- **默认使用预设音色库**（快速、稳定）
- **高级功能使用Voice Design**（个性化、定制化）

---

## 📝 注意事项

1. **Voice Design描述质量**：描述越具体、多维，生成的音色质量越好
2. **音色缓存**：生成的voice_id可以重复使用，无需每次重新创建
3. **API限制**：注意Voice Design API的调用频率限制
4. **错误处理**：Voice Design失败时会回退到默认音色

---

## 🚀 下一步

1. **完善Voice Design集成**：实现完整的音色创建和管理流程
2. **前端UI**：添加Voice Design描述输入界面
3. **音色预览**：允许玩家预览生成的音色效果
4. **音色管理**：实现音色的保存、编辑、删除功能

---

## 📚 参考文档

- DashScope TTS API文档：https://help.aliyun.com/zh/model-studio/qwen-tts-api
- Voice Design API文档：https://www.alibabacloud.com/help/en/model-studio/qwen-tts-voice-design
- Qwen3-TTS全面升级：https://developer.aliyun.com/article/1692946
