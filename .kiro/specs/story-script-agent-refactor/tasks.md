# 实现计划：StoryScriptAgent 结构重构

## 概述

按六个独立步骤组织实现任务，每步可独立合并、独立回滚，不破坏现有 API 契约。
旧方法 `ensure_script_for_session` 在兼容期内保留，新会话使用 `fill_scenario_narratives`。

## Tasks

- [x] 1. 定义 v2 Pydantic 模型与工具函数
  - [x] 1.1 在 `story_script_agent.py` 中新增 v2 Pydantic 模型
    - 新增 `ScriptNarrativeLine(BaseModel)`：`speaker: str`、`content: str`
    - 新增 `ScriptNarrativeOptionItem(BaseModel)`：`option_id: str`、`narrative_label: str`、`impact_hint: str = ""`
    - 新增 `ScriptNarrative(BaseModel)`：`monologue: str`、`dialogue: List[ScriptNarrativeLine]`、`bridge_summary: str`、`options_narrative: Dict[str, ScriptNarrativeOptionItem]`
    - 新增 `TrainingStoryScriptV2Payload(BaseModel)`：`version: str = "training_story_script_v2"`、`cast: List[Dict[str, str]]`、`narratives: Dict[str, ScriptNarrative]`、`fallback_used: bool = False`、`generated_at: str = ""`
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 1.2 新增 `resolve_narrative_for_scenario` 工具函数
    - 函数签名：`resolve_narrative_for_scenario(payload: Dict[str, Any], scenario_id: str) -> Dict[str, Any]`
    - `version == "training_story_script_v2"` 时从 `payload["narratives"][scenario_id]` 读取
    - `version == "training_story_script_v1"` 或无 version 时，使用 `_legacy_match_scene` 按 `major_scene_order` + `micro_scene_order` 字段做前缀匹配
    - 找不到时返回空字典，不抛出异常
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ]* 1.3 为 v2 模型编写属性测试（Property A）
    - **Property A: v2 payload round-trip 不变性**
    - **Validates: Requirements 3.5**
    - 使用 `@given` 生成任意合法 v2 payload，验证序列化后反序列化结果等价

  - [ ]* 1.4 为 `resolve_narrative_for_scenario` 编写属性测试（Property C）
    - **Property C: resolve_narrative_for_scenario 不抛出异常**
    - **Validates: Requirements 5.4**
    - 使用 `@given` 生成任意 payload（含空字典、v1、v2、格式错误）和任意 scenario_id，验证不抛出异常

- [x] 2. 新增 `StoryScriptAgent.fill_scenario_narratives` 方法
  - [x] 2.1 实现 `fill_scenario_narratives` 主方法骨架
    - 方法签名：`fill_scenario_narratives(self, *, session_id, scenario_payload_sequence, player_profile=None, allow_llm=True) -> Dict[str, Any]`
    - 记录 `session_id` 和场景数量的 info 日志（Requirements 8.1）
    - `scenario_payload_sequence` 为空时记录 error 日志并返回空 v2 payload
    - `allow_llm=True` 时调用 `_fill_by_llm`，失败时降级到 `_fill_by_fallback`
    - `allow_llm=False` 时直接调用 `_fill_by_fallback`
    - 返回 v2 格式 payload，调用 `_store_v2_payload` 持久化
    - _Requirements: 1.1, 1.7, 8.1_

  - [x] 2.2 实现 `_fill_by_llm` 方法（LLM 内容填充路径）
    - 构建新版 prompt：明确传入完整 `scenario_payload_sequence`（含 `id`、`title`、`brief`、`mission`）
    - prompt 明确指示 LLM 不得修改 `scenario_id` 和 `title`，只填充 `monologue`、`dialogue`、`bridge_summary`、`options_narrative`
    - prompt 要求 LLM 输出以 `scenario_id` 为 key 的 `narratives` 字典（v2 schema）
    - 最多重试 2 次，失败时调用 JSON 修复流程（复用现有 `_repair_to_strict_json` 逻辑）
    - LLM 输出缺少某个 `scenario_id` 时，对该场景使用 fallback 内容并记录 warning（Requirements 2.4, 8.4）
    - 所有重试均失败时抛出异常，由调用方降级到 `_fill_by_fallback`
    - _Requirements: 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 8.2_

  - [x] 2.3 实现 `_fill_by_fallback` 方法（本地确定性降级路径）
    - 为 `scenario_payload_sequence` 中的每一个场景生成确定性叙事内容
    - 使用场景的 `title`、`brief`、`location` 字段作为内容种子
    - 生成 6 行固定角色对话（复用现有 `mk_dialogue` 逻辑，但绑定到 scenario 的 title）
    - 生成 3 个选项的叙事台词（复用现有 `mk_options` 逻辑）
    - 在返回的 payload 中标记 `fallback_used: true`
    - 记录 warning 日志（Requirements 8.3）
    - _Requirements: 1.7, 8.3_

  - [x] 2.4 实现 `_store_v2_payload` 方法（持久化）
    - 检查 `TrainingStoryScript` 表中是否已有该 session 的记录
    - 已有记录时调用 `update_story_script_by_session_id` 更新 payload
    - 无记录时调用 `create_story_script` 创建新记录，`version` 字段写入 `"training_story_script_v2"`
    - _Requirements: 3.4_

  - [ ]* 2.5 为 `fill_scenario_narratives` 编写属性测试（Property B、D）
    - **Property B: fill_scenario_narratives 不修改结构字段**
    - **Validates: Requirements 1.3, 1.4**
    - 使用 `@given` 生成任意 scenario_payload_sequence，验证 id/title/brief/mission/options 字段不变
    - **Property D: fallback 覆盖所有场景**
    - **Validates: Requirements 1.7**
    - 使用 `@given` 生成任意 scenario_payload_sequence，mock LLM 不可用，验证每个场景都有非空叙事内容

