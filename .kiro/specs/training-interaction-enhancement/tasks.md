# 实现计划：训练交互增强（training-interaction-enhancement）

## 概述

按七个独立步骤组织实现任务，每步可独立合并、独立回滚，不破坏现有训练流程。
所有新功能在 ScriptNarrative 不可用时均降级到现有 brief+mission 行为。

## Tasks

- [x] 1. narrativeConsequenceBuilder 工具函数
  - [x] 1.1 新建 `frontend/src/utils/narrativeConsequenceBuilder.ts`
    - 实现 `buildNarrativeConsequence(input: NarrativeConsequenceInput): string[]`
    - `impactHint` 非空时包装为叙事句子
    - `riskFlags` 每条映射到后果描述（含 fallback 模板）
    - `skillDelta` 中 `|delta| > 0.05` 的项映射到隐性提示句子
    - 三者均为空/零时返回 `[]`
    - 输出字符串中禁止出现原始数值格式（如 `+0.05`）或原始字段名
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 1.2 为 `narrativeConsequenceBuilder` 编写属性测试（Property 8、9、10）
    - **Property 8: skillDelta 阈值规则**
    - **Property 9: 系统数据不以原始格式展示**
    - **Property 10: 后果叙事空值跳过**
    - 使用 fast-check，每个属性最少运行 100 次
    - _Requirements: 5.4, 5.5, 5.6, 5.7_

- [x] 2. useStoryScriptPayload hook
  - [x] 2.1 新建 `frontend/src/hooks/useStoryScriptPayload.ts`
    - 实现 `useStoryScriptPayload(sessionId: string | null | undefined): UseStoryScriptPayloadResult`
    - 同一 `sessionId` 只请求一次，结果缓存在 `useRef` 中
    - 状态为 `pending` 或 `running` 时，3 秒后重试，最多重试 2 次
    - 请求失败时 `status` 设为 `unavailable`，`payload` 为 `null`
    - 不阻塞主流程，异步获取
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 2.2 为 `useStoryScriptPayload` 编写属性测试（Property 14）
    - **Property 14: StoryScriptPayload 缓存不重复请求**
    - _Requirements: 9.4_

- [x] 3. useNarrativePhaseEngine hook
  - [x] 3.1 新建 `frontend/src/hooks/useNarrativePhaseEngine.ts`
    - 实现 7 阶段状态机：`monologue → dialogue → decision_pause → choice → consequence → bridge`
    - `monologue` 文本按句号/换行分段，段间 300ms 停顿
    - 决策停顿提示语池随机选取
    - 每个阶段设置 5 秒安全超时自动推进
    - `decision_pause` 固定 1.5 秒后自动推进
    - `consequence` 固定 3 秒后自动推进
    - ScriptNarrative 不可用时跳过 Phase 1–3，直接进入 `choice`
    - 暴露 `advance()` 和 `skipToChoice()` 方法
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 2.1, 2.2, 2.4, 2.5, 3.1, 3.2, 3.3, 8.4_

  - [ ]* 3.2 为 `useNarrativePhaseEngine` 编写属性测试（Property 5、6、13）
    - **Property 5: 对话行截断（最多 6 行）**
    - **Property 6: 对话逐行揭示**
    - **Property 13: 5 秒安全超时**
    - _Requirements: 2.3, 2.2, 8.4_

- [x] 4. NarrativeConsequenceView 组件
  - [x] 4.1 新建 `frontend/src/components/training/NarrativeConsequenceView.tsx`
    - 接受 `lines: string[]` 和 `onClick: () => void` props
    - 叙事句子逐行淡入展示
    - 点击任意位置触发 `onClick`
    - 底部展示"点击继续"提示
    - _Requirements: 5.1, 5.8, 5.9_

  - [x] 4.2 在 `Training.css` 中新增 Phase 5 相关样式
    - `.training-consequence-view`、`.training-consequence-view__line`
    - 遵循现有暖色调设计语言
    - _Requirements: 5.1_

