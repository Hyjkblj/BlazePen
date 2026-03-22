# BlazePen 故事后端与训练后端独立拆分实施清单

更新日期：2026-03-22

## 1. 结论

建议拆分，但采用“单仓双后端入口，共享基础设施，隔离领域服务”的方式推进，而不是现在就拆成两个独立仓库。

推荐目标形态：

1. 故事后端只对外提供 story 域能力，默认入口 `http://localhost:8000`
2. 训练后端只对外提供 training 域能力，默认入口 `http://localhost:8010`
3. 两者共享基础设施层，但不共享领域 service、会话模型和恢复模型
4. 前端 story 只连 story backend，training 只连 training backend

不建议继续维持当前这种“主后端和训练后端同时都能对外提供 training 路由”的长期状态。

## 2. 为什么现在要拆

当前已经出现了以下信号：

1. 前端 training 已经独立到 `3001`，但 `frontend/vite.app.config.ts` 仍写死代理到 `8000`，说明前后端边界没有一起拆干净。
2. 后端已经新增 `backend/api/training_app.py`，说明训练域正在形成独立服务入口，但 `backend/api/app.py` 仍继续挂载 `training.router`。
3. story 使用 `threadId`，training 使用 `sessionId`，两个域的会话概念和恢复模型本质不同，继续放在同一入口下会持续扩大耦合。
4. training 未来还会继续长出 `progress / report / diagnostics / recovery / smoke / self-check`，其运维和契约要求已经和 story 不同。

## 3. 拆分原则

### 3.1 允许共享

1. 日志、trace、request context
2. 通用错误封装与 response envelope
3. CORS 配置构造器
4. 数据库连接管理
5. 通用 DTO 基类、脚本启动壳层

### 3.2 不允许共享

1. story service 直接调用 training service
2. training service 直接复用 story session/thread 语义
3. story router 暴露 training 域主入口
4. training router 暴露 story 域主入口
5. 前端依赖 localStorage 作为跨 story/training 的权威会话源

### 3.3 领域边界

故事域负责：

1. `threadId`
2. 故事初始化、回合推进、历史、结局、快照恢复
3. story 页面需要的读模型

训练域负责：

1. `sessionId`
2. 训练初始化、场景推进、回合提交、进度、报告、诊断、恢复
3. training 页面需要的读模型

共享域只做基础设施，不承接 story/training 的业务状态。

## 4. 目标结构

建议目标结构如下：

```text
backend/
  api/
    app.py                  # story backend entry
    training_app.py         # training backend entry
    app_factory.py          # 共享 app 装配
    cors_config.py          # 共享 CORS 规则构造
    middleware/
    routers/
      story_*.py
      training.py
  services/
    story/
    shared/
  training/
    repository_store/
    policy/
    dto/
    async_task/
  story/
    repository_store/
    policy/
    dto/
```

如果当前阶段不想大搬目录，最低要求也必须做到：

1. `backend/api/app.py` 只挂 story 路由
2. `backend/api/training_app.py` 只挂 training 路由
3. 两个入口复用同一套 middleware、trace、error、CORS 装配

## 5. 分阶段实施

### 5.1 阶段 A：先收口入口，不先大搬代码

目标：

1. 明确 story 和 training 的唯一对外入口
2. 消除双入口漂移
3. 不在这一阶段做大规模目录迁移

任务清单：

- [ ] 新增共享 app 装配层，例如 `backend/api/app_factory.py`
- [ ] 把 `backend/api/app.py` 的 trace middleware 提炼为共享安装逻辑
- [ ] 把 `install_common_exception_handlers(app)` 的调用收口到共享装配层
- [ ] 把 `build_cors_middleware_options()` 的调用收口到共享装配层
- [ ] 让 `backend/api/app.py` 只负责 story 路由装配
- [ ] 让 `backend/api/training_app.py` 只负责 training 路由装配
- [ ] 明确保留哪些静态资源只由 story backend 提供
- [ ] 明确 training backend 是否需要 `/static`，若不需要则不挂载

建议 PR：

1. `PR-BE-SPLIT-01` 共享 app factory 与 middleware 收口
2. `PR-BE-SPLIT-02` 训练入口收口为 training-only authority

涉及文件：

1. `backend/api/app.py`
2. `backend/api/training_app.py`
3. `backend/api/cors_config.py`
4. `backend/api/middleware/error_handler.py`
5. `backend/api/request_context.py`
6. `backend/api/response.py`

### 5.2 阶段 B：停掉主后端上的 training 对外主入口

目标：

1. 结束 `api.app` 和 `api.training_app` 同时暴露 training 的状态
2. 让 training 前端只命中 training backend

任务清单：

- [ ] 从 `backend/api/app.py` 移除 `app.include_router(training.router, prefix="/api")`
- [ ] 如果需要过渡兼容，单独加短期兼容层，不保留长期双入口
- [ ] 明确兼容层退出日期和删除条件
- [ ] 更新开发文档、启动脚本、README
- [ ] 更新本地启动命令，明确 story backend 和 training backend 各自端口

建议 PR：

1. `PR-BE-SPLIT-03` 主后端移除 training 主入口

涉及文件：

1. `backend/api/app.py`
2. `backend/run_training_api.py`
3. `backend/start_training_backend.ps1`
4. 相关 README 和 docs

### 5.3 阶段 C：前端跟随后端完成真正解耦

目标：

1. 训练前端不再默认打到 story backend
2. 训练 read 页面使用显式 `sessionId`

