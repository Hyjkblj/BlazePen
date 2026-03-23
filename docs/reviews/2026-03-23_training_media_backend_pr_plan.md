# BlazePen 训练后端媒体能力接入 PR 计划（2026-03-23）

## 任务理解
- 本轮目标是让训练后端具备“可调度生图、语音、文本大模型任务”的工程能力，同时不破坏当前训练主链路稳定性。
- 领域归属保持清晰：训练域负责任务触发、状态、幂等、恢复；媒体域负责具体生成执行。
- 会话状态以服务端为单一事实源，训练会话仅使用 `sessionId`，不引入故事域 `threadId` 语义。
- 关键状态迁移要可追踪：任务创建、任务执行中、任务成功/失败/超时、会话恢复。
- 不做项：不把生图/语音重任务塞回 `submit_round` 同步热路径；不让前端本地猜任务状态。

## 后端方案

### router
- 新增 `api/routers/training_media.py`。
- 提供接口：
  - `POST /api/v1/training/media/tasks`：创建媒体任务。
  - `GET /api/v1/training/media/tasks/{task_id}`：查询任务详情。
  - `GET /api/v1/training/media/sessions/{session_id}/tasks`：按会话查询任务列表。
- `training_app.py` 在 training-only 入口挂载该路由，保持服务边界可见。

### service
- 新增 `api/services/training_media_task_service.py`，职责仅限：
  - 校验请求与会话归属。
  - 生成幂等键并落库任务。
  - 投递异步执行（后续 PR 接入执行器）。
  - 提供统一查询视图。
- 保留 `TrainingService` 的训练回合评估与状态推进职责。
- 拆分点：媒体任务编排从 `TrainingService` 剥离，不扩大巨型 service。

### repository-store
- 在 `models/training.py` 新增 `TrainingMediaTask` 表（建议）：
  - `task_id`（主键）
  - `session_id`（索引，关联训练会话）
  - `round_no`（可空，支持 init 阶段任务）
  - `task_type`（`image`/`tts`/`text`）
  - `status`（`pending`/`running`/`succeeded`/`failed`/`timeout`）
  - `idempotency_key`（唯一约束）
  - `request_payload`（JSON）
  - `result_payload`（JSON，可空）
  - `error_payload`（JSON，可空）
  - `retry_count`、`max_retries`
  - `created_at`、`updated_at`、`started_at`、`finished_at`
- 在 `training_repository.py` + `training_store.py` 增加：
  - `create_media_task(...)`
  - `get_media_task(task_id)`
  - `list_media_tasks(session_id, round_no?)`
  - `claim_media_task(task_id)`（CAS：`pending -> running`）
  - `complete_media_task(task_id, result/error, status)`

### policy
- 新增 `training/media_task_policy.py`：
  - `task_type` 与 payload schema 规则。
  - canonical payload 归一化（用于稳定幂等键）。
  - 幂等键生成策略与输入合法性校验。
  - 可恢复任务判定（是否允许重试）。

### async-task
- 分两步：
  - PR-06A：先建立任务表与状态契约，任务创建后保持 `pending`，保证 API 契约稳定。
  - PR-06B：新增 `training/media_task_executor.py` + dispatcher，按 `task_type` 调用已有 `ImageService` / `TTSService` / `TextModelService` 适配层。
- 执行模型：
  - 非阻塞异步执行，避免 round 提交热路径等待外部模型。
  - provider 调用失败仅影响任务状态，不回滚已提交的训练回合事实。

### dto
- 新增请求 DTO：
  - `TrainingMediaTaskCreateRequest`
    - `session_id: str`
    - `round_no: Optional[int]`
    - `task_type: Literal["image", "tts", "text"]`
    - `payload: dict`
    - `idempotency_key: Optional[str]`
- 新增响应 DTO：
  - `TrainingMediaTaskResponse`
    - `task_id`, `session_id`, `round_no`, `task_type`, `status`
    - `result: Optional[dict]`
    - `error: Optional[TrainingMediaTaskErrorDetail]`
    - `created_at`, `updated_at`, `started_at`, `finished_at`
  - `TrainingMediaTaskListResponse`
    - `session_id`, `items: List[TrainingMediaTaskResponse]`
