# BlazePen 训练/故事拆分剩余任务清单

- Date: `2026-03-22`
- Baseline: current worktree on top of `HEAD` `1794ee4`
- Source review: `docs/reviews/2026-03-22_frontend_backend_progress_review.md`

## 当前判断
- 已基本完成：
  - `PR-BE-SPLIT-01` 共享 app factory 收口
  - `PR-BE-SPLIT-02` training-only 后端入口
  - `PR-BE-SPLIT-03` story 主入口移除 training 暴露
  - `PR-FE-SPLIT-01` 前端双入口/双端口壳层
- 仍需收口：
  - `PR-FE-SPLIT-02` 训练显式 `sessionId` 读链路
  - `PR-BE-SPLIT-04` story/training 领域实现对称拆分
  - `PR-BE-SPLIT-05` 双后端运维、CORS、smoke、文档收口

## 推荐顺序
1. 先收 `PR-FE-SPLIT-02`
2. 再推 `PR-BE-SPLIT-04`
3. 最后关 `PR-BE-SPLIT-05`

## PR-FE-SPLIT-02

### 目标
- 让训练主页和 `progress / report / diagnostics` 读页统一消费同一套 `session target` 决策。
- 明确 `sessionId` 是否是训练读链路的严格契约，而不是继续保持“有 URL 就用 URL，没有 URL 再兜底”的模糊状态。

### 当前问题
- `frontend/src/pages/Training.tsx` 仍自己拼 `sessionView?.sessionId ?? resumeTarget?.sessionId`。
- 训练主页与读页没有完全复用同一套 target 解析。
- `briefing -> brief` 仍停留在 normalizer 和 API 类型层，canonical 契约还没完全定型。

### 必做任务
- 把训练主页 insight 跳转目标统一改为消费 `useTrainingSessionReadTarget` 或等价单一 selector。
- 移除训练主页自己维护的 `sessionId` fallback 拼装逻辑。
- 明确读页契约：
  - 如果目标是严格显式 `sessionId`：
    - 读页无 query `sessionId` 时直接空态，不再读取 `activeSession / resumeTarget`
  - 如果目标是显式优先但允许 fallback：
    - 在文档和测试中把这条规则固定为正式契约
- 清理 `briefing` 历史 alias：
  - 前端 API 类型不再把 `briefing` 暴露给页面消费层
  - `TrainingScenario` 只保留 `brief`
  - 页面层禁止再出现 `brief || briefing`

### 明确不做
- 不改训练提交 write-path。
- 不改训练报告视觉样式。
- 不引入新的业务字段。

### 主要文件
- `frontend/src/pages/Training.tsx`
- `frontend/src/hooks/useTrainingSessionReadTarget.ts`
- `frontend/src/hooks/useTrainingSessionViewModel.ts`
- `frontend/src/pages/TrainingProgress.tsx`
- `frontend/src/pages/TrainingReport.tsx`
- `frontend/src/pages/TrainingDiagnostics.tsx`
- `frontend/src/utils/trainingSession.ts`
- `frontend/src/types/api.ts`
- `frontend/src/types/training.ts`

### 测试补齐
- 新增或补强 `frontend/src/pages/Training.integration.test.tsx`
  - 锁定训练主页跳转时使用的 `sessionId` 与读页实际读取的 `sessionId` 一致
  - 锁定 `activeSession / resumeTarget / explicit sessionId` 冲突优先级
- 补强 `frontend/src/pages/TrainingInsights.integration.test.tsx`
  - 锁定 query `sessionId` 优先级
  - 如果保留 fallback，锁定 fallback 是正式契约
- 补强 `frontend/src/utils/trainingSession.test.ts`
  - 锁定 `brief` 为 canonical 字段

### 合并门槛
- 训练主页和 3 个读页只使用一套 `sessionId` 决策规则。
- 页面层不再消费 `briefing`。
- 相关 Vitest 全绿。

## PR-BE-SPLIT-04

### 目标
- 让 story/training 真正完成实现层对称拆分，而不是只完成入口拆分。
- 把 story 域收成与 training 对称的结构：`routers / services / repository-store / policy / dto`。

### 当前问题
- story 域虽然已有 `backend/story/*`，但仍保留 `api/services/game_service.py` 作为过渡 facade。
- `api/dependencies.py` 仍在承担较重的 story 装配责任。
- 当前还没有 import 约束，无法防止 story/training 再次互相穿透。

