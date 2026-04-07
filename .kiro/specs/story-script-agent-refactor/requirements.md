# 需求文档

## 简介

本功能对 `StoryScriptAgent` 进行结构重构，解决叙事层与训练层之间的"双结构源"问题。

当前 `StoryScriptAgent` 同时承担"定义结构"（决定场景数量、scene_id、顺序）和"填充内容"（生成独白、对话、选项台词）两件事，导致叙事层自行维护一套 `major-1 / micro-1-1` ID 体系，与训练层 `SessionStorylinePolicy` 生成的 `scenario_payload_sequence` ID 体系不一致，叙事内容无法精确对应训练场景。

重构后，`StoryScriptAgent` 只负责内容填充，结构由训练层唯一定义并以 `scenario_payload_sequence` 的形式传入。

**前置条件：**
- Phase 1 已完成，场景结构已统一为 6 major + 18 micro = 24 个场景
- `session_snapshot_policy` 已实现，`scenario_payload_sequence` 在会话创建时已冻结

---

## 词汇表

- **StoryScriptAgent**：叙事内容填充代理，负责为训练场景生成独白、对话、选项台词等叙事内容
- **SessionStorylinePolicy**：训练层场景结构策略，负责生成并冻结完整的 `scenario_payload_sequence`
- **TrainingStoryScriptExecutor**：后台执行器，负责调度 `StoryScriptAgent` 的生成任务
- **scenario_payload_sequence**：训练层冻结的完整场景序列，包含 major 和 micro 场景，每个场景含 `id`、`title`、`brief`、`mission` 等结构字段
- **scenario_id**：训练层场景的唯一标识符，格式如 `{major_id}` 或 `{major_id}_micro_{major_index}_{micro_index}_{storyline_suffix}`
- **Narrative**：叙事内容，包含 `monologue`（独白）、`dialogue`（对话列表）、`bridge_summary`（承接摘要）、`options_narrative`（选项台词）
- **v1 payload**：旧版剧本存储格式，使用 `scenes` 数组，`scene_id` 为 `major-1 / micro-1-1` 格式
- **v2 payload**：新版剧本存储格式，使用 `narratives` 字典，key 直接为训练层 `scenario_id`
- **TrainingStoryScript**：数据库表，存储每个训练会话的剧本 payload
- **fallback**：LLM 不可用时的本地确定性降级生成路径

---

## 需求

### 需求 1：StoryScriptAgent 新增内容填充方法

**用户故事：** 作为训练系统，我希望 StoryScriptAgent 能接收训练层已冻结的完整场景序列并为每个场景填充叙事内容，以便叙事内容与训练场景精确对应。

#### 验收标准

1. THE StoryScriptAgent SHALL 提供 `fill_scenario_narratives` 方法，接受 `session_id`、`scenario_payload_sequence`、`player_profile`、`allow_llm` 四个参数
2. WHEN `fill_scenario_narratives` 被调用时，THE StoryScriptAgent SHALL 为 `scenario_payload_sequence` 中的每一个场景填充 `monologue`、`dialogue`、`bridge_summary`、`options_narrative` 字段
3. THE StoryScriptAgent SHALL 不修改输入 `scenario_payload_sequence` 中的 `id`、`title`、`brief`、`mission`、`options` 等结构字段
4. THE StoryScriptAgent SHALL 不自行决定场景数量、场景顺序或 `scenario_id` 命名
5. WHEN `fill_scenario_narratives` 被调用时，THE StoryScriptAgent SHALL 将 `scenario_id` 原样传入 LLM prompt，要求 LLM 按 `scenario_id` 索引输出叙事内容，不允许 LLM 自行命名场景 ID
6. WHEN LLM 返回的 JSON 无法解析或未通过 schema 校验时，THE StoryScriptAgent SHALL 最多重试 2 次，并在重试时调用 JSON 修复流程
7. IF 所有 LLM 调用均失败，THEN THE StoryScriptAgent SHALL 使用本地确定性 fallback 路径生成叙事内容，并在 payload 中标记 `fallback_used: true`

---

### 需求 2：LLM Prompt 语义从"生成结构"改为"填充内容"

**用户故事：** 作为开发者，我希望 LLM prompt 明确告知模型只填充叙事内容而不定义结构，以便生成结果与训练层场景结构严格对齐。

#### 验收标准

1. THE StoryScriptAgent SHALL 在 prompt 中明确传入完整的 `scenario_payload_sequence`（含 `id`、`title`、`brief`、`mission`）
2. THE StoryScriptAgent SHALL 在 prompt 中明确指示 LLM 不得修改 `scenario_id` 和 `title`，只填充 `monologue`、`dialogue`、`bridge_summary`、`options_narrative`
3. THE StoryScriptAgent SHALL 在 prompt 中要求 LLM 输出以 `scenario_id` 为 key 的 `narratives` 字典，而非 `scenes` 数组
4. WHEN LLM 输出的 `narratives` 字典中缺少某个 `scenario_id` 时，THE StoryScriptAgent SHALL 对该场景使用 fallback 内容填充，并记录警告日志

---

### 需求 3：v2 payload 格式定义

**用户故事：** 作为系统，我希望新版剧本 payload 使用 `scenario_id` 作为 key 的字典结构，以便消费方能通过 `scenario_id` 直接查找叙事内容，消除 ID 不统一问题。

