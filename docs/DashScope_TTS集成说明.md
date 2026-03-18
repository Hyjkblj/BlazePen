# DashScope Qwen-TTS 集成说明

## 📋 已实现功能

已使用 **DashScope Qwen3-TTS-Flash-Realtime** 模型实现TTS语音合成服务。

### 配置信息

- **API Key**: `sk-972acd8d4be44cd497bc396f38a6a088`
- **模型**: `qwen3-tts-flash-realtime`（统一使用）
- **音色数量**: 49种音色
- **支持语言**: 中文（多种方言）、英文、日文、韩文等

---

## 🎯 核心特性

### Qwen3-TTS-Flash 优势

✅ **49种高品质音色**：涵盖不同性别、年龄和角色设定  
✅ **多语言多方言**：支持10大主流语言及多种方言  
✅ **自然韵律**：自适应调节语速和韵律，拟人化程度高  
✅ **流式输出**：支持流式输出，降低延迟  
✅ **成本低**：0.8元/万字符（中国内地北京地域）  

---

## 📁 文件结构

```
backend/
├── api/
│   └── services/
│       └── tts_service.py          # TTS服务（新增）
├── data/
│   └── preset_voices.py            # 预设音色库配置（新增）
└── audio/
    └── cache/                       # 音频缓存目录（自动创建）
```

---

## 🔧 使用方法

### 1. 基本使用

```python
from api.services.tts_service import TTSService

# 初始化TTS服务
tts_service = TTSService()

# 生成语音
audio_info = tts_service.generate_speech(
    text="你好，很高兴认识你！",
    character_id=1,
    emotion_params={
        'emotion': 'happy',
        'speed': 1.0
    }
)

print(f"音频URL: {audio_info['audio_url']}")
print(f"音频路径: {audio_info['audio_path']}")
print(f"时长: {audio_info['duration']}秒")
```

### 2. 集成到游戏流程

```python
# backend/api/services/game_service.py

from api.services.tts_service import TTSService

class GameService:
    def __init__(self):
        # ... 现有代码 ...
        self.tts_service = TTSService()
    
    def process_input(self, thread_id: str, user_input: str, option_id: Optional[int] = None):
        # ... 生成对话 ...
        
        # 生成角色语音
        if dialogue_data.get('character_dialogue'):
            try:
                audio_info = self.tts_service.generate_speech(
                    text=dialogue_data['character_dialogue'],
                    character_id=character_id,
                    emotion_params=emotion_params,
                    use_cache=True
                )
                
                response_data['character_audio'] = {
                    'url': audio_info['audio_url'],
                    'duration': audio_info.get('duration', 0)
                }
            except Exception as e:
                print(f"[TTS错误] {e}")
        
        return response_data
```

---

## ⚙️ 环境变量配置

在 `.env` 文件中配置：

```env
# DashScope TTS配置
DASHSCOPE_API_KEY=sk-972acd8d4be44cd497bc396f38a6a088
DASHSCOPE_TTS_MODEL=qwen3-tts-flash-realtime  # 默认

# TTS提供商选择
TTS_PROVIDER=dashscope

# 缓存配置（可选）
TTS_CACHE_ENABLED=true
TTS_CACHE_DIR=backend/audio/cache
```

---

## 🎨 预设音色库

### 当前配置的音色

**男声（5种）**：
- 沉稳男声（zhitianyi）
- 阳光男声（zhiyan）
- 温柔男声（zhijian）
- 磁性男声（zhimo）
- 活力男声（zhiqiang）

**女声（5种）**：
- 甜美女声（zhiqi）
- 知性女声（zhimei）
- 元气女声（zhixia）
- 温柔女声（zhishuang）
- 高冷女声（zhiling）

### 扩展音色

Qwen3-TTS-Flash支持49种音色，可以在 `backend/data/preset_voices.py` 中添加更多音色配置。

