# BlazePen 训练前端独立端口与故事主线复原任务清单

更新日期：2026-03-22

## 1. 目标

本文按以下假设制定任务清单：

1. “训练独立出来新开一个端口”指的是：训练前端不再作为故事前端中的一组路由存在，而是成为同仓库内的独立前端应用。
2. “将对故事的影响复原”指的是：训练拆出后，故事主线前端回到独立运行、独立路由、独立状态、独立恢复模型，不再被训练页面、训练 Provider、训练存储和训练路由污染。

建议目标端口：

1. 故事前端：`3000`
2. 训练前端：`3001`
3. 后端：`8000`

## 2. 完成定义

满足以下条件后，才算完成本任务：

1. 故事前端和训练前端可以分别单独启动、单独访问、单独构建。
2. 故事前端不再注册训练路由，不再挂载训练专用 Provider。
3. 训练前端不再复用 story runtime hook、story session store、story restore 逻辑。
4. story 只使用 `threadId`，training 只使用 `sessionId`。
5. 故事主线 smoke 回归通过，训练主线 smoke 回归通过。
6. 两个前端共享的仅是基础组件、通用工具和通用 HTTP 基础设施，不共享业务状态。

## 3. 目标结构

建议采用“同仓库双前端应用 + 共享基础层”的结构，而不是继续在一个 `App.tsx` 里混挂 story 与 training：

```text
frontend/
  apps/
    story/
      index.html
      main.tsx
      AppStory.tsx
      router/
    training/
      index.html
      main.tsx
      AppTraining.tsx
      router/
  src/
    shared/
      components/
      services/
      utils/
      config/
    story/
      pages/
      flows/
      hooks/
      services/
      storage/
      contexts/
    training/
      pages/
      flows/
      hooks/
      services/
      storage/
      contexts/
```

如果当前阶段不想一次性搬目录，也至少要先做到：

1. `AppStory.tsx` 与 `AppTraining.tsx` 分离。
2. `StoryRouter` 与 `TrainingRouter` 分离。
3. `vite.story.config.ts` 与 `vite.training.config.ts` 分离。

## 4. 实施原则

1. 先稳故事，再拆训练。不能一边拆壳一边继续改故事业务。
2. 先拆入口和 Provider，再拆业务目录。不要反过来。
3. 训练前端不能再通过故事上下文“顺手拿状态”。
4. localStorage 只能做跨应用启动提示，不得做 story/training 会话事实源。
5. 端口分离后，跨应用只走显式契约，不走隐式内存共享。

## 5. 任务清单

### 阶段 A：冻结现状与验收基线

- [ ] 固化故事前端当前 smoke 基线。
  - 目标：保证拆训练前后，故事主线可回归对比。
  - 文件：
    - `frontend/src/pages/MainPathSmoke.integration.test.tsx`
    - `frontend/src/hooks/useStoryTurnSubmission.test.tsx`
    - `frontend/src/hooks/useGameInit.ts`
- [ ] 固化训练前端当前 smoke 基线。
  - 目标：拆壳后训练页最小主流程仍可验证。
  - 文件：
    - `frontend/src/pages/Training.integration.test.tsx`
    - `frontend/src/pages/TrainingInsights.integration.test.tsx`
    - `frontend/src/hooks/useTrainingSessionBootstrap.test.tsx`
- [ ] 记录当前 story/training 共享入口。
  - 当前耦合点至少包括：
    - `frontend/src/App.tsx`
    - `frontend/src/router/index.tsx`
    - `frontend/src/contexts/index.ts`

### 阶段 B：拆前端入口与端口

- [ ] 为故事前端创建独立入口。
  - 新增建议：
    - `frontend/apps/story/main.tsx`
    - `frontend/apps/story/AppStory.tsx`
    - `frontend/apps/story/index.html`
- [ ] 为训练前端创建独立入口。
  - 新增建议：
    - `frontend/apps/training/main.tsx`
    - `frontend/apps/training/AppTraining.tsx`
    - `frontend/apps/training/index.html`
- [ ] 新增双 Vite 配置。
  - 新增建议：
    - `frontend/vite.story.config.ts`
    - `frontend/vite.training.config.ts`
  - 端口：
    - story: `3000`
    - training: `3001`
- [ ] 更新 `package.json` 脚本。
  - 建议新增：
    - `dev:story`
    - `dev:training`
    - `dev:all`
    - `build:story`
    - `build:training`
