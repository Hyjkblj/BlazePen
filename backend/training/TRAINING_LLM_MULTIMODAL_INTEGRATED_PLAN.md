# Training LLM 治理 + 多模态接入整合方案（最小改动版）

## 1. 目标
- 在不改数据库表结构的前提下，为 training 链路接入 `LLM 上下文文本 + 生图 + TTS 情绪语音`。
- 保持现有训练决策主链路稳定：`Recommendation/Flow/DecisionContext` 继续由 K/S 算法主导。
- 把当前大模型方案的治理风险（暴露面、超时、观测）一起收敛，做到可灰度、可回滚、可审计。

## 2. 当前现状（评估结论）
- LLM 已接入，但主要用于回合评估融合，不参与“下一题选择”决策。
- 默认配置下 `use_llm_eval=false`，当前线上默认偏规则链路。
- 评估链路有降级：`rules_only -> rules_fallback -> llm_plus_rules`，鲁棒性基础较好。
- 主要风险：
  - `llm_raw_text` 透传到输出 DTO/API，存在信息暴露面。
  - 有重试，但缺全链路预算超时与熔断策略。
  - 审计缺少 LLM 关键观测维度（provider/model/latency/tokens/fallback_rate）。
  - 多模态仍处于文档态，尚未落地到 `training_service` 主流程。

## 3. 总体原则（整合后）
1. 算法决策边界不动：场景流转与评分更新仍由 K/S + 规则引擎决定。
2. LLM 只做表达层：生成上下文文案、情绪标签、图片提示词，不改训练状态。
3. 多模态失败不阻塞训练主流程：任一子能力失败都回退到文本兜底。
4. 最小改动优先：优先复用 `user_action/session_meta/extra_fields`，避免 schema 破坏。
5. 先治理后扩展：先做 P0 风险收敛，再做体验增强。

## 4. 一体化目标架构
- 决策层（保持现状）：
  - `recommendation_policy.py` / `round_flow_policy.py` / `decision_context_policy.py`
- 评估层（治理增强）：
  - `evaluator.py` + `llm/base.py` + `telemetry_policy.py`
- 体验层（新增）：
  - `multimodal_experience_policy.py`（新增）
  - `training_service.py`（仅在 `init_training/get_next_scenario` 接入）
- 资源层（复用）：
  - `ImageService`、`TTSService`
- 回放层（可选增强）：
  - `runtime_artifact_policy.py` 扩展 `experience` 工件写回与提取

## 5. 整合方案（按优先级）

### P0（必须先做，风险收敛）
1. 关闭 `llm_raw_text` 默认外露
- 目标：响应默认不返回原始模型文本，仅调试开关可见。
- 最小改动建议：
  - 在 `TrainingEvaluationOutput.to_dict()` 增加条件输出（默认隐藏）。
  - 或在 `TrainingService` 出参组装前做字段剔除。
  - 增加配置：`TRAINING_EXPOSE_LLM_RAW_TEXT=false`（默认）。

2. 增加 LLM 调用“总超时预算 + 快速降级”
- 目标：外部抖动时不拖慢提交链路，超时即 `rules_fallback`。
- 最小改动建议：
  - `evaluator.py` 为 `_evaluate_by_llm` 增加耗时守卫（如 6~8 秒预算）。
  - `llm` provider 统一支持超时配置（OpenAI 补显式 timeout 参数）。
  - 超时/失败统一打 `fallback_reason`。

3. 确保 training-only 可访问静态资源
- 目标：`experience.image/audio` URL 在 8010 端口可直接访问。
- 最小改动建议：
  - 抽公共挂载函数 `api/static_assets.py`。
  - `api/app.py` 与 `api/training_app.py` 统一复用。

### P1（推荐，能力增强）
1. 落地 `TrainingMultimodalExperiencePolicy`（新增）
- 输入：`session/scenario_payload/round_no/k_state/s_state/recent_risk_rounds`
- 输出：`experience`（context/image/audio + status/error）
- 集成点：
  - `init_training()` 返回 `next_scenario` 前
  - `get_next_scenario()` 返回 `scenario` 前

