# BlazePen 故事后端与训练后端拆分 PR 执行表

更新日期：2026-03-22

## 1. 执行目标

本表用于把“故事后端与训练后端独立拆分”从架构目标落到可执行 PR。

执行结果必须达到：

1. story backend 成为故事域唯一权威入口
2. training backend 成为训练域唯一权威入口
3. story 前端只连 `8000`
4. training 前端只连 `8010`
5. `threadId` 与 `sessionId` 不再跨域混用

## 2. 总体顺序

按以下顺序推进，不建议打乱：

1. `PR-BE-SPLIT-01` 共享装配收口
2. `PR-BE-SPLIT-02` training-only 入口收口
3. `PR-FE-SPLIT-01` training 前端切到 `8010`
4. `PR-FE-SPLIT-02` training 显式 `sessionId` 路由化
5. `PR-BE-SPLIT-03` 主后端移除 training 主入口
6. `PR-BE-SPLIT-04` story / training 领域软分层
7. `PR-BE-SPLIT-05` 双后端 smoke、trace、CORS、文档收口

## 3. 后端 PR

## 3.1 PR-BE-SPLIT-01 共享装配收口

### 目标

把 `api.app` 与 `api.training_app` 的公共装配逻辑统一，结束中间件栈漂移。

### 必做范围

1. 抽出共享 app factory 或 installer
2. 统一安装 trace middleware
3. 统一安装异常处理器
4. 统一安装 CORS middleware
5. 明确 story / training 入口各自只传入自己的 service scope

### 主要文件

1. `backend/api/app.py`
2. `backend/api/training_app.py`
3. `backend/api/cors_config.py`
4. `backend/api/request_context.py`
5. `backend/api/middleware/error_handler.py`
6. 新增 `backend/api/app_factory.py`

### 明确不做

1. 不移除 `api.app` 上的 training 路由
2. 不做目录大迁移
3. 不改训练业务逻辑

### 合并门槛

1. `api.app` 与 `api.training_app` 成功响应都返回 `X-Trace-Id`
2. story 与 training 两个入口的 error envelope 完全一致
3. 入口级单测能锁定公共中间件已生效

### 必补测试

1. `backend/test_training_standalone_app.py` 增加 `X-Trace-Id` 断言
2. 新增 `backend/test_api_entry_common_middleware.py`

## 3.2 PR-BE-SPLIT-02 training-only 入口收口

### 目标

让 `backend/api/training_app.py` 明确成为训练域权威入口。

### 必做范围

1. `training_app.py` 只挂 training 路由
2. 明确 training app 是否需要静态资源挂载
3. 明确 training app 的 `/health`、`/docs`、根路径响应
4. 统一 training app 的启动方式和环境变量

### 主要文件

1. `backend/api/training_app.py`
2. `backend/run_training_api.py`
3. `backend/start_training_backend.ps1`
4. `backend/test_training_standalone_app.py`

### 明确不做

1. 不从主后端移除 training 路由
2. 不修改 story 路由

### 合并门槛

1. `8010` 单独启动可用
2. `init / next / submit / progress / report / diagnostics` 均可通过 training app 访问
3. training app 的 trace、错误码、CORS 均与主装配基线一致

### 必补测试

1. 扩展 `backend/test_training_standalone_app.py`
2. 新增 training-only 入口级 contract test

## 3.3 PR-BE-SPLIT-03 主后端移除 training 主入口

### 目标

结束 `api.app` 与 `api.training_app` 同时对外暴露训练域能力的状态。

### 必做范围

1. 从 `backend/api/app.py` 移除 `training.router`
2. 如果要保留兼容层，必须是显式短期兼容，不允许长期双入口
3. 更新所有文档和本地启动说明

### 主要文件

1. `backend/api/app.py`
2. `backend/api/routers/training.py`
3. `backend/run_training_api.py`
4. 相关 docs

### 明确不做

1. 不调整 training service 内部实现
2. 不做数据库层改造

### 合并门槛

1. 主后端不再响应 training 主路由
2. training 前端联调全部走 `8010`
3. 文档中不再出现“训练默认走 8000”的说明

### 必补测试

1. 新增 `backend/test_story_app_entry.py`
2. 锁定主后端不再响应 `/api/v1/training/**`

## 3.4 PR-BE-SPLIT-04 story / training 领域软分层

### 目标

把 story 与 training 从“入口分离”推进到“领域实现分离”。

### 必做范围

1. 建立 story 领域目录边界
2. 建立 training 领域目录边界
3. 训练域按 `routers / services / repository-store / policy / dto / async-task` 收口
4. story 域按 `routers / services / repository-store / policy / dto` 收口
5. 清理 story import training、training import story 的直接依赖

### 主要文件

1. `backend/api/routers/*`
2. `backend/api/services/*`
3. `backend/training/*`
4. 新增 `backend/story/*` 或同等 story 领域目录

### 明确不做

1. 不拆仓库
2. 不拆数据库
3. 不改对外 API 契约

### 合并门槛

