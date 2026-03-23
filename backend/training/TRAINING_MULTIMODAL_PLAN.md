# Training 多模态体验接入方案（最小改动 + 最佳实践）

## 1. 目标
- 场景支持生图服务输出，并把图片资源交给前端展示。
- 场景上下文由 LLM 文本模型生成（不是规则模板硬编码）。
- 同步提供 TTS 音频，支持情绪语气（语速/音调/音量）。
- 保持最小改动：不改数据库表结构，不破坏现有 training API 契约。

## 2. 当前可复用能力（已存在）
- 训练链路：`api/services/training_service.py`、`training/round_transition_policy.py`、`training/runtime_artifact_policy.py`。
- LLM 调用：`training/evaluator.py` 已通过 `llm.LLMService` 打通模型调用、重试、解析、降级。
- 生图服务：`api/services/image_service.py` + `api/services/image/image_generation_service.py`。
- TTS 服务：`api/services/tts_service.py`（支持 emotion 参数与缓存）。
- 输出扩展位：`TrainingScenarioOutput` 支持 `extra_fields`，`TrainingScenarioResponse` 已 `extra = allow`，可以无破坏地新增返回字段。
- 持久化扩展位：`training_rounds.user_action` 为 JSON，可存多模态工件，无需 migration。

## 3. 设计原则
1. 默认不改表结构，优先复用 JSON 字段（`user_action`/`session_meta`）。
2. 不改主流程语义：`init -> next -> submit` 保持一致。
3. 多模态失败不阻塞训练主链路（LLM/生图/TTS 任一失败都能继续训练）。
4. 输出采用统一状态机：`ready | pending | failed`，前端只做状态渲染。
5. 以配置开关灰度发布，先小流量再全量。

## 4. 推荐落地方案（V1）

### 4.1 新增一个编排策略（核心改动最小）
新增文件：`training/multimodal_experience_policy.py`

职责：
- 输入：`session_id / character_id / scenario_payload / round_no / k_state / s_state`。
- 输出：`experience` 对象（上下文文本 + 图片资源 + 音频资源 + 状态/错误信息）。
- 内部复用：
  - `LLMService` 生成上下文文本和情绪标签。
  - `ImageService` 生成或返回场景图。
  - `TTSService` 把上下文文本转音频（带情绪参数）。

建议接口：
```python
class TrainingMultimodalExperiencePolicy:
    def build_experience(self, *, session, scenario_payload, round_no, k_state, s_state) -> dict:
        ...
```

### 4.2 在 TrainingService 两个点接入
修改文件：`api/services/training_service.py`

接入点：
- `init_training()` 返回 `next_scenario` 前。
- `get_next_scenario()` 返回 `scenario` 前。

做法：
- 对当前场景 payload 调用 `build_experience(...)`。
- 将结果挂到场景扩展字段，例如：`scenario_payload["experience"] = {...}`。
- 再走现有 `TrainingScenarioOutput.from_payload()`，借助 `extra_fields` 原样返回前端。

这样不需要改 `api/schemas.py` 的主结构。

### 4.3 前端契约（建议）
新增字段位置：
- `init` 响应：`data.next_scenario.experience`
- `scenario/next` 响应：`data.scenario.experience`

示例：
```json
{
  "experience": {
    "version": "v1",
    "context": {
      "text": "夜色下的前线消息彼此冲突，你必须在时效与核验之间做出取舍。",
      "source": "llm",
      "model": "deepseek-v3-250324"
    },
    "image": {
      "status": "ready",
      "url": "/static/images/smallscenes/xxx.jpg",
      "detail": "generated"
    },
    "audio": {
      "status": "ready",
      "url": "/static/audio/cache/xxx.wav",
      "duration": 4.2,
      "emotion": "tense"
    }
  }
}
```

状态约定：
- `ready`: 资源可直接播放/显示。
- `pending`: 异步生成中（前端可轮询下一次 `scenario/next` 或 session summary）。
- `failed`: 生成失败（前端显示文本兜底）。

