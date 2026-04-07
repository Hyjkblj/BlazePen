# 需求文档

## 简介

本功能将训练页面（`frontend/src/pages/Training.tsx`）从"训练工具界面"重构为"嵌入式评估的互动叙事体验"。

核心设计原则：**系统信息必须伪装为故事的一部分。用户应主动想要放慢节奏，而非被迫等待。**

交互流程分为七个叙事阶段，依次为：独白（Phase 1）→ 对话（Phase 2）→ 决策停顿（Phase 3）→ 选项（Phase 4）→ 后果叙事（Phase 5）→ 过渡桥接（Phase 6）→ 进度（Phase 7）。

技术背景：
- 前端：React + TypeScript
- `resolveNarrativeForScenario` 工具函数已存在于 `frontend/src/utils/trainingSession.ts`
- `ScriptNarrative` 类型已定义于 `frontend/src/types/training.ts`
- 当前训练页面：`frontend/src/pages/Training.tsx`

---

## 词汇表

- **Training_Page**：训练页面，`frontend/src/pages/Training.tsx`。
- **TrainingMvpFlow**：训练主流程 hook，`frontend/src/flows/useTrainingMvpFlow.ts`。
- **ScriptNarrative**：单个场景的叙事内容类型，包含 `monologue`、`dialogue`、`bridge_summary`、`options_narrative` 字段，定义于 `frontend/src/types/training.ts`。
- **Narrative_Resolver**：`resolveNarrativeForScenario` 工具函数，根据 `scenarioId` 从 StoryScriptPayload 中解析 ScriptNarrative。
- **Monologue_Phase**：Phase 1，打字机独白阶段，展示 `ScriptNarrative.monologue`。
- **Dialogue_Phase**：Phase 2，逐行对话阶段，展示 `ScriptNarrative.dialogue[]`。
- **Decision_Pause_Phase**：Phase 3，决策前心理停顿阶段，展示过渡提示语。
- **Choice_Phase**：Phase 4，选项展示阶段，展示带叙事标签的选项。
- **Consequence_Phase**：Phase 5，选择后叙事化反馈阶段，将评估数据转化为叙事句子。
- **Bridge_Phase**：Phase 6，场景过渡桥接阶段，展示 `bridge_summary` 作为氛围文字。
- **Progress_Phase**：Phase 7，进度指示阶段，以最小化方式展示轮次信息。
- **ChoiceBand**：选项卡组件（`TrainingCinematicChoiceBand`），展示当前场景的可选项。
- **SceneTransition**：大场景切换动画组件。
- **NarrativeLabel**：选项的叙事标签，来源于 `ScriptNarrative.options_narrative[optionId].narrative_label`。
- **ImpactHint**：选项的影响提示文本，来源于 `ScriptNarrative.options_narrative[optionId].impact_hint`。

---

## 需求

### 需求 1：Phase 1 — 独白（叙事进入）

**用户故事：** 作为训练学员，我希望场景以沉浸式独白开场，以便自然进入叙事情境，而非感觉在阅读系统说明。

#### 验收标准

1. WHEN 场景加载完成且 `ScriptNarrative.monologue` 非空时，THE Training_Page SHALL 以打字机效果逐字展示 `monologue` 文本，字符间隔为 32ms。
2. WHEN `ScriptNarrative.monologue` 为空或 ScriptNarrative 不可用时，THE Training_Page SHALL 回退到使用 `brief` 与 `mission` 字段拼接叙事文本，保持现有行为。
3. THE Training_Page SHALL 将 `monologue` 文本按句子分段展示，每段之间保留视觉停顿，而非将全部文本作为一个连续块输出。
4. WHEN 用户在打字机效果进行中点击叙事区域时，THE Training_Page SHALL 立即完成当前段落的全部文字展示（跳过打字机动画），而非跳转到下一阶段。
5. WHEN 打字机效果已完成且用户再次点击叙事区域时，THE Training_Page SHALL 进入 Dialogue_Phase。
6. THE Training_Page SHALL 在 ScriptNarrative 解析失败时不抛出运行时错误，回退到现有叙事渲染逻辑。

### 需求 2：Phase 2 — 对话（对话展开）

**用户故事：** 作为训练学员，我希望对话内容逐行揭示，以便感受到真实对话的节奏感，而非一次性看到所有台词。