1. story 和 training 领域实现不再直接互相引用
2. 公共逻辑仅保留在 shared / infra 层
3. 对外 API 契约不发生回归

### 必补测试

1. 目录依赖约束检查
2. story / training 回归测试各自通过

## 3.5 PR-BE-SPLIT-05 双后端 smoke 与运维收口

### 目标

让两个后端都具备独立可运行、可诊断、可发布的最低基线。

### 必做范围

1. story 与 training 各自具备 health check
2. story 与 training 各自具备 smoke
3. story 与 training 各自具备启动脚本
4. story 与 training 各自具备 CORS allowlist 说明
5. 完成 trace、错误上下文、部署文档收口

### 主要文件

1. `backend/start_training_backend.ps1`
2. story backend 启动脚本
3. `backend/test_api_cors_config.py`
4. smoke 相关脚本和测试
5. 相关 docs

### 明确不做

1. 不做新的业务功能
2. 不扩展前端页面

### 合并门槛

1. story 与 training 两条 smoke 都能单独通过
2. 生产环境 origin 配置说明明确
3. 本地启动文档、联调文档和部署文档一致

### 必补测试

1. story smoke
2. training smoke
3. 入口级 CORS 测试

## 4. 前端 PR

## 4.1 PR-FE-SPLIT-01 training 前端切到 8010

### 目标

让训练前端真正脱离 story backend。

### 必做范围

1. story 和 training 使用不同 API target
2. `vite.story.config.ts` 指向 `8000`
3. `vite.training.config.ts` 指向 `8010`
4. 本地开发脚本明确 story / training 双端口联调方式

### 主要文件

1. `frontend/vite.app.config.ts`
2. `frontend/vite.story.config.ts`
3. `frontend/vite.training.config.ts`
4. `frontend/package.json`

### 明确不做

1. 不改训练页面业务交互
2. 不改 story 页面逻辑

### 合并门槛

1. `3000 -> 8000`
2. `3001 -> 8010`
3. training 本地联调不再依赖 story backend 训练路由

### 必补测试

1. 配置级测试或脚本校验
2. build 和 dev smoke

## 4.2 PR-FE-SPLIT-02 training 显式 sessionId 路由化

### 目标

让训练 read-model 页面围绕显式 `sessionId` 运转，而不是依赖隐式缓存恢复。

### 必做范围

1. `Training.tsx` 子导航显式带 `sessionId`
2. progress、report、diagnostics 页面优先消费 URL 中的 `sessionId`
3. `activeSession` 与 `resumeTarget` 只作为回退，不再充当主身份来源
4. 支持复制链接和新标签页稳定恢复

### 主要文件

1. `frontend/src/pages/Training.tsx`
2. `frontend/src/config/routes.ts`
3. `frontend/src/components/training/TrainingInsightShell.tsx`
4. `frontend/src/pages/TrainingProgress.tsx`
5. `frontend/src/pages/TrainingReport.tsx`
6. `frontend/src/pages/TrainingDiagnostics.tsx`

### 明确不做

1. 不扩展新的训练功能
2. 不改 story 主链

### 合并门槛

1. 点击训练子导航时 URL 包含当前 `sessionId`
2. 刷新后仍能稳定读取同一训练会话
3. 多会话切换时不会串读

### 必补测试

1. `frontend/src/pages/Training.integration.test.tsx`
2. `frontend/src/pages/TrainingMainPathSmoke.integration.test.tsx`
3. insight 页面 URL 恢复测试

## 5. 并行建议

可以并行：

1. `PR-BE-SPLIT-01` 与 `PR-FE-SPLIT-01` 可并行设计，但前端最终要等后端入口方案冻结后再合并
2. `PR-BE-SPLIT-04` 可以在 `PR-BE-SPLIT-03` 接近完成时开始准备目录迁移方案

不建议并行：

1. `PR-BE-SPLIT-03` 与 `PR-FE-SPLIT-01` 不建议同时直接合并，否则容易出现前端切换时后端入口未稳定
2. `PR-FE-SPLIT-02` 不应早于 `PR-FE-SPLIT-01`

## 6. 每个 PR 的 Review 重点

### 后端 Review Focus

1. 是否引入新的双入口或兼容歧义
2. 是否继续扩大巨型 service
3. 是否混用 `threadId` 与 `sessionId`
4. 是否丢失 trace、错误码或 CORS 一致性
5. 是否补齐入口级测试

### 前端 Review Focus

1. 是否仍把 training 挂在 story backend
2. 是否仍依赖 localStorage 或内存状态作为训练读模型的主事实源
3. 是否把 session 兼容逻辑散落在页面层
4. 是否影响 story 主链稳定性

## 7. 当前最该先做的三件事

1. 做 `PR-BE-SPLIT-01`
2. 做 `PR-FE-SPLIT-01`
3. 做 `PR-BE-SPLIT-03`

这三步完成后，架构上才算真正开始分离，而不是仍停留在“逻辑共存、端口看似分开”的状态。