- [ ] 明确 Electron 只先挂 story 端口。
  - 第一阶段不要把 training 一起塞回 Electron dev 流程。
  - 先保证 `electron:dev` 仍只依赖 story app。

### 阶段 C：拆 Router 与 Provider

- [ ] 从根 `App.tsx` 移除 story/training 混挂。
  - 当前问题：
    - `frontend/src/App.tsx` 同时挂了 `GameFlowProvider` 和 `TrainingFlowProvider`。
  - 目标：
    - story app 只挂 story 需要的 Provider。
    - training app 只挂 training 需要的 Provider。
- [ ] 拆分故事路由。
  - 当前问题：
    - `frontend/src/router/index.tsx` 同时注册 `Game`、`Training`、`TrainingProgress`、`TrainingReport`、`TrainingDiagnostics`。
  - 目标：
    - `StoryRouter` 只保留故事和角色创建链路。
- [ ] 拆分训练路由。
  - 目标：
    - `TrainingRouter` 只承载 `Training`、`TrainingProgress`、`TrainingReport`、`TrainingDiagnostics`。
- [ ] 故事和训练分别挂自己的错误边界。
  - 不再使用一个全局根级边界吞掉全部业务域。

### 阶段 D：恢复故事主线不受训练污染

- [ ] 把训练从故事首页导航和故事页面导航逻辑中剥离。
  - 目标：故事前端回到“只服务故事主线”的产品形态。
- [ ] 把故事恢复链路从训练耦合里清理出来。
  - 检查点：
    - `frontend/src/hooks/useGameInit.ts`
    - `frontend/src/hooks/useStoryTurnSubmission.ts`
    - `frontend/src/flows/useGameSessionFlow.ts`
- [ ] 把故事状态事实源固定为 story runtime。
  - 规则：
    - story 只认 `threadId`
    - 训练的 `sessionId` 不得进入 story app
- [ ] 确认故事存储键不再被训练入口读取或写入。
  - 检查：
    - `frontend/src/storage/gameStorage.ts`
    - `frontend/src/storage/storySessionCache.ts`
- [ ] 故事 smoke 回归必须通过后，才允许继续移动训练页面。

### 阶段 E：训练前端独立化

- [ ] 把训练页面迁移到训练应用目录。
  - 文件：
    - `frontend/src/pages/Training.tsx`
    - `frontend/src/pages/TrainingProgress.tsx`
    - `frontend/src/pages/TrainingReport.tsx`
    - `frontend/src/pages/TrainingDiagnostics.tsx`
- [ ] 把训练 flow、hook、context 明确收口到 training 域。
  - 文件：
    - `frontend/src/flows/useTrainingMvpFlow.ts`
    - `frontend/src/hooks/useTrainingSessionBootstrap.ts`
    - `frontend/src/hooks/useTrainingRoundRunner.ts`
    - `frontend/src/contexts/TrainingFlowContext.tsx`
    - `frontend/src/contexts/trainingFlowCore.ts`
- [ ] 把训练服务与类型入口切到 training 域。
  - 文件：
    - `frontend/src/services/trainingApi.ts`
    - `frontend/src/types/training.ts`
    - `frontend/src/utils/trainingSession.ts`
- [ ] 训练应用不再引用 story runtime hook。
  - 禁止复用：
    - `useGameInit`
    - `useStoryTurnSubmission`
    - `GameFlowContext`
    - story storage

### 阶段 F：定义跨应用显式契约

- [ ] 定义 story -> training 的启动契约。
  - 推荐最小字段：
    - `characterId`
    - 可选 `name`
    - 可选 `entrySource`
  - 不要直接传 `threadId`。
- [ ] 定义 training -> story 的返回契约。
  - 如果训练完成后要回故事前端，只允许传：
    - `characterId`
    - 可选 `trainingSessionId`
    - 可选 `trainingCompleted=true`
- [ ] 决定跨应用参数载体。
  - 推荐优先级：
    1. URL query
    2. 后端读取接口
    3. 本地缓存仅作启动 hint
- [ ] 禁止跨应用共享 live session。
  - story 不能恢复 training session。
  - training 不能恢复 story thread。

### 阶段 G：共享层收口

- [ ] 识别真正可共享的基础层。
  - 可共享：
    - HTTP client
    - 通用按钮/壳层组件
    - logger
    - telemetry 基础设施
    - routes builder 工具
  - 不可共享：
    - story flow/hook/context
    - training flow/hook/context
    - story session storage
    - training session storage
