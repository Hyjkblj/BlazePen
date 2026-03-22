# BlazePen 故事后端与训练后端详细 PR 规划总表

更新日期：2026-03-22

## 1. 文档目的

本文基于以下两份文档汇总并细化：

1. `docs/BlazePen_故事后端与训练后端拆分PR执行表.md`
2. `docs/BlazePen_故事后端与训练后端独立拆分实施清单.md`

目标不是再重复“要不要拆”，而是把每一个 PR 拆到可以直接执行、评审、验收。

本文特别增加了两类信息：

1. 当前代码状态
2. 每个 PR 的详细范围、任务、测试、风险、合并门槛

## 2. 总目标

拆分完成后，项目应满足以下状态：

1. story backend 是故事域唯一权威入口，默认端口 `8000`
2. training backend 是训练域唯一权威入口，默认端口 `8010`
3. story frontend 只连 story backend
4. training frontend 只连 training backend
5. `threadId` 只属于 story 域
6. `sessionId` 只属于 training 域
7. 两个后端入口共享基础设施，但不共享领域状态机和会话模型

## 3. 当前代码状态判断

结合当前代码基线，先给出每个 PR 的状态判断：

| PR | 目标 | 当前状态 | 判断 |
| --- | --- | --- | --- |
| `PR-BE-SPLIT-01` | 共享装配收口 | 已有 `backend/api/app_runtime.py` 和共享 `cors_config.py`，但还没有真正统一成 app factory | 部分完成 |
| `PR-BE-SPLIT-02` | training-only 入口收口 | `backend/api/training_app.py` 已独立存在，且只挂 training 路由 | 大体完成 |
| `PR-FE-SPLIT-01` | training 前端切到 `8010` | `frontend/vite.story.config.ts` 和 `frontend/vite.training.config.ts` 已分流，且有配置测试 | 基本完成 |
| `PR-FE-SPLIT-02` | training 显式 `sessionId` 路由化 | 路由构造器和 header 导航已带 `sessionId`，但 read-model 仍保留较强回退语义 | 部分完成 |
| `PR-BE-SPLIT-03` | 主后端移除 training 主入口 | `backend/api/app.py` 当前已不再挂 training.router，且有边界测试 | 基本完成 |
| `PR-BE-SPLIT-04` | story / training 领域软分层 | training 领域已有独立目录，但 story 领域尚未等价收口 | 未完成 |
| `PR-BE-SPLIT-05` | 双后端 smoke / trace / CORS / 文档收口 | 已有一部分测试和脚本，但 story/training 级别运维文档和 smoke 仍未完全对齐 | 部分完成 |

结论：

1. 入口层拆分已经开始，但还没有彻底收口
2. 真正未完成的核心工作在于 `PR-BE-SPLIT-04` 和 `PR-BE-SPLIT-05`
3. 前端还需要补完 `PR-FE-SPLIT-02`，把 `sessionId` 路由身份变成严格契约，而不是“可选显式，默认回退”

## 4. 建议执行顺序

从当前代码状态出发，建议实际执行顺序调整为：

1. 收尾 `PR-BE-SPLIT-01`
2. 收尾 `PR-FE-SPLIT-02`
3. 复核并确认 `PR-BE-SPLIT-02`
4. 复核并确认 `PR-BE-SPLIT-03`
5. 执行 `PR-BE-SPLIT-04`
6. 执行 `PR-BE-SPLIT-05`

`PR-FE-SPLIT-01` 当前只需要做回归确认，不建议再开大改。

## 5. 详细 PR 规划

## 5.1 PR-BE-SPLIT-01 共享装配收口

### 当前状态

已存在：

1. `backend/api/app_runtime.py`
2. `backend/api/cors_config.py`
3. `backend/api/app.py` 与 `backend/api/training_app.py` 都已经调用共享 trace 安装逻辑

未完成：

1. 还没有统一 app factory
2. 异常处理、startup 检查、middleware 装配仍散落在两个入口文件
3. 入口装配规范没有彻底变成单一事实源