任务清单：

- [ ] 给 story 和 training 分别配置 API target
- [ ] `vite.story.config.ts` 默认指向 story backend
- [ ] `vite.training.config.ts` 默认指向 training backend
- [ ] 训练主页面跳转 progress、report、diagnostics 时显式携带 `sessionId`
- [ ] 禁止 training read 页面仅靠 `activeSession` 或 `resumeTarget` 推断会话身份
- [ ] 补页面级和配置级回归测试

建议 PR：

1. `PR-FE-SPLIT-01` story/training 双 backend target
2. `PR-FE-SPLIT-02` training 显式 `sessionId` 路由身份

涉及文件：

1. `frontend/vite.app.config.ts`
2. `frontend/vite.story.config.ts`
3. `frontend/vite.training.config.ts`
4. `frontend/package.json`
5. `frontend/src/pages/Training.tsx`
6. `frontend/src/config/routes.ts`
7. `frontend/src/components/training/TrainingInsightShell.tsx`

### 5.4 阶段 D：把共享和领域代码做软分层

目标：

1. 后端共享基础设施与 story/training 业务层真正分离
2. 为未来是否拆仓库保留空间

任务清单：

- [ ] 建立 `story/` 与 `training/` 的领域目录边界
- [ ] 训练域按 `routers / services / repository-store / policy / dto / async-task` 收口
- [ ] story 域按 `routers / services / repository-store / policy / dto` 收口
- [ ] 禁止 story 目录 import training 领域实现
- [ ] 禁止 training 目录 import story 领域实现
- [ ] 共享逻辑只允许放到 shared/infra 层

建议 PR：

1. `PR-BE-SPLIT-04` 领域目录软分层

### 5.5 阶段 E：部署、观察性与运维收口

目标：

1. 两个后端都能独立启动、独立 smoke、独立定位问题
2. 不因拆分损失 trace、日志和错误上下文

任务清单：

- [ ] 两个后端统一返回 `X-Trace-Id`
- [ ] 两个后端统一稳定 error envelope
- [ ] story 与 training 各自有独立 smoke
- [ ] story 与 training 各自有独立 health check
- [ ] story 与 training 各自有启动脚本与启动文档
- [ ] 明确生产环境 `STORY_ALLOWED_ORIGINS` 与 `TRAINING_ALLOWED_ORIGINS`

建议 PR：

1. `PR-BE-SPLIT-05` 双后端可观测性和运维收口

## 6. 验收标准

只有满足以下条件，才算“故事后端与训练后端拆分完成”：

1. story 前端默认只访问 `8000`
2. training 前端默认只访问 `8010`
3. `backend/api/app.py` 不再暴露 training 主入口
4. `backend/api/training_app.py` 不再承担 story 域能力
5. 两个入口都具备相同的 trace、error、CORS 装配基线
6. 训练 read 页面可通过 URL 中的 `sessionId` 稳定复现
7. story 域不再接触 `sessionId`
8. training 域不再接触 `threadId`

## 7. 必补测试

### 7.1 后端

- [ ] `backend/test_training_standalone_app.py` 补 `X-Trace-Id` 响应头断言
- [ ] 新增 `backend/test_story_app_entry.py`，锁定主后端不再响应 training 主路由
- [ ] 新增 `backend/test_training_app_entry.py`，锁定 training app 不响应 story 路由
- [ ] 新增入口级 CORS 测试，而不是只测 `cors_config.py` helper
- [ ] story 与 training 各自补 smoke 命令回归

### 7.2 前端

- [ ] `frontend/src/pages/Training.integration.test.tsx` 补“点击子导航必须携带 sessionId”
- [ ] `frontend/src/pages/TrainingMainPathSmoke.integration.test.tsx` 补“training 默认命中 training backend 配置”
- [ ] 新增配置级测试，锁定 `3000 -> 8000`、`3001 -> 8010`
- [ ] 补 story 前端回归，确保训练拆出后 story 主链不被污染

## 8. 风险点

1. 只拆端口，不拆后端权威入口，最终只会变成“表面拆分”。
2. 如果 training 前端继续依赖 `activeSession` 和 localStorage 推断身份，训练读模型仍然不稳定。
3. 如果 `api.app` 和 `api.training_app` 的 middleware 栈继续分叉，后续排查线上问题会越来越困难。
4. 如果现在就大规模迁目录，而不先锁定入口和契约，回归面会过大。

## 9. 推荐执行顺序

推荐严格按下面顺序推进：

1. `PR-BE-SPLIT-01` 共享 app factory 和 middleware 收口
2. `PR-BE-SPLIT-02` training-only 入口收口
3. `PR-FE-SPLIT-01` training 前端切到 `8010`
4. `PR-FE-SPLIT-02` training 显式 `sessionId` 路由化
5. `PR-BE-SPLIT-03` 主后端移除 training 主入口
6. `PR-BE-SPLIT-04` story 和 training 领域软分层
7. `PR-BE-SPLIT-05` 双后端 smoke、trace、CORS、文档收口

## 10. 当前最该先做的三件事

1. 让 `frontend` 的 training 端口真正连到 `8010`
2. 让 `backend/api/training_app.py` 和 `backend/api/app.py` 复用同一套 middleware、trace、error 装配
3. 从 `backend/api/app.py` 移除 training 主路由，结束双入口

这三步做完，才算真正迈入“后端独立拆分”阶段，而不是停留在“已经多了一个 `training_app.py` 文件”的阶段。
