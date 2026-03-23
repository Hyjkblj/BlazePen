# Training 多模态补充方案：文本连续性 + 大/小场景生图

> 适用范围：`backend/training` 链路，最小改动接入。  
> 复用现有服务：`LLMService`、`ImageService`、`TTSService`。  
> 目标：在不改动核心 K/S 决策链路的前提下，稳定输出 `context_text + image + tts`。

---

## 1. 现状与边界

- 决策边界保持不变：`Recommendation/Flow/DecisionContext` 继续由 K/S 与规则驱动。
- LLM 只负责“表达层”：生成 `context_text / tts_text / emotion / image_prompt`。
- 生图与TTS失败不阻塞回合推进。
- 你当前已有分层场景基础：`data/scenes.py`
  - `MAJOR_SCENES`：6 个大场景
  - `SUB_SCENES`：80 个小场景

---

## 2. JSON 契约如何“约束 + 连续”

### 2.1 固定输出契约（对 LLM 强约束）

```json
{
  "context_text": "40-120字，面向玩家",
  "tts_text": "20-140字，可与context_text相同",
  "emotion": "calm|neutral|tense|urgent|reassuring",
  "image_prompt": "80-220字，面向生图服务",
  "style_tags": ["0-4个白名单标签"]
}
```

### 2.2 字段级硬约束（建议在 policy 里做校验）

- `context_text`
  - 长度：40-120 字。
  - 必须包含 3 个语义槽：`场景锚点`、`风险/冲突信号`、`本轮行动窗口`。
  - 禁止新增世界观事实（例如突然新增地点/角色身份）。
- `tts_text`
  - 长度：20-140 字。
  - 句子短、少括号、少数字串，便于播报。
- `emotion`
  - 仅允许 5 个枚举值。
  - 与 `conflict_level` 映射必须一致（见 2.4）。
- `image_prompt`
  - 80-220 字。
  - 必须包含：`major_scene`、`sub_scene`、`time_of_day`、`weather`、`conflict_level`。
  - 不得出现“多人脸部特写、文字水印、logo、低清、畸形”等负面词。
- `style_tags`
  - 从白名单取值，最多 4 个。

### 2.3 连续性状态（存 session_meta，不改表结构）

建议新增：`session_meta.multimodal_context_state`

```json
{
  "style_profile": "v1_news_realism",
  "major_scene_id": "school",
  "sub_scene_id": "library",
  "time_of_day": "黄昏",
  "weather": "阴天",
  "last_emotion": "tense",
  "last_conflict_level": "medium",
  "facts_locked": ["地点=图书馆", "任务=核验快讯"],
  "open_loops": ["目击者证词待二次核验"],
  "last_context_digest": "sha256(...)"
}
```

### 2.4 连续性生成规则（每轮执行）

1. 先从 K/S 计算 `conflict_index/conflict_level`（算法主导）。
2. 读取 `multimodal_context_state` 作为“硬锚点”。
3. 调用 LLM 生成 JSON。
4. 本地校验：长度、枚举、白名单、事实冲突。
5. 校验失败：一次修复重试（把失败原因回注 prompt）。
6. 再失败：模板兜底（按 `conflict_level` 选模板）。
7. 把本轮结果回写 `multimodal_context_state`。

推荐情绪映射（可配置）：
- `low -> calm|neutral`
- `medium -> tense`
- `high -> urgent|reassuring`（是否安抚由风险类型决定）

---

## 3. 大场景/小场景生图如何生成

### 3.1 总体策略：分层预生成 + 在线补全

- L0（预生成，离线）：先生成“大场景母版图”。
- L1（预生成，离线）：再生成“小场景变体图”（复用母版风格）。
- L2（在线，实时）：缓存未命中时才实时生图。

这样做能把首包时延压到最小，同时保持视觉连续性。

### 3.2 推荐生成批次（按最小可用优先）

基于你当前 `6` 个大场景、`80` 个小场景：

- Phase A（先上线）
  - 大场景：每个大场景生成 `3` 张（`low/medium/high`）
  - 共 `6 x 3 = 18` 张