- [ ] 从现有 `src` 中抽出 shared 层。
  - 建议位置：
    - `frontend/src/shared/components`
    - `frontend/src/shared/services`
    - `frontend/src/shared/utils`
- [ ] 清理 story/training 双向 import。
  - 验收标准：
    - story 目录不 import training 业务文件
    - training 目录不 import story 业务文件

### 阶段 H：构建、联调与发布链路

- [ ] 为 story 和 training 分别输出构建产物。
  - 不能继续默认只有一个 `dist` 概念。
- [ ] 明确本地联调方式。
  - story: `http://localhost:3000`
  - training: `http://localhost:3001`
  - backend: `http://localhost:8000`
- [ ] 明确反向代理与静态资源策略。
  - 两个前端都应能代理 `/api`、`/health`、`/static`。
- [ ] 如果后续要接 Nginx 或 Electron，再单独做壳层整合，不在本任务里混做。

## 6. 推荐 PR 拆分

### PR-FE-SP-01：双入口与双端口基线

- 范围：
  - 独立入口
  - 独立 Vite 配置
  - 独立 npm scripts
- 不做：
  - 不搬业务目录
  - 不改 story/training 业务逻辑

### PR-FE-SP-02：Story Router/Provider 复原

- 范围：
  - `AppStory`
  - `StoryRouter`
  - story Provider 收口
- 不做：
  - 不迁训练页面

### PR-FE-SP-03：Training Router/Provider 独立

- 范围：
  - `AppTraining`
  - `TrainingRouter`
  - training Provider 收口
- 不做：
  - 不触 story runtime

### PR-FE-SP-04：跨应用启动契约

- 范围：
  - story -> training launch
  - training -> story return
  - query 参数/后端读取契约
- 不做：
  - 不共用 live session

### PR-FE-SP-05：共享层抽取与 import 清理

- 范围：
  - shared components/services/utils
  - 双向 import 清理
- 不做：
  - 不新增业务功能

### PR-FE-SP-06：回归与构建收口

- 范围：
  - smoke
  - build
  - README/dev docs
  - 端口说明

## 7. 测试清单

### 故事前端

- [ ] story 入口可单独启动。
- [ ] 角色创建 -> 场景选择 -> 游戏初始化 -> 回合提交 主链路 smoke 通过。
- [ ] 故事恢复、ending、history 不受 training 拆出影响。
- [ ] 故事前端运行时不再加载 training route。

### 训练前端

- [ ] training 入口可单独启动。
- [ ] 训练初始化 -> 提交回合 -> 进度/报告/诊断读取 主链路 smoke 通过。
- [ ] training app 不引用 `threadId`。
- [ ] training app 刷新后只通过 `sessionId` 恢复。

### 架构保护

- [ ] ESLint/脚本检查 story 不 import training 业务目录。
- [ ] ESLint/脚本检查 training 不 import story 业务目录。
- [ ] 测试覆盖跨应用启动参数解析与异常路径。

## 8. 风险点

1. 如果只拆端口，不拆 Provider 和 Router，最后仍然是“物理分端口、逻辑不分域”。
2. 如果继续让 localStorage 承担跨应用事实源，story/training 会再次形成双事实源。
3. 如果 training app 继续复用 story hook，后续任何 story 改动都会回灌训练前端。
4. 如果先搬目录再补 smoke，故事主线很容易在拆壳过程中回归失守。

## 9. 建议执行顺序

1. 先做 `PR-FE-SP-01`，把双入口和双端口立住。
2. 再做 `PR-FE-SP-02`，先把故事主线复原成独立 app。
3. 再做 `PR-FE-SP-03`，把训练前端迁到独立 app。
4. 然后做 `PR-FE-SP-04`，补跨应用显式契约。
5. 最后做 `PR-FE-SP-05` 和 `PR-FE-SP-06`，收共享层和测试/构建。

## 10. 最终验收口径

最终你应该能得到两个前端：

1. 一个只负责 story 的前端应用。
2. 一个只负责 training 的前端应用。

并且两者满足：

1. story 不再被 training 路由、Provider、状态、恢复逻辑污染。
2. training 不再建立在 story runtime 复用之上。
3. 两者通过显式契约协作，而不是通过隐式共享状态“碰巧能跑”。