- 新增错误 DTO（统一结构）：
  - `code`（HTTP）
  - `message`
  - `error_code`
  - `details`（至少包含 `session_id`、`round_no`、`task_id`、`route`）

## 一致性与契约设计

### 会话事实源
- 单一事实源：`training_sessions` + `training_media_tasks`。
- 前端只消费服务端任务状态，不在本地推断“任务是否成功”。

### 幂等策略
- 默认幂等键：`sha256(session_id + round_no + task_type + canonical_payload)`。
- 数据库 `UNIQUE(idempotency_key)` 做最终重复提交保护。
- 重复请求命中幂等键时返回已有 `task_id` 与当前状态。

### 恢复策略
- 服务重启后扫描 `running/pending`：
  - 超时任务转 `timeout`。
  - 可重试任务按策略回到 `pending` 并记录审计事件。
- `GET /sessions/{session_id}/tasks` 作为恢复后任务视图入口。

### 错误码
- `TRAINING_MEDIA_TASK_NOT_FOUND`
- `TRAINING_MEDIA_TASK_INVALID`
- `TRAINING_MEDIA_TASK_UNSUPPORTED`
- `TRAINING_MEDIA_PROVIDER_UNAVAILABLE`
- `TRAINING_MEDIA_TASK_EXECUTION_FAILED`
- `TRAINING_MEDIA_TASK_TIMEOUT`

### 事务边界与回滚边界
- `submit_round` 事务内：训练回合事实 + 媒体任务记录 + 审计事件，一起提交或一起回滚。
- 异步执行事务外：只更新任务状态与结果，不回滚历史回合。
- 回滚边界清晰：外部模型失败不会回滚训练域主线事实。

## 风险点
- 数据一致性风险：无唯一幂等键会导致重复任务和重复成本消耗。
- 并发风险：多 worker 抢同一任务会产生双执行，必须使用状态 CAS/行级锁。
- 恢复风险：进程崩溃导致 `running` 任务悬挂，需要超时回收。
- 性能风险：若误入同步路径会拉高 `submit_round` 延迟并放大失败面。
- 兼容性风险：新增字段若漂移会破坏前端契约，需契约测试冻结。
- 可观测性风险：若日志缺少 `session_id/round_no/task_id` 将难以排障与审计。

## 测试建议
- 单测：
  - `media_task_policy` 的 payload 归一化、幂等键稳定性、非法输入拒绝。
  - 任务状态机合法迁移与非法迁移拦截。
- 集成测试：
  - 创建任务、重复提交幂等命中、查询任务列表。
  - 执行器接入后覆盖成功/失败/超时分支。
- 契约测试：
  - `training_media` router 的 request/response/error schema 冻结。
  - `round/submit` 引入 `media_tasks` 摘要时的向后兼容验证。
- 恢复测试：
  - 重启后 `running/pending` 任务恢复与超时回收。
  - provider 不可用时错误码与审计事件一致性。
- smoke/CORS：
  - training standalone 入口可访问 `training_media` 路由。
  - 双入口（full api / training-only）跨域配置一致性验证。

## 产出要求
- 按 4 个小 PR 推进，避免大 PR 混改：
  - `BE-TRAINING-MEDIA-06A`：任务模型、仓储接口、路由与 DTO 契约落地（不执行）。
  - `BE-TRAINING-MEDIA-06B`：异步执行器、状态迁移、重试与超时处理。
  - `BE-TRAINING-MEDIA-06C`：`submit_round` 触发改造（事务内落任务，事务外执行）。
  - `BE-TRAINING-MEDIA-06D`：standalone + smoke/CORS + runbook 闭环。
- 每个 PR 必须包含：
  - 对应契约测试与边界测试。
  - 审计日志上下文（`session_id`、`round_no`、`task_id`、`route`）。
  - 过渡兼容说明与退场条件。