#### 验收标准

1. WHEN `ScriptNarrative.dialogue` 列表非空时，THE Training_Page SHALL 在 Monologue_Phase 完成后进入 Dialogue_Phase，逐行展示对话内容。
2. THE Training_Page SHALL 每次仅展示一行对话，用户点击后展示下一行，或在 2 秒后自动展示下一行。
3. THE Training_Page SHALL 最多展示 `dialogue` 列表中的前 6 行，超出部分截断不展示。
4. WHEN `ScriptNarrative.dialogue` 列表为空时，THE Training_Page SHALL 跳过 Dialogue_Phase，直接进入 Decision_Pause_Phase。
5. THE Training_Page SHALL 在任意时刻允许用户点击跳过剩余对话行，直接进入 Decision_Pause_Phase。

### 需求 3：Phase 3 — 决策停顿（决策前心理停顿）

**用户故事：** 作为训练学员，我希望在选项出现前有一个短暂的停顿提示，以便感受到决策的分量，而非选项突然弹出。

#### 验收标准

1. WHEN Dialogue_Phase 完成（或被跳过）后，THE Training_Page SHALL 展示一条决策提示语，持续 1.5 秒后自动进入 Choice_Phase。
2. THE Training_Page SHALL 从以下提示语中选取展示："你需要做出决定了。"或"现在，你会怎么做？"或同等语气的短句。
3. WHEN 用户在决策停顿期间点击任意位置时，THE Training_Page SHALL 立即跳过停顿，进入 Choice_Phase。

### 需求 4：Phase 4 — 选项（选项设计）

**用户故事：** 作为训练学员，我希望选项同时展示功能性标签和叙事性标签，以便在理解选项含义的同时保持沉浸感。

#### 验收标准

1. THE ChoiceBand SHALL 为每个选项展示主文本（原始 `label`）和副文本（`NarrativeLabel`）两层内容。
2. WHEN `ScriptNarrative.options_narrative` 中存在与选项 `id` 匹配的条目时，THE ChoiceBand SHALL 将该条目的 `narrative_label` 作为副文本展示。
3. WHEN `options_narrative` 中不存在与选项 `id` 匹配的条目，或 ScriptNarrative 不可用时，THE ChoiceBand SHALL 仅展示原始 `label`，不展示副文本区域。
4. THE ChoiceBand SHALL 在 ScriptNarrative 不可用时保持选项功能完整，不影响用户提交选择。

### 需求 5：Phase 5 — 后果叙事（选择后叙事化反馈）

**用户故事：** 作为训练学员，我希望选择后看到叙事化的后果描述，以便理解决策影响，而非看到原始数字和系统标记。

#### 验收标准

1. WHEN 用户选择一个选项后，THE Training_Page SHALL 在进入下一场景前展示 Consequence_Phase，以叙事句子呈现评估结果。
2. WHEN `ImpactHint` 非空时，THE Training_Page SHALL 将其转化为叙事句子展示，例如将"消息扩散"转化为"你按下了发送键。几分钟后，消息迅速扩散。"
3. WHEN `TrainingEvaluation.riskFlags` 非空时，THE Training_Page SHALL 将每条风险标记转化为后果描述句子展示，例如"⚠ 一些未经核实的信息引发了公众恐慌。"
4. WHEN `TrainingEvaluation.skillDelta` 中存在绝对值大于 0.05 的变化项时，THE Training_Page SHALL 以故事化语言隐性提示技能变化，例如"编辑对你的信任有所提升。"
5. WHEN `TrainingEvaluation.skillDelta` 中所有变化项的绝对值均不超过 0.05 时，THE Training_Page SHALL 不展示技能变化提示。
6. THE Training_Page SHALL 不以原始数值格式展示 `skillDelta`（例如禁止展示"核实能力 +0.05"或"skill_delta: +0.05"等形式）。
7. WHEN `ImpactHint` 为空且 `riskFlags` 为空且无显著 `skillDelta` 时，THE Training_Page SHALL 跳过 Consequence_Phase，直接进入下一场景。
8. THE Training_Page SHALL 在 Consequence_Phase 展示 3 秒后自动进入下一场景。
9. WHEN 用户在 Consequence_Phase 展示期间点击任意位置时，THE Training_Page SHALL 立即进入下一场景。