### PR 目标

把 story backend 和 training backend 的公共装配真正收口为一套标准流程，避免后续继续分叉。

### 本 PR 必做

1. 新增 `backend/api/app_factory.py`
2. 统一封装：
   - FastAPI app 初始化
   - `install_common_exception_handlers`
   - `install_trace_context_middleware`
   - CORS middleware 安装
3. 明确 story / training 两个入口只通过参数传入：
   - title
   - description
   - service_scope
   - startup message
4. 统一 startup DB 连通性检查模式
5. 明确入口文件只做：
   - create app
   - include routers
   - 根路由和 health 路由

### 本 PR 不做

1. 不恢复 `api.app` 上的 training 路由
2. 不做 story / training 目录迁移
3. 不改 training 领域逻辑

### 涉及文件

1. `backend/api/app.py`
2. `backend/api/training_app.py`
3. `backend/api/app_runtime.py`
4. `backend/api/cors_config.py`
5. `backend/api/middleware/error_handler.py`
6. `backend/api/request_context.py`
7. 新增 `backend/api/app_factory.py`

### 代码任务拆解

1. 把共享 startup 检查逻辑提取成可复用函数
2. 把 health/root 路由生成逻辑做成轻量 helper，避免两个入口再各自手写漂移
3. 明确 story app 和 training app 的差异只保留在配置参数和路由集合
4. 保证两个入口在 response、trace、异常处理上完全一致

### 需要补的测试

1. 新增 `backend/test_api_entry_common_middleware.py`
2. 在 `backend/test_training_standalone_app.py` 中断言成功响应带 `X-Trace-Id`
3. 增加 story app 的同类断言

### 风险

1. 如果把静态资源挂载也硬塞进 app factory，story 特有逻辑会再次污染训练入口
2. 如果 startup 检查抽取方式不稳，会影响本地启动和测试 patch 点

### 合并门槛

1. `api.app` 与 `api.training_app` 成功响应都返回 `X-Trace-Id`
2. 两个入口的错误 envelope 一致
3. 两个入口的公共装配只有一处事实源

### Review 重点

1. app factory 是否真的减少分叉，而不是再包一层壳
2. training app 是否仍无 story 特有依赖
3. 静态资源和 story 特有能力是否错误下沉到 shared 层

## 5.2 PR-BE-SPLIT-02 training-only 入口收口

### 当前状态

当前已具备：

1. `backend/api/training_app.py`
2. 训练端口默认 `8010`
3. training app 只挂 `training.router`

还需确认：

1. 训练入口的文档、脚本、自检路径是否统一
2. training app 是否存在多余的 story 运行依赖

### PR 目标

让 training app 从“新增入口文件”变成“可独立部署的训练域入口”。

### 本 PR 必做

1. 统一 training app 的启动命令
2. 明确 training app 的 `health`、根路由、docs 行为
3. 统一相关脚本：
   - `backend/run_training_api.py`
   - `backend/run_training_cli.py`
   - `backend/start_training_backend.ps1`
   - `backend/start_training_experience.ps1`
4. 明确 training app 的最小依赖集合

### 本 PR 不做

1. 不移除 story backend 的 training 路由兼容层以外的内容
2. 不调整 story 业务

### 涉及文件

1. `backend/api/training_app.py`
2. `backend/run_training_api.py`
3. `backend/run_training_cli.py`
4. `backend/start_training_backend.ps1`
5. `backend/start_training_experience.ps1`
6. `backend/test_training_standalone_app.py`

### 代码任务拆解

1. 统一命令入口命名
2. 统一环境变量命名
3. 明确 training 独立运行时需要的脚本和 smoke 路径
4. 去掉 training app 内可能存在的 story 域残留说明或依赖

### 需要补的测试

1. training-only 路由 contract 测试
2. training app 启动脚本的 CLI 测试
3. 独立 app 的 health/root 文档测试

### 风险