#### 验收标准

1. THE System SHALL 定义 v2 payload 格式，包含 `version: "training_story_script_v2"` 字段和 `narratives` 字典
2. THE System SHALL 定义 `narratives` 字典的 schema：key 为 `scenario_id`（字符串），value 包含 `monologue`（字符串）、`dialogue`（对话列表）、`bridge_summary`（字符串）、`options_narrative`（字典）
3. THE System SHALL 使用 Pydantic 模型对 v2 payload 进行 schema 校验
4. WHEN 新会话的剧本被生成时，THE System SHALL 以 v2 格式写入 `TrainingStoryScript` 表
5. FOR ALL 合法的 v2 payload，将其序列化为 JSON 后再反序列化，SHALL 得到等价的 payload 对象（round-trip 属性）

---

### 需求 4：TrainingStoryScriptExecutor 调用方升级

**用户故事：** 作为训练系统，我希望 TrainingStoryScriptExecutor 传入完整的 `scenario_payload_sequence`（含 major + micro）并调用新方法，以便叙事生成能覆盖所有 24 个场景。

#### 验收标准

1. THE TrainingStoryScriptExecutor SHALL 从 `session_snapshot_policy` 获取完整的 `scenario_payload_sequence`，包含 major 和 micro 场景
2. THE TrainingStoryScriptExecutor SHALL 调用 `StoryScriptAgent.fill_scenario_narratives` 而非旧方法 `ensure_script_for_session`
3. WHEN `scenario_payload_sequence` 为空或无法获取时，THE TrainingStoryScriptExecutor SHALL 记录错误日志并将该会话的剧本状态标记为 `failed`
4. THE TrainingStoryScriptExecutor SHALL 在调用新方法后，将生成结果以 v2 格式更新到 `TrainingStoryScript` 表

---

### 需求 5：双版本 payload 兼容读取

**用户故事：** 作为系统，我希望在兼容期内能同时读取 v1 和 v2 格式的 payload，以便旧会话的剧本不受影响。

#### 验收标准

1. THE System SHALL 提供 `resolve_narrative_for_scenario(payload, scenario_id)` 工具函数，根据 `version` 字段自动选择读取路径
2. WHEN `payload.version == "training_story_script_v2"` 时，THE System SHALL 从 `payload.narratives[scenario_id]` 读取叙事内容
3. WHEN `payload.version == "training_story_script_v1"` 或 `version` 字段缺失时，THE System SHALL 使用旧版 `scene_id` 前缀匹配逻辑读取叙事内容
4. IF `scenario_id` 在 payload 中不存在，THEN THE System SHALL 返回空字典，不抛出异常
5. THE System SHALL 保留旧方法 `ensure_script_for_session` 在兼容期内可调用，不立即删除

---

### 需求 6：前端消费层适配

**用户故事：** 作为前端，我希望能通过 `scenario_id` 直接查找叙事内容，以便前端渲染逻辑与训练层场景 ID 保持一致。

#### 验收标准

1. THE Frontend SHALL 从 `payload.narratives[scenario_id]` 读取叙事内容，当 `payload.version == "training_story_script_v2"` 时
2. WHEN `payload.version == "training_story_script_v1"` 时，THE Frontend SHALL 继续使用旧版 `scenes[].scene_id` 查找逻辑，保证旧会话正常渲染
3. THE Frontend SHALL 不依赖 `scenes` 数组的顺序索引来定位叙事内容，改为按 `scenario_id` 键值查找
4. IF `narratives[scenario_id]` 不存在，THEN THE Frontend SHALL 渲染空白叙事内容占位，不抛出运行时错误

---

### 需求 7：旧方法兼容期与清理策略

**用户故事：** 作为开发者，我希望旧方法在兼容期内保持可用，并在兼容期结束后有明确的清理路径，以便平滑迁移。

#### 验收标准

1. THE System SHALL 在兼容期内保留 `StoryScriptAgent.ensure_script_for_session` 方法，并在方法上添加 deprecation 注释
2. THE System SHALL 在兼容期内保留 v1 payload 的读取路径，不强制迁移旧会话数据
3. WHEN 兼容期结束时，THE System SHALL 能够安全删除 `ensure_script_for_session` 方法和 v1 兼容读取路径，且不影响新会话的正常运行
4. THE System SHALL 通过 `version` 字段区分 v1 和 v2 payload，不依赖其他字段推断版本

---

### 需求 8：日志与可观测性

**用户故事：** 作为运维人员，我希望剧本生成过程有足够的日志，以便在生成失败时快速定位问题。

#### 验收标准

1. WHEN `fill_scenario_narratives` 开始执行时，THE StoryScriptAgent SHALL 记录 `session_id` 和 `scenario_payload_sequence` 的场景数量
2. WHEN LLM 调用失败或 JSON 解析失败时，THE StoryScriptAgent SHALL 记录 warning 级别日志，包含 `session_id`、`attempt` 编号和错误信息
3. WHEN fallback 路径被触发时，THE StoryScriptAgent SHALL 记录 warning 级别日志，包含 `session_id` 和触发原因
4. WHEN 某个 `scenario_id` 的叙事内容缺失时，THE StoryScriptAgent SHALL 记录 warning 级别日志，包含 `session_id` 和缺失的 `scenario_id`