- [x] 3. 标注旧方法 deprecation
  - [x] 3.1 在 `ensure_script_for_session` 方法上添加 deprecation 注释
    - 在 docstring 中添加 `[DEPRECATED] 使用 fill_scenario_narratives 替代。兼容期内保留，不立即删除。`
    - 不修改方法逻辑，不删除方法
    - _Requirements: 7.1, 7.2_

- [x] 4. 升级 `TrainingStoryScriptExecutor`
  - [x] 4.1 修改 `_generate` 方法：传完整序列并调用新方法
    - 将 `major_scene_sources = snapshot_bundle.scenario_payload_sequence[:6]` 替换为 `full_sequence = list(snapshot_bundle.scenario_payload_sequence or [])`
    - `full_sequence` 为空时记录 error 日志，调用 `update_story_script_by_session_id` 将状态标记为 `failed`，并 return
    - 将 `agent.ensure_script_for_session(...)` 替换为 `agent.fill_scenario_narratives(session_id=session_id, scenario_payload_sequence=full_sequence, player_profile=player_profile, allow_llm=True)`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 5. 前端消费层适配
  - [x] 5.1 在前端新增 `resolveNarrativeForScenario` 工具函数
    - 函数签名：`resolveNarrativeForScenario(payload: unknown, scenarioId: string): ScriptNarrative | null`
    - `payload.version === "training_story_script_v2"` 时从 `payload.narratives[scenarioId]` 读取
    - 其他情况使用旧版 `scenes[].scene_id` 查找逻辑（v1 兼容）
    - 找不到时返回 `null`，不抛出运行时错误
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 5.2 更新前端消费叙事内容的组件
    - 将直接访问 `scenes[index]` 的地方替换为调用 `resolveNarrativeForScenario(payload, scenarioId)`
    - 返回 `null` 时渲染空白叙事内容占位
    - _Requirements: 6.3, 6.4_

- [x] 6. 单元测试补齐
  - [ ]* 6.1 为 `fill_scenario_narratives` 编写单元测试
    - 验证 `allow_llm=False` 时直接走 fallback 路径（Requirements 1.7）
    - 验证 LLM 失败时降级到 fallback，payload 中 `fallback_used=true`（Requirements 1.7）
    - 验证 `scenario_payload_sequence` 为空时返回空 v2 payload 且不抛出异常
    - 验证生成结果以 v2 格式写入 store（Requirements 3.4）

  - [ ]* 6.2 为 `TrainingStoryScriptExecutor` 编写单元测试
    - 验证 `scenario_payload_sequence` 为空时状态标记为 `failed`（Requirements 4.3）
    - 验证调用 `fill_scenario_narratives` 而非 `ensure_script_for_session`（Requirements 4.2）

  - [ ]* 6.3 为 `resolve_narrative_for_scenario` 编写单元测试
    - 验证 v2 payload 按 scenario_id 正确读取（Requirements 5.2）
    - 验证 v1 payload 按 scene_id 前缀匹配正确读取（Requirements 5.3）
    - 验证 scenario_id 不存在时返回空字典（Requirements 5.4）

  - [ ]* 6.4 为前端 `resolveNarrativeForScenario` 编写单元测试
    - 验证 v2 payload 按 scenarioId 正确读取（Requirements 6.1）
    - 验证 v1 payload 走旧版查找逻辑（Requirements 6.2）
    - 验证找不到时返回 null（Requirements 6.4）

## Notes

- 标记 `*` 的子任务为可选测试任务，可跳过以加快 MVP 进度
- 每个子任务引用具体需求条款以保证可追溯性
- 属性测试使用 Hypothesis，每个属性最少运行 100 次（`@settings(max_examples=100)`）
- 旧方法 `ensure_script_for_session` 在兼容期内保留，不删除
- 前端任务（Task 5）依赖后端 Task 1-4 完成后再开始
- Task 3（deprecation 标注）可与 Task 2 同步进行，不存在依赖关系