1. 训练入口脚本过多，命名不统一，后续运维容易误用
2. 独立入口说明不清晰，前端可能仍打到错误后端

### 合并门槛

1. `8010` 单独启动可用
2. 所有训练主链接口都能通过 training app 访问
3. training app 文档说明足够明确

### Review 重点

1. training app 是否仍保持 training-only
2. 训练脚本是否和 story 脚本职责混淆
3. CLI 和 PowerShell 脚本是否形成单一启动路径

## 5.3 PR-FE-SPLIT-01 training 前端切到 8010

### 当前状态

当前已具备：

1. `frontend/vite.story.config.ts` 默认指向 `8000`
2. `frontend/vite.training.config.ts` 默认指向 `8010`
3. `frontend/vite.app.config.ts` 已支持按 env var 区分 target
4. `frontend/vite.app.config.test.ts` 已覆盖默认代理目标

### PR 目标

让 training frontend 在开发、构建和联调层面彻底脱离 story backend。

### 本 PR 必做

1. 锁定 story 端默认只走 `8000`
2. 锁定 training 端默认只走 `8010`
3. 更新 `package.json` 脚本说明
4. 更新联调文档

### 本 PR 不做

1. 不改训练页面业务流程
2. 不改 story 页面逻辑

### 涉及文件

1. `frontend/vite.app.config.ts`
2. `frontend/vite.story.config.ts`
3. `frontend/vite.training.config.ts`
4. `frontend/vite.app.config.test.ts`
5. `frontend/package.json`

### 代码任务拆解

1. 明确 story / training 两个 env var 的命名规范
2. 明确构建产物目录和命令
3. 补 README 中的双端联调说明

### 需要补的测试

1. 保留并补强 `frontend/vite.app.config.test.ts`
2. 跑 story/training 双 build

### 风险

1. 如果文档未同步，开发者仍可能手动把 training 指到 `8000`
2. 如果后端入口没彻底冻结，前端配置会反复改

### 合并门槛

1. `3000 -> 8000`
2. `3001 -> 8010`
3. 配置级测试通过

### Review 重点

1. 是否还有任何 training 默认代理回 `8000` 的残留
2. 是否出现“测试配了，dev 脚本没配”的假拆分

## 5.4 PR-FE-SPLIT-02 training 显式 sessionId 路由化

### 当前状态

当前已具备：

1. `frontend/src/config/routes.ts` 已有 `buildTrainingProgressRoute` 等构造器
2. `frontend/src/components/training/TrainingShellHeader.tsx` 已显式基于 `sessionId` 生成导航链接
3. 训练主页面已经把 `sessionId` 透传到 insight 导航

未完成点：

1. `useTrainingReadQuery` 仍保留较强的 `activeSession / resumeTarget` 回退
2. 读页面还没有完全固定为“URL sessionId 优先，其他只做兜底”
3. 多会话场景的身份一致性还需要更多测试保护

### PR 目标

让训练读模型页面稳定围绕显式 `sessionId` 运行，避免恢复身份漂移。

### 本 PR 必做

1. 固定 URL 中的 `sessionId` 为 read-model 页面第一身份来源
2. `activeSession` 和 `resumeTarget` 只保留为无 URL 时的兜底
3. 明确刷新、新标签页、复制链接场景的行为
4. 补齐页面测试

### 本 PR 不做

1. 不新增训练功能
2. 不扩展 story 主链

### 涉及文件

1. `frontend/src/pages/Training.tsx`
2. `frontend/src/config/routes.ts`
3. `frontend/src/components/training/TrainingShellHeader.tsx`
4. `frontend/src/components/training/TrainingInsightShell.tsx`
5. `frontend/src/hooks/useTrainingReadQuery.ts`
6. `frontend/src/pages/TrainingProgress.tsx`
7. `frontend/src/pages/TrainingReport.tsx`
8. `frontend/src/pages/TrainingDiagnostics.tsx`

### 代码任务拆解

