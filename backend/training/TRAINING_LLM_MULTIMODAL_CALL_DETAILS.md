# Training 多模态细化方案（文本 / 生图 / TTS 调用细节）

> 基于：
> - `TRAINING_LLM_MULTIMODAL_INTEGRATED_PLAN.md`（整合总方案）
> - 现有实现：`LLMService` / `ImageService` / `TTSService`
>
> 目标：细化到“具体怎么调、参数怎么配、失败怎么降级、代码落在哪”。

## 1. 调用总览（一次场景体验的完整链路）

1. 训练引擎先完成决策（选题/流转）  
2. 体验层计算 `conflict_index`（由 K/S + 最近风险驱动）  
3. 文本模型生成：
   - `context_text`
   - `tts_text`
   - `emotion`
   - `image_prompt`
4. 生图模型基于 `image_prompt` 生成场景图  
5. TTS 基于 `tts_text + emotion_params` 生成音频  
6. 组装 `experience` 回包给前端（`ready/pending/failed`）

边界原则：LLM 只做表达，不改评分/推荐/流转。

---

## 2. 文本大模型（LLM）调用细节

### 2.1 使用入口
- 类：`llm.LLMService`
- 调用：`call_with_retry(messages=..., max_tokens=..., temperature=..., max_retries=..., retry_delay=...)`
- 当前训练评估链路参考：`training/evaluator.py`

### 2.2 建议新增体验层调用（用于 context）
- 新建 `training/multimodal_experience_policy.py`
- 在其中注入 `LLMService(provider="auto" or config)`

### 2.3 Prompt 输入（最小必要字段）
- 场景：`id/title/location/brief/mission/decision_focus/risk_tags`
- 运行态：`round_no/k_state/s_state/recent_risk_flags`
- 冲突：`conflict_index/conflict_level/drivers`
- 输出约束：JSON-only

### 2.4 输出 JSON 契约（建议固定）
```json
{
  "context_text": "40-120字，面向玩家",
  "tts_text": "可与context_text相同",
  "emotion": "calm|neutral|tense|urgent|reassuring",
  "image_prompt": "面向生图服务的场景描述",
  "style_tags": ["可选"]
}
```

### 2.5 参数建议（体验层）
- `provider`: `auto`
- `model`: `LLM_TEXT_MODEL`（默认来自 `model_config.py`，当前默认值 `deepseek-v3-250324`）
- `max_tokens`: `220`
- `temperature`: `0.4`
- `max_retries`: `1`
- `retry_delay`: `0.3`
- 预算超时（建议在 policy 控制总预算）：`2.5s`

### 2.6 失败降级
- LLM失败时按 `conflict_level` 使用模板：
  - `low`: 冷静核验提示
  - `medium`: 时效与准确权衡提示
  - `high`: 风险升级与决策窗口收缩提示
- 记录 `fallback_reason` 到 `experience.context`

---

## 3. 生图大模型调用细节

### 3.1 使用入口（复用现有服务）
- 门面：`api/services/image_service.py`
- 场景图：`image_service.generate_scene_image(scene_data, scene_id, user_id)`
- 内部真实执行：`image/image_generation_service.py`

### 3.2 输入结构（建议）
```python
scene_data = {
    "scene_id": scenario_id,
    "scene_name": scenario_title,
    "scene_description": context_text,
    "atmosphere": conflict_level,   # low/medium/high 可映射为平稳/紧张/危机
    "time_of_day": "白天|夜晚|黄昏",
    "weather": "晴天|阴天|雨天"
}
```

### 3.3 当前实现中的关键参数（现状）
- VolcEngine（优先）：
  - endpoint: `https://{host}/api/v3/images/generations`
  - payload:
    - `model = VOLCENGINE_IMAGE_MODEL`
    - `size = "2560x1440"`（场景图）
    - `response_format = "url"`
    - `watermark = False`
    - `stream = False`
  - timeout: `120s`（现状）
- DashScope（兜底）：
  - `model = wanx-v1`
  - `size = "1920*1080"`
  - `n = 1`

### 3.4 训练链路参数建议（为首包时延优化）
- `image_timeout_budget`: `7s`（体验层预算）
- 同步模式 V1：
  - 超时则 `image.status=failed`，不阻塞整体
- 异步模式 V2：
  - 首包 `pending`，后台补全后 `ready`

### 3.5 缓存与复用
- 以 `session_id + scenario_id + image_prompt_hash` 为键写入：
  - `session_meta.multimodal_cache`
- 已命中缓存则直接返回已有 URL，避免重复生图。

### 3.6 重要实现注意
- 现有“场景图”分支即使本地落盘，也可能返回临时远端 URL。  
  建议最小修复：若保存成功，统一转换成 `/static/images/scenes/...` 再返回，避免临时链接过期。

---

## 4. TTS 大模型调用细节

### 4.1 使用入口（复用现有服务）
- `tts_service.generate_speech(text, character_id, emotion_params=..., use_cache=True, override_voice_id=None)`
- 返回：
  - `audio_url`
  - `audio_path`
  - `duration`
  - `cached`

### 4.2 当前实现中的参数通道
- HTTP通道（火山/部分实现）识别：
  - `speed_ratio`（来自 `emotion_params["speed"]`）
  - `volume_ratio`（来自 `emotion_params["volume"]`）
  - `pitch_ratio`（来自 `emotion_params["pitch"]`）
- WebSocket通道识别：
  - `emotion`
  - `emotion_scale`
  - `speech_rate`
  - `loudness_rate`