2. 落地 KS 驱动冲突指数（Conflict Index）
- 公式（可配置）：
  - `conflict_index = 0.35*weakness + 0.30*panic + 0.20*safety_risk + 0.15*risk_recent`
- 分层：
  - `low <0.35`，`medium 0.35~0.65`，`high >=0.65`
- 用法：
  - 只注入 LLM prompt 影响表达（`context_text/tts_text/emotion/image_prompt`）
  - 不反向修改推荐与流转决策

3. 观测补齐（审计可追踪）
- 在 `telemetry_policy.py` 的 round 事件中补充：
  - `llm_provider`、`llm_model`、`llm_latency_ms`、`llm_usage`、`eval_mode`、`fallback_reason`
- 用于后续成本与稳定性分析。

### P2（体验优化）
1. 图片/TTS 异步化
- 首包返回 `pending`，完成后 `ready`（可轮询 next/summary）。
- 降低首包延迟，避免同步阻塞。

2. 多模态缓存
- `session_meta.multimodal_cache[scenario_id]` 缓存已生成资源，避免重复调用。

3. 回放工件标准化（可选）
- `user_action["experience"]` 持久化每轮体验工件。
- `runtime_artifact_policy.py` 增加 attach/extract 方法。

## 6. 统一数据契约（前端）
- 注入位置：
  - `init`: `data.next_scenario.experience`
  - `next`: `data.scenario.experience`

```json
{
  "experience": {
    "version": "v1",
    "context": {
      "text": "夜色下消息冲突加剧，你需要在时效与核验之间做选择。",
      "tts_text": "夜色下消息冲突加剧，你需要在时效与核验之间做选择。",
      "emotion": "tense",
      "conflict_index": 0.61,
      "conflict_level": "medium",
      "drivers": ["public_panic", "source_safety"],
      "source": "llm",
      "model": "xxx"
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

状态机统一：`ready | pending | failed`

## 7. 失败降级矩阵
- LLM 文本失败：使用模板文本（按 conflict_level 选模板），主流程继续。
- 生图失败：`image.status=failed`，仅文本+音频返回。
- TTS 失败：`audio.status=failed`，仅文本+图片返回。
- 多能力同时失败：仍返回 `context.text`（最低可用体验）。

## 8. 计划排期（建议）
- Day 1-2（P0）：
  - `llm_raw_text` 隐藏
  - LLM 超时预算/快速降级
  - training-only 静态资源挂载统一
- Day 3-4（P1）：
  - 新增 `multimodal_experience_policy.py`
  - `training_service` 两处接入 experience
  - KS 冲突指数驱动 prompt/emotion
  - 审计字段补齐
- Day 5+（P2）：
  - 异步化 + 缓存 + 回放工件标准化

## 9. 最小改动文件清单
- 新增：
  - `backend/training/multimodal_experience_policy.py`
  - `backend/api/static_assets.py`（建议）
- 修改：
  - `backend/api/services/training_service.py`
  - `backend/training/evaluator.py`
  - `backend/training/telemetry_policy.py`
  - `backend/training/training_outputs.py`（评估字段脱敏策略）
  - `backend/api/training_app.py`
  - `backend/api/app.py`（调用公共静态挂载）
  - `backend/training/runtime_artifact_policy.py`（可选）

## 10. 验收标准（DoD）
- `init/next` 均返回 `scenario.experience`，前端可直接渲染。
- LLM、生图、TTS 任一失败不影响 `submit_round` 与主链路稳定。
- 训练决策边界不变：推荐/流转仍由 K/S 算法驱动。
- `llm_raw_text` 默认不对外暴露。
- 审计可看到 LLM 基础观测指标并统计 fallback 率。
- 8010 training-only 端口可访问图片与音频静态 URL。