1. 明确 read-query 的优先级判定函数
2. 当 URL sessionId 与本地 activeSession 冲突时，以 URL 为准
3. 保证页面之间跳转始终延续同一 `sessionId`
4. 明确 session 丢失时的空态和错误态

### 需要补的测试

1. `frontend/src/pages/Training.integration.test.tsx`
2. `frontend/src/pages/TrainingMainPathSmoke.integration.test.tsx`
3. `frontend/src/pages/TrainingInsights.integration.test.tsx`
4. `frontend/src/hooks/useTrainingReadQuery.test.tsx`

### 风险

1. 如果 URL 与缓存冲突规则不明，多标签页会串读
2. 如果继续大量依赖 fallback，会让“显式 sessionId”只停留在表层

### 合并门槛

1. insight 页面 URL 必带 `sessionId`
2. 刷新和复制链接都能稳定复现同一训练会话
3. 测试覆盖 URL 优先级、冲突、空态、错误态

### Review 重点

1. 读模型是否仍隐式依赖 localStorage
2. 页面是否还自己做身份兼容拼装
3. `sessionId` 是否已经成为训练读链路的明确契约

## 5.5 PR-BE-SPLIT-03 主后端移除 training 主入口

### 当前状态

当前已具备：

1. `backend/api/app.py` 已不再 include `training.router`
2. `backend/test_api_entrypoint_boundaries.py` 已锁定 story app 不暴露 training 路由

因此本 PR 实际上已经大体完成，后续只需要做结果确认和文档清算。

### PR 目标

结束双入口对外暴露 training 的状态。

### 本 PR 必做

1. 确认主后端不再响应 `/api/v1/training/**`
2. 清理旧文档中“训练默认走 8000”的说法
3. 清理代码和脚本中的遗留注释

### 本 PR 不做

1. 不改训练业务逻辑
2. 不改数据库层

### 涉及文件

1. `backend/api/app.py`
2. `backend/test_api_entrypoint_boundaries.py`
3. 相关 docs

### 需要补的测试

1. 继续保留入口边界测试
2. 如果有 story app API 文档快照，可增加快照校验

### 风险

1. 文档没同步，开发者仍会以为 `8000` 可直接承接 training
2. 某些外部脚本仍可能命中旧路由

### 合并门槛

1. 主后端 404 training 主路由
2. 前端联调不再依赖主后端 training 路由
3. 边界测试持续通过

### Review 重点

1. 是否真的彻底停掉双入口
2. 是否存在任何灰色兼容路径未文档化

## 5.6 PR-BE-SPLIT-04 story / training 领域软分层

### 当前状态

当前 training 领域已有较多代码位于 `backend/training/*`。

但仍存在问题：

1. story 域没有形成对等的领域目录
2. router/service/repository/policy/dto 的分层规范还没有在两边统一
3. 共享层和领域层的边界仍不够清晰

### PR 目标

从“入口拆分”推进到“领域实现拆分”，为后续长期维护和可能的拆仓库做准备。

### 本 PR 必做

1. 明确 story 域目录结构
2. 明确 training 域目录结构
3. 把 training 域整理为：
   - `routers`
   - `services`
   - `repository-store`
   - `policy`
   - `dto`
   - `async-task`
4. 把 story 域整理为：
   - `routers`
   - `services`
   - `repository-store`
   - `policy`
   - `dto`
5. 明确 shared / infra 层只保留公共能力

### 本 PR 不做

1. 不拆仓库
2. 不拆数据库
3. 不改外部 API 契约

### 涉及文件

1. `backend/api/routers/*`
2. `backend/api/services/*`
3. `backend/training/*`
4. 新增 `backend/story/*` 或同等 story 领域目录

### 代码任务拆解

1. 构建 story 域目录
2. 把 story 业务逻辑逐步迁入 story 域
3. 将 training 域内部继续按层收口
4. 建立 import 约束，禁止 story 直接 import training 领域实现
5. 建立 import 约束，禁止 training 直接 import story 领域实现

### 需要补的测试

