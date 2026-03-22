# BlazePen 前端状态职责与命名基线

- 适用范围: `frontend/`
- 对应规划: `PR-01 基线治理与命名规范`
- 更新日期: `2026-03-19`

## 1. 术语与命名

- 故事主线会话统一使用 `threadId`。
- 训练主线会话统一使用 `sessionId`。
- 角色统一使用 `characterId`。
- 场景统一使用 `sceneId`。
- 训练回合统一使用 `roundNo`。
- 训练运行态统一使用 `runtimeState`。

页面、flow、hook、context 不允许直接消费后端 snake_case 会话字段。后端历史字段兼容只允许在 `services/` 与 normalizer 中收口。
训练场景正文对页面层只暴露 `brief`，不再把 `briefing` 作为前端可消费契约继续扩散。

## 2. 前端状态分层

### 2.1 入口流程状态

- 载体: `src/contexts/GameFlowContext.tsx`
- 责任:
  - 角色草稿
  - 当前激活故事会话入口信息
  - 恢复入口信息
- 不负责:
  - 游戏页运行时对话列表
  - 提交中的瞬时状态
  - 资源加载失败标记

### 2.2 页面运行时状态

- 载体: `src/hooks/useGameState.ts`
- 责任:
  - 当前对白
  - 当前选项
  - 当前场景展示
  - 过场动画和加载态
  - 资源降级后的页面显示状态
- 不负责:
  - 角色创建草稿
  - 跨页面入口恢复决策
  - 原始后端 DTO 解析

### 2.3 服务端会话镜像状态

- 载体: `src/services/gameApi.ts` 返回的标准化结果
- 责任:
  - 会话初始化结果
  - 故事回合提交结果
  - 会话恢复标记
- 约束:
  - flow 只消费 camelCase 结果
  - 会话恢复语义优先由 service 层翻译后再暴露给 flow

### 2.4 训练读链路目标选择

- 载体:
  - `src/hooks/useTrainingSessionReadTarget.ts`
  - `src/hooks/useTrainingSessionViewModel.ts`
- 正式优先级:
  - 显式 `sessionId`
  - 当前内存 `activeSession`
  - 本地 `resumeTarget`
- 约束:
  - 训练主页的 insight 入口与 `progress / report / diagnostics` 读页必须复用同一套 target selector
  - 页面层不允许再手工拼 `sessionId` fallback
  - 本地 `resumeTarget` 只作为 UX 恢复入口，不提升为服务端事实源

### 2.5 本地缓存状态

- 载体: `src/storage/gameStorage.ts`
- 责任:
  - UX 层草稿缓存
  - 游戏页恢复辅助快照
- 不负责:
  - 充当服务端会话单一事实源
  - 承载后端恢复语义判断

## 3. 分层职责

### 3.1 `pages/`

- 负责页面容器、路由级组织和组件拼装。
- 不负责复杂业务编排和后端响应结构适配。

### 3.2 `flows/`

- 负责页面级流程编排。
- 可以组合 `hooks / services / contexts`。
- 不允许直接处理 raw snake_case 字段或 message 文本业务判断。

### 3.3 `hooks/`

- 负责可复用交互逻辑和页面局部状态。
- 不同时承担接口适配、缓存兼容、路由跳转、恢复判定全部职责。

### 3.4 `services/`

- 负责 HTTP 请求、DTO 适配、错误模型收口。
- 负责将后端兼容字段映射为前端稳定模型。

### 3.5 `storage/`

- 负责浏览器本地存取和兼容读取。
- 不直接暴露给页面层做多处拼装。

### 3.6 `contexts/`

- 只承载跨页面、稳定、低频变化的流程态。
- 不承载游戏页的完整运行时细节。

## 4. 路由拆分原则

### 4.1 故事主线

- 当前主线页面:
  - `Home`
  - `FirstStep`
  - `CharacterSetting`
  - `CharacterSelection`
  - `FirstMeetingSelection`
  - `Game`
- 会话标识只认 `threadId`。

### 4.2 训练主线

- 后续新增训练页面时必须单独建路由簇。
- 会话标识只认 `sessionId`。
- 不允许复用故事主线的运行时 state、恢复逻辑和存储 key。

## 5. 本次基线要求

- 页面与 flow 不直接依赖后端 message 文本判断业务分支。
- 角色接口与故事接口在 service 边界内区分归属。
- 本地缓存只作为恢复辅助，不作为服务端会话事实源。
- 任何新增前端状态前，先判断是否可由现有状态推导。