### 4.4 LLM 文本上下文最佳实践
- 强制 JSON 输出（和 `training/evaluator.py` 一样），避免自然语言不可解析。
- Prompt 输入最小必要字段：`title/location/brief/mission/decision_focus/risk_tags/round_no/k_state/s_state`。
- 输出结构建议：
  - `context_text`（40~120 字）
  - `tts_text`（可与 context_text 相同）
  - `emotion`（枚举）
  - `image_prompt`（用于生图）
- 失败降级：模板文本（不阻塞主流程）。

### 4.5 TTS 情绪映射建议
LLM 返回情绪标签后，映射为 `emotion_params`：

| emotion | speed | pitch | volume |
| --- | --- | --- | --- |
| calm | 0.95 | 0.95 | 1.0 |
| neutral | 1.0 | 1.0 | 1.0 |
| tense | 1.08 | 1.08 | 1.05 |
| urgent | 1.15 | 1.12 | 1.08 |
| reassuring | 0.92 | 0.98 | 1.02 |

实现时直接复用：
- `tts_service.generate_speech(text, character_id, emotion_params=...)`

### 4.6 生图策略（兼顾最小改动）
- 优先同步生成（先做通路），单次超时后返回 `failed` 或 `pending`。
- 二期再改成后台异步任务（可复用 story 的资产生成思路）。
- 为避免重复生图，建议把结果写入 `session_meta.multimodal_cache[scenario_id]`。

### 4.7 使用既有 K/S 算法推动上下文冲突（必须项）
目标：继续用现有 K/S 状态驱动“冲突强度”，LLM 只负责“表达方式”，不接管训练流转决策。

冲突指数（`conflict_index`）建议公式（可配置）：
```python
weakness = avg(max(0.0, 1.0 - k_state.get(skill, 0.5)) for skill in target_skills)
panic = clamp01(s_state.public_panic)
safety_risk = clamp01(1.0 - s_state.source_safety)
risk_recent = clamp01(recent_risk_hits / risk_window)

conflict_index = (
    0.35 * weakness +
    0.30 * panic +
    0.20 * safety_risk +
    0.15 * risk_recent
)
```

变量说明：
- `target_skills`：来自当前场景的 `decision_focus` 或推荐策略给出的目标技能集合。
- `recent_risk_hits`：最近 N 轮（如 5 轮）中触发 `risk_flags` 的次数。
- `clamp01`：把值限制在 `[0, 1]`，避免异常输入导致过冲。

阈值分层（建议）：
- 低冲突：`conflict_index < 0.35`
- 中冲突：`0.35 <= conflict_index < 0.65`
- 高冲突：`conflict_index >= 0.65`

分层到表达策略（示例）：
- 低冲突：`emotion = calm | neutral`，context 以信息完整和核验提示为主。
- 中冲突：`emotion = tense`，context 强调时效与准确的权衡。
- 高冲突：`emotion = urgent`，context 强调风险升级与决策窗口收缩。

前端输出建议（新增在 `experience.context`）：
- `conflict_index`: `0~1` 浮点值
- `conflict_level`: `low | medium | high`
- `drivers`: 主要驱动因子列表（如 `["public_panic", "source_safety"]`）

接入顺序（关键边界）：
1. `RecommendationPolicy/FlowPolicy` 先决定“下一题是谁、走哪条训练路径”。
2. `TrainingMultimodalExperiencePolicy` 基于 `k_state/s_state/risk_flags` 计算 `conflict_index`。
3. 把 `conflict_level + drivers` 注入 LLM prompt，仅生成 `context_text/tts_text/emotion/image_prompt`。
4. TTS 根据 `emotion` 映射 `emotion_params`，生图根据 `image_prompt` 生成视觉资源。

边界约束（防止职责漂移）：
- LLM 不得决定场景跳转、评分、推荐、掌握度更新。
- LLM 输出只作用于体验层（文本、语气、画面描述），不改训练引擎状态。