- Phase B（主流程覆盖）
  - 只对“训练链路会命中的小场景”生成
  - 每个小场景 `2` 张（`normal/tense`）
- Phase C（全量完善）
  - 80 个小场景全量生成，每个 `3` 张（`low/medium/high`）
  - 共 `80 x 3 = 240` 张

> 建议不要一开始全量 240 张，先做命中路径（最小改动、最快见效）。

### 3.3 提示词拼装（保证同一世界观）

最终 `image_prompt` 推荐由三段拼接：

1. `StyleAnchor`（固定）
- 例如：新闻纪实、写实插画、16:9、电影光影、无人物特写、无文字水印。

2. `MajorSceneAnchor`（半固定）
- 来自 `MAJOR_SCENES[major_scene_id]` 的 `name/description/keyword`。

3. `SubSceneDelta`（动态）
- 来自 `SUB_SCENES[sub_scene_id]` 的 `name/description` + `time_of_day/weather/conflict_level`。

这样可确保：
- 大场景统一风格；
- 小场景有差异但不跳戏；
- 冲突强度变化能体现在光照/构图/氛围上。

### 3.4 运行时选图顺序（强烈建议固定）

1. `session_meta.multimodal_cache` 命中直接返回。
2. 命中预生成图包（按 `major/sub/conflict_level` 选图）。
3. 仍未命中才调用 `image_service.generate_scene_image(...)`。
4. 超时 > `image_timeout_budget(7s)`：返回 `image.status=failed|pending`，不阻塞主流程。

缓存键建议：
- `session_id + scenario_id + major_scene_id + sub_scene_id + conflict_level + style_profile + image_prompt_hash`

### 3.5 关键实现修复（最小改动）

你当前场景生图里已本地落盘，但返回值常是远端临时 URL。建议修复为：

- 当 `save_image()` 成功时，返回本地静态 URL：
  - 小场景：`/static/images/smallscenes/...`
  - 大场景：`/static/images/scenes/...`
- 仅落盘失败时才回退远端 URL。

---

## 4. 模型调用参数建议（训练链路）

### 4.1 文本 LLM

- `provider`: `auto`
- `max_tokens`: `220`
- `temperature`: `0.4`
- `max_retries`: `1`
- `retry_delay`: `0.3`
- `context_timeout_budget`: `2.5s`

### 4.2 生图

- `generate_scene_image(scene_data, scene_id, user_id)`
- `image_timeout_budget`: `7s`（体验预算）
- V1 同步：超时即 `failed`
- V2 异步：首包 `pending`，后台补图后 `ready`

### 4.3 TTS

- `generate_speech(text, character_id, emotion_params, use_cache=True)`
- `tts_timeout_budget`: `3s`
- `emotion` 统一映射为 `speed/pitch/volume`（HTTP）+ `emotion_scale/speech_rate/loudness_rate`（WebSocket）

---

## 5. 最小改动接入点

- 新增：`training/multimodal_experience_policy.py`
  - 负责 LLM 文本、生图、TTS 编排和校验。
- 修改：`api/services/training_service.py`
  - `init_training()` 与 `get_next_scenario()` 注入 `experience`。
- 修改：`api/services/image/image_generation_service.py`
  - 场景图落盘后优先返回本地静态 URL。
- 复用：`session_meta` 存 `multimodal_context_state` 和 `multimodal_cache`（不改 DB schema）。

---

## 6. 验收标准

- 文本：`context_text` 连续 5 轮不出现地点/任务跳变，字段全部通过校验。
- 生图：首包可在预算内返回 `ready/pending/failed`，不阻塞训练。
- 连续性：同一 `major_scene` 下小场景切换不出现明显风格断裂。
- 稳定性：LLM/生图/TTS 任一失败，训练主流程仍可完成。

---

## 7. 你可以直接执行的上线顺序

1. 先做 `文本连续性校验 + session_meta 状态`（最快见效）。
2. 再做 `大场景18张预生成`（立刻提升视觉稳定性）。
3. 最后按命中率补小场景图包，并开启异步补图。