**注意**：实际可用的音色ID需要查看DashScope官方文档：
https://help.aliyun.com/zh/model-studio/qwen-tts-api

---

## 📊 API参数说明

### DashScope TTS API参数

```python
{
    'text': '要合成的文本',        # 必填，最大600字符
    'model': 'qwen3-tts-flash-realtime',   # 模型名称
    'voice': 'zhiqi',              # 音色ID（可选）
    'format': 'wav',               # 输出格式（wav, mp3等）
    'sample_rate': 24000,          # 采样率（16000, 24000等）
}
```

### 情绪参数（当前实现）

```python
emotion_params = {
    'emotion': 'happy',    # 情绪类型（happy, sad, angry等）
    'speed': 1.0,          # 语速（0.5-2.0）
    'tone': 'soft',        # 语调（soft, normal, strong）
    'volume': 0.8,         # 音量（0-1）
    'pause_before': 0,     # 前停顿（ms）
    'pause_after': 0       # 后停顿（ms）
}
```

**注意**：Qwen3-TTS-Flash可能不支持所有情绪参数，需要根据实际API文档调整。

---

## 💾 缓存机制

### 缓存策略

- **位置**：`backend/audio/cache/`
- **命名**：MD5(text + character_id + voice_id + emotion_params)
- **格式**：WAV格式（24kHz采样率）
- **清理**：建议定期清理未使用的缓存（LRU策略）

### 缓存键生成

```python
cache_key = md5({
    'text': text,
    'character_id': character_id,
    'voice_id': voice_id,
    'emotion_params': emotion_params,
    'model': 'qwen3-tts-flash-realtime'
})
```

---

## 💰 成本估算

### 价格

- **单价**：0.8元/万字符（中国内地北京地域）
- **免费额度**：2000字符（2025年11月13日前开通）或1万字符（之后开通）

### 使用量估算

- 平均对话：50字符
- 1000次对话 = 5万字 ≈ ￥4
- 月活1万用户，每人100次对话 = 50万字 ≈ ￥40/月

---

## 🚀 下一步

### 1. 完善音色配置

- [ ] 查看DashScope官方文档，确认所有49种音色的ID
- [ ] 更新 `preset_voices.py` 添加更多音色
- [ ] 生成预览音频文件

### 2. 集成到游戏流程

- [ ] 修改 `GameService` 集成TTS服务
- [ ] 前端音频播放组件
- [ ] 端到端测试

### 3. 情绪分析集成

- [ ] 实现情绪分析服务
- [ ] 将情绪参数传递给TTS服务
- [ ] 测试情绪表达效果

### 4. 性能优化

- [ ] 实现异步生成（Celery）
- [ ] 流式输出支持
- [ ] CDN缓存（生产环境）

---

## 📚 参考文档

- DashScope TTS API文档：https://help.aliyun.com/zh/model-studio/qwen-tts-api
- Qwen3-TTS全面升级：https://developer.aliyun.com/article/1692946
- DashScope Python SDK：https://help.aliyun.com/zh/model-studio/cosyvoice-python-sdk

---

## ⚠️ 注意事项

1. **音色ID**：当前配置的音色ID是示例，需要根据DashScope官方文档确认实际可用的音色ID
2. **情绪参数**：Qwen3-TTS-Flash可能不支持所有情绪参数，需要测试确认
3. **依赖安装**：确保已安装 `dashscope>=1.24.6`
4. **API密钥**：请妥善保管API密钥，不要提交到代码仓库

---

## ✅ 已完成

- [x] TTS服务实现（`tts_service.py`）
- [x] 预设音色库配置（`preset_voices.py`）
- [x] 缓存机制
- [x] DashScope集成
- [x] 基础文档

## 🔄 待完成

- [ ] 确认所有49种音色的ID
- [ ] 集成到游戏流程
- [ ] 前端音频播放组件
- [ ] 情绪分析集成
- [ ] 性能优化