1. 分层目录约束测试或静态扫描脚本
2. story 域回归
3. training 域回归

### 风险

1. 这是当前改动面最大的 PR，回归面会显著增大
2. 如果没有接口冻结，目录迁移很容易把业务改动混进去
3. 如果 shared 层边界不清晰，会出现“看似分层，实则继续耦合”

### 合并门槛

1. story 和 training 实现不再直接互相 import
2. shared 层不承接业务状态
3. 对外 API 不发生行为回归

### Review 重点

1. 是否真的降低耦合而不是换目录名
2. 是否把巨型 service 进一步拆清
3. 是否仍存在 `threadId / sessionId` 混用

## 5.7 PR-BE-SPLIT-05 双后端 smoke、trace、CORS、文档收口

### 当前状态

当前已有：

1. `backend/test_api_cors_config.py`
2. `backend/test_training_runner_bootstrap.py`
3. `backend/test_training_cli_entry.py`
4. `backend/test_api_entrypoint_boundaries.py`

但仍未完全收口：

1. story / training 独立 smoke 体系还不完全对称
2. story / training 启动文档和联调文档还未完全统一
3. 生产 allowlist 说明还需要正式化

### PR 目标

让 story backend 和 training backend 都具备独立启动、独立联调、独立排障和独立发布的最低运维基线。

### 本 PR 必做

1. 完成 story 与 training 双 health check 收口
2. 完成 story 与 training 双 smoke 收口
3. 完成 story 与 training 双启动脚本收口
4. 完成 `STORY_ALLOWED_ORIGINS` 与 `TRAINING_ALLOWED_ORIGINS` 文档收口
5. 完成 trace、错误上下文、启动文档、联调文档统一

### 本 PR 不做

1. 不新增业务功能
2. 不改前端页面能力

### 涉及文件

1. `backend/test_api_cors_config.py`
2. `backend/test_api_entrypoint_boundaries.py`
3. `backend/test_training_runner_bootstrap.py`
4. 相关 smoke 脚本
5. 启动脚本和 docs

### 代码任务拆解

1. 增补 story smoke
2. 明确 training smoke 的标准输出和成功条件
3. 统一 story / training 的启动说明
4. 统一生产环境 origin 变量说明
5. 补双后端联调文档

### 需要补的测试

1. story smoke
2. training smoke
3. 入口级 CORS 测试
4. 独立入口边界测试持续保留

### 风险

1. 文档滞后会让拆分后的联调成本飙升
2. smoke 只做 training 不做 story，会让 story 成为新的盲区
3. 如果 CORS 只测 helper，不测入口级行为，线上仍可能出错

### 合并门槛

1. story 与 training 都有可执行 smoke
2. story 与 training 都有明确启动方式
3. CORS 和 trace 说明与代码一致

### Review 重点

1. 是否做到了“双后端都能独立运维”
2. 是否仍依赖人工口头约定
3. 文档与代码是否一致

## 6. 推荐排期

如果按当前基线推进，推荐排期如下：

### 第一轮

1. 收尾 `PR-BE-SPLIT-01`
2. 收尾 `PR-FE-SPLIT-02`

### 第二轮

1. 复核并冻结 `PR-BE-SPLIT-02`
2. 复核并冻结 `PR-BE-SPLIT-03`

### 第三轮

1. 执行 `PR-BE-SPLIT-04`
2. 执行 `PR-BE-SPLIT-05`

## 7. 最终建议

从今天的代码状态看，入口拆分已经不是空想，已经进入“收口和定型”阶段。

真正最关键的不是继续新增入口，而是：

1. 把共享装配做成真正单一事实源
2. 把 `sessionId` 显式路由化做严
3. 把 story / training 领域实现彻底软分层
4. 把双后端 smoke 和文档补齐

如果你下一步要继续推进，优先顺序应当是：

1. `PR-BE-SPLIT-01`
2. `PR-FE-SPLIT-02`
3. `PR-BE-SPLIT-04`
4. `PR-BE-SPLIT-05`