### 必做任务
- 定义 story 域最终目录结构，并写入实施说明。
- 继续下沉 `GameService` 的 story 逻辑：
  - router-facing facade 仅保留短期兼容职责
  - 核心业务继续迁入 `backend/story/*`
- 明确 story 域内部职责：
  - session query
  - session restore
  - turn submit
  - history read
  - ending read
  - asset/image orchestration
- 在 `api/dependencies.py` 中把 story 装配边界收紧成“组装 story bundle”，不要继续增长 router/domain 混合逻辑。
- 新增 story/training import 约束：
  - story 不能直接 import training 实现
  - training 不能直接 import story 实现
  - shared 层不承载 story/training 领域状态
- 给 `GameService` 定义退出条件：
  - 哪些方法还允许保留
  - 哪些方法迁移完成后必须删除

### 明确不做
- 不改 story/training 外部 API 契约。
- 不在这个 PR 混入 CORS、smoke、部署文档收口。
- 不做数据库层大迁移。

### 主要文件
- `backend/api/services/game_service.py`
- `backend/api/dependencies.py`
- `backend/api/routers/game.py`
- `backend/api/routers/characters.py`
- `backend/story/*`

### 测试补齐
- 新增或补强 story 域回归测试，覆盖：
  - session restore
  - turn submit
  - history
  - ending
- 新增静态边界测试或脚本，锁定 story/training 不得互相 import 实现层。
- 保持现有 `backend/test_api_entrypoint_boundaries.py` 持续通过。

### 合并门槛
- story/training 领域实现边界清晰，不再靠 `GameService` 持续吞并业务。
- `api/dependencies.py` 不再继续长成巨型领域编排器。
- story/training 互相直接依赖实现的路径被测试或脚本锁死。

## PR-BE-SPLIT-05

### 目标
- 把双后端的运维事实源收成一处。
- 完成 story/training 双入口下的 CORS、smoke、启动方式、环境变量、文档统一。

### 当前问题
- 新实现使用 `backend/api/cors_config.py` 的双 scope 设计。
- 旧配置层 `backend/config_manager.py` 仍保留单一 `ALLOWED_ORIGINS` 口径。
- 当前只有 helper 级 CORS 测试，没有入口级 CORS 行为测试。
- 有 training standalone 测试，但还缺 story 对称版本和双后端运维文档统一。

### 必做任务
- 决定旧配置口径的归宿：
  - 方案 A：`config_manager.py` 复用 `cors_config.py`
  - 方案 B：废弃旧 CORS 配置入口，统一只保留 `cors_config.py`
- 统一环境变量说明：
  - `STORY_ALLOWED_ORIGINS`
  - `TRAINING_ALLOWED_ORIGINS`
  - `ALLOWED_ORIGINS` 是否只作为共享 fallback
- 新增 story standalone 入口测试或最小 smoke。
- 新增入口级 CORS 行为测试：
  - story app
  - training app
- 统一 story/training 启动文档：
  - 本地开发启动
  - 联调端口
  - 健康检查
  - smoke 运行方式
- 补齐双后端最小 smoke 口径：
  - story smoke
  - training smoke
  - 成功条件写清楚

### 明确不做
- 不再改 story/training 领域逻辑。
- 不在此 PR 内继续做前端页面重构。

### 主要文件
- `backend/api/cors_config.py`
- `backend/config_manager.py`
- `backend/test_api_cors_config.py`
- `backend/test_training_standalone_app.py`
- 新增 story standalone/smoke 测试文件
- `.env.example`
- 相关启动与联调文档

### 测试补齐
- 入口级 CORS 行为测试
- story standalone app 测试
- story/training 双 smoke 命令或脚本验证

### 合并门槛
- CORS 配置只有一套权威语义。
- story/training 都有独立启动、独立 smoke、独立排障说明。
- 文档不再混用单后端时代的 origin 和端口口径。

## 并行建议
- 前端开发者先做 `PR-FE-SPLIT-02`。
- 后端开发者先做 `PR-BE-SPLIT-04` 的边界收口和迁移说明。
- `PR-BE-SPLIT-05` 放到 `PR-BE-SPLIT-04` 后半段或之后执行，不要和领域迁移混到同一个 PR。

## 不允许的混改
- 不要把前端 `sessionId` 规则收口和后端 DTO/CORS/部署改动混在一起。
- 不要把 story 领域迁移和运维文档/CORS 收口混在一起。
- 不要在页面层继续兼容后端历史脏字段。
- 不要让 `GameService` 长期作为 story 域权威实现继续扩张。