默认参数建议：
- `risk_window = 5`
- `weights = {weakness: 0.35, panic: 0.30, safety_risk: 0.20, risk_recent: 0.15}`
- `thresholds = {low: 0.35, high: 0.65}`

失败降级：
- 取不到 `k_state/s_state` 时使用保守默认值（如 `0.5`）并标记 `drivers=["fallback_state"]`。
- LLM 失败时按 `conflict_level` 使用模板文本，保证主流程可用。
- TTS/生图失败时仅降级该资源，`context.text` 继续返回。

## 5. 持久化与回放（不改表结构）
- 把当轮多模态结果写入：`training_rounds.user_action["experience"]`。
- 在 `runtime_artifact_policy.py` 增加常量与提取方法（可选）：
  - `USER_ACTION_EXPERIENCE_KEY = "experience"`
  - `attach_experience_to_user_action(...)`
  - `extract_round_experience(...)`
- 优点：报告/诊断后续要回放音频和图片时可直接复用。

## 6. 关键风险与处理

### 6.1 训练独立服务静态资源问题
现状：`api/training_app.py` 未挂载 `/static/images/*` 和 `/static/audio/cache`。

影响：如果前端连的是 training-only 端口（默认 8010），可能拿到 URL 但访问不到资源。

建议最小改动：
- 抽一个 `api/static_assets.py`（公共挂载函数）。
- `api/app.py` 与 `api/training_app.py` 都调用它。

### 6.2 外部服务抖动
- LLM/生图/TTS 都设置超时与重试上限。
- 任一失败时只降级该资源，不中断训练提交。
- 记录审计事件：`multimodal_context_failed`、`multimodal_image_failed`、`multimodal_tts_failed`。

### 6.3 成本与延迟
- 增加开关：仅在 `TRAINING_ENABLE_MULTIMODAL=true` 时启用。
- 可按训练模式启用：先 `guided` 灰度，再扩到 `adaptive/self-paced`。

## 7. 文件改动清单（建议）

必改：
- `backend/training/multimodal_experience_policy.py`（新增）
- `backend/api/services/training_service.py`（接入策略，填充 `scenario.experience`）
- `backend/api/training_app.py`（挂载静态资源，或复用公共挂载函数）

建议改：
- `backend/training/runtime_artifact_policy.py`（experience 入/出 `user_action`）
- `backend/api/dependencies.py`（注入单例策略/执行器，保持与现有依赖管理一致）

测试：
- `backend/test_training_multimodal_experience_policy.py`（新增）
- `backend/test_training_service.py`（补 `next_scenario/scenario` 新字段断言）
- `backend/test_training_router.py`（验证 response model 对扩展字段兼容）

## 8. 分阶段实施建议

### Phase 1（1-2 天）
- 打通 LLM context + TTS + 图片生成（同步模式）。
- 在 `init_training/get_next_scenario` 返回 `experience`。
- 保证失败降级与主流程解耦。

### Phase 2（2-3 天）
- 改为图片异步生成（`pending -> ready`），减少首包延迟。
- `session_meta` 增加缓存，避免同场景重复生成。
- `user_action` 回放落库与诊断事件补齐。

### Phase 3（可选）
- 将多模态配置并入 `training_runtime_config.json` 与 `config_loader.py`（集中配置治理）。
- 增加成本控制策略（按用户/会话限额）。

## 9. 验收标准（DoD）
- `init` 与 `scenario/next` 响应包含 `scenario.experience`。
- 至少 1 条场景可稳定返回 `context.text + image.url + audio.url`。
- LLM、图片、TTS 任一故障时，训练主流程仍可继续。
- training-only 服务可直接访问返回的静态资源 URL。
- 单元/路由测试通过，且旧接口无破坏性回归。

---

如果要直接进入开发，建议先按 **Phase 1** 实现，我可以下一步直接给你按文件粒度输出“可执行改造清单 + 代码骨架”。