- [x] 5. TrainingCinematicChoiceBand — 新增叙事副标签
  - [x] 5.1 修改 `frontend/src/components/training/TrainingCinematicChoiceBand.tsx`
    - 新增 `narrativeLabels?: Record<string, string>` prop
    - 当 `narrativeLabels[option.id]` 存在时渲染副文本 `<span class="...option-narrative">`
    - 不存在时不渲染副文本 DOM 元素
    - 不影响现有选项功能和样式
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 5.2 为 `TrainingCinematicChoiceBand` 编写属性测试（Property 7）
    - **Property 7: 选项叙事标签渲染**
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 6. SceneTransition — 新增 bridge_summary 槽
  - [x] 6.1 修改 `frontend/src/components/SceneTransition.tsx`
    - 新增 `bridgeSummary?: string | null` prop
    - `bridgeSummary` 非空时在场景名称下方渲染 `<p class="scene-transition-bridge">`
    - 为空或 null 时不渲染额外元素
    - 不影响现有场景名称和幕次展示逻辑
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 6.2 为 `SceneTransition` 编写属性测试（Property 11）
    - **Property 11: bridge_summary 渲染与降级**
    - _Requirements: 6.1, 6.3_

- [x] 7. Training.tsx — 集成阶段引擎
  - [x] 7.1 集成 `useStoryScriptPayload` 和 `useNarrativePhaseEngine`
    - 引入 `useStoryScriptPayload(sessionView?.sessionId)` 获取 payload
    - 引入 `useNarrativePhaseEngine` 替换现有 `choiceStage` 状态机
    - 将 `phaseEngine.state.phase` 作为渲染判断依据
    - _Requirements: 1.1, 2.1, 3.1, 9.1_

  - [x] 7.2 接入 Phase 1–3 叙事渲染
    - Phase 1（monologue）：打字机展示当前分段，点击跳过/加速
    - Phase 2（dialogue）：逐行展示对话，点击推进
    - Phase 3（decision_pause）：展示决策提示语
    - 在 `Training.css` 中新增 `.training-narrative-phase` 相关样式
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 2.1, 2.2, 2.5, 3.1, 3.3_

  - [x] 7.3 接入 Phase 4 叙事副标签
    - 从 `ScriptNarrative.options_narrative` 构建 `narrativeLabels` 映射
    - 传入 `TrainingCinematicChoiceBand`
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 7.4 接入 Phase 5 后果叙事
    - 选项提交后，等待评估结果，构建 `consequenceLines`
    - 渲染 `NarrativeConsequenceView`
    - 点击或 3 秒后进入下一场景
    - _Requirements: 5.1, 5.8, 5.9_

  - [x] 7.5 接入 Phase 6 过渡桥接
    - 大场景切换时将上一场景的 `bridge_summary` 传入 `SceneTransition`
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 7.6 新增 ProgressBadge（Phase 7）
    - 新建 `frontend/src/components/training/ProgressBadge.tsx`
    - 展示"第 N 轮 / 共 M 轮"或"第 N 轮"
    - 小型不显眼样式，不占主视觉区域
    - 不展示任何技能数值
    - _Requirements: 7.1, 7.2, 7.3_

## Notes

- 标记 `*` 的子任务为可选测试任务，可跳过以加快 MVP 进度
- 属性测试使用 fast-check，每个属性最少运行 100 次（`{ numRuns: 100 }`）
- 每个属性测试注释格式：`// Feature: training-interaction-enhancement, Property N: <描述>`
- Task 1–6 相互独立，可并行开发；Task 7 依赖 Task 1–6 全部完成
- 所有新功能在 ScriptNarrative 不可用时必须降级到现有行为，不破坏现有训练流程
- CSS 遵循现有暖色调（`#2f2014`、`rgba(255,255,255,0.9)`）和圆角（`border-radius: 16px`）设计语言