### 4.3 统一情绪映射（建议同时给两套字段）
```python
EMOTION_MAP = {
    "calm": {
        "speed": 0.95, "pitch": 0.95, "volume": 1.00,
        "emotion": "calm", "emotion_scale": 1.0, "speech_rate": 0.95, "loudness_rate": 1.00
    },
    "neutral": {
        "speed": 1.00, "pitch": 1.00, "volume": 1.00,
        "emotion": "neutral", "emotion_scale": 1.0, "speech_rate": 1.00, "loudness_rate": 1.00
    },
    "tense": {
        "speed": 1.08, "pitch": 1.06, "volume": 1.03,
        "emotion": "serious", "emotion_scale": 1.2, "speech_rate": 1.08, "loudness_rate": 1.03
    },
    "urgent": {
        "speed": 1.15, "pitch": 1.10, "volume": 1.06,
        "emotion": "urgent", "emotion_scale": 1.4, "speech_rate": 1.15, "loudness_rate": 1.06
    },
    "reassuring": {
        "speed": 0.92, "pitch": 0.98, "volume": 1.02,
        "emotion": "warm", "emotion_scale": 1.1, "speech_rate": 0.92, "loudness_rate": 1.02
    }
}
```

### 4.4 参数建议（体验层）
- `text`: 优先 `tts_text`，无则 `context_text`
- `character_id`: 会话角色ID（无则给默认角色）
- `use_cache`: `True`
- 预算超时：`3s`（超时只降级音频）

---

## 5. `TrainingMultimodalExperiencePolicy` 参考调用骨架

```python
class TrainingMultimodalExperiencePolicy:
    def build_experience(self, *, session, scenario_payload, round_no, k_state, s_state, recent_risk_rounds):
        conflict = self._compute_conflict_index(
            scenario_payload=scenario_payload,
            k_state=k_state,
            s_state=s_state,
            recent_risk_rounds=recent_risk_rounds,
        )

        # 1) 文本 LLM
        text_result = self._build_context_by_llm(
            scenario_payload=scenario_payload,
            round_no=round_no,
            conflict=conflict,
            k_state=k_state,
            s_state=s_state,
        )  # 失败返回模板

        # 2) 生图
        image_result = self._build_scene_image(
            session=session,
            scenario_payload=scenario_payload,
            image_prompt=text_result["image_prompt"],
            conflict=conflict,
        )  # 失败仅标记 failed

        # 3) TTS
        tts_result = self._build_tts_audio(
            session=session,
            text=text_result["tts_text"] or text_result["context_text"],
            emotion=text_result["emotion"],
        )  # 失败仅标记 failed

        return {
            "version": "v1",
            "context": {
                "text": text_result["context_text"],
                "tts_text": text_result["tts_text"],
                "emotion": text_result["emotion"],
                "conflict_index": conflict["conflict_index"],
                "conflict_level": conflict["conflict_level"],
                "drivers": conflict["drivers"],
                "source": text_result.get("source", "llm"),
                "model": text_result.get("model"),
                "fallback_reason": text_result.get("fallback_reason"),
            },
            "image": image_result,
            "audio": tts_result,
        }
```

---

## 6. `TrainingService` 接入点与调用顺序

### 6.1 接入点
- `init_training()`：构建 `next_scenario` 后注入 `experience`
- `get_next_scenario()`：构建 `scenario` 后注入 `experience`

### 6.2 注入方式（最小改动）
- 直接对场景 payload 增加：
  - `scenario_payload["experience"] = experience_dict`
- 依赖当前 `TrainingScenarioOutput.extra_fields` + `TrainingScenarioResponse.extra="allow"` 透传，无需改主响应 schema。

---

## 7. 配置项建议（新增到 training_runtime_config.json）

```json
{
  "multimodal": {
    "enabled": true,
    "modes": ["guided", "adaptive"],
    "timeouts": {
      "total_ms": 9000,
      "context_ms": 2500,
      "image_ms": 7000,
      "tts_ms": 3000
    },
    "text_llm": {
      "provider": "auto",
      "max_tokens": 220,
      "temperature": 0.4,
      "max_retries": 1,
      "retry_delay": 0.3
    },
    "image": {
      "enabled": true,
      "async_mode": false,
      "cache_ttl_minutes": 1440
    },
    "tts": {
      "enabled": true,
      "use_cache": true
    },
    "conflict": {
      "risk_window": 5,
      "weights": {
        "weakness": 0.35,
        "panic": 0.30,
        "safety_risk": 0.20,
        "risk_recent": 0.15
      },
      "thresholds": {
        "low": 0.35,
        "high": 0.65
      }
    }
  }
}
```

---

## 8. 观测与审计（建议新增事件）

- `multimodal_context_generated`
- `multimodal_context_failed`
- `multimodal_image_generated`
- `multimodal_image_failed`
- `multimodal_tts_generated`
- `multimodal_tts_failed`

事件 payload 最少包含：
- `session_id`
- `round_no`
- `scenario_id`
- `provider/model`
- `latency_ms`
- `cached`（image/tts）
- `fallback_reason`（失败时）

---

## 9. 前端调用与渲染约定

前端无需新增接口，继续使用：
- `POST /api/training/init`
- `POST /api/training/scenario/next`

只新增读取：
- `next_scenario.experience`
- `scenario.experience`

渲染策略：
- `context.text` 始终可渲染
- `image.status == ready` 时渲染图
- `audio.status == ready` 时显示可播放控件
- `failed` 时显示轻提示，不中断训练流程

---

## 10. 实施优先顺序（落地建议）

1. 先做文本 LLM + TTS（低延迟、易观察）  
2. 再接生图同步（先打通）  
3. 最后做生图异步和缓存深化  

这样可以最快给前端“可见价值”，同时把风险控制在最小范围。