### 需求 6：Phase 6 — 过渡桥接（场景过渡）

**用户故事：** 作为训练学员，我希望大场景切换时看到氛围性过渡文字，以便感受到时间流逝和场景转换，而非突然跳入新场景。

#### 验收标准

1. WHEN 发生大场景切换（`majorSceneId` 变化）且 `ScriptNarrative.bridge_summary` 非空时，THE SceneTransition SHALL 将 `bridge_summary` 以氛围文字形式展示，语气为时间流逝感，例如"时间过去了几个小时……"风格。
2. THE SceneTransition SHALL 不将 `bridge_summary` 作为摘要或总结展示，而是作为叙事氛围文字融入过渡动画。
3. WHEN `bridge_summary` 为空或 ScriptNarrative 不可用时，THE SceneTransition SHALL 仅展示现有的场景名称与幕次动画，不展示额外文字区域。
4. WHEN 非大场景切换（`majorSceneId` 未变化）时，THE Training_Page SHALL 不展示 Bridge_Phase，仅使用现有的场景淡入淡出动画。

### 需求 7：Phase 7 — 进度（进度系统）

**用户故事：** 作为训练学员，我希望以最小化方式感知训练进度，以便不被系统感打断叙事沉浸，同时了解关键后果。

#### 验收标准

1. THE Training_Page SHALL 以小型不显眼元素展示当前轮次信息，格式为"第 N 轮 / 共 M 轮"，不占据主视觉区域。
2. WHEN 总轮次不可用时，THE Training_Page SHALL 仅展示当前轮次编号，格式为"第 N 轮"。
3. THE Training_Page SHALL 在正常流程中不展示任何技能数值（包括 `skillDelta` 的具体数字）。
4. WHEN `TrainingConsequenceEvent` 中存在严重程度为 `critical` 的事件时，THE Training_Page SHALL 以叙事事件形式展示，例如将 `sourceExposed` 标记展示为"⚠ 来源暴露"故事节拍，而非系统标记。
5. THE Training_Page SHALL 不在进度区域展示原始 `riskFlags` 数组内容或 `skillDelta` 数值。

### 需求 8：反模式禁止

**用户故事：** 作为产品设计者，我希望明确禁止三类破坏叙事体验的反模式，以便确保实现符合"互动叙事体验"而非"训练工具界面"的设计原则。

#### 验收标准

1. THE Training_Page SHALL 在所有打字机阶段允许用户随时点击跳过或加速，不存在任何无法跳过的强制等待打字机动画。
2. THE Training_Page SHALL 不将 `dialogue` 列表全部内容一次性渲染到 DOM 中，对话内容必须逐行揭示。
3. THE Training_Page SHALL 不以原始数据格式向用户展示任何系统内部字段，包括但不限于：`skill_delta` 数值、`risk_flags` 数组、`impact_hint` 原文、`bridge_summary` 原文。
4. IF Training_Page 在任意阶段出现无法通过用户交互退出的等待状态，THEN THE Training_Page SHALL 在等待超过 5 秒后自动推进到下一阶段。

### 需求 9：叙事内容获取与降级

**用户故事：** 作为训练学员，我希望叙事内容加载失败时训练流程仍能正常进行，以便不因内容获取问题中断体验。

#### 验收标准

1. THE TrainingMvpFlow SHALL 在训练会话初始化完成后，异步获取当前会话的 StoryScriptPayload，不阻塞主流程。
2. WHEN StoryScriptPayload 获取成功时，THE TrainingMvpFlow SHALL 将 payload 存储在会话状态中，供 Training_Page 各阶段使用。
3. WHEN StoryScriptPayload 获取失败时，THE TrainingMvpFlow SHALL 将叙事内容置为不可用状态，Training_Page 回退到现有的 `brief + mission` 叙事渲染逻辑，不向用户展示错误提示。
4. THE TrainingMvpFlow SHALL 在场景切换时复用已缓存的 StoryScriptPayload，不重复发起网络请求。
5. WHEN StoryScriptPayload 的状态为 `pending` 或 `running` 时，THE TrainingMvpFlow SHALL 在 3 秒后重试一次获取，最多重试 2 次。
6. THE Training_Page SHALL 在 ScriptNarrative 任意字段缺失或类型不符时，对该字段单独降级处理，不影响其他字段的正常展示。
