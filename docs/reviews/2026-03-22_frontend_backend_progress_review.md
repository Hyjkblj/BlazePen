# BlazePen 当前项目进展与训练/故事拆分 PR Review

- Review date: `2026-03-22`
- Review scope: current worktree on top of `HEAD` (`1794ee4`)
- Review focus: `training / story` 后端拆分 PR 链路，以及对应前端双入口、双端口联调基线
- Verification:
  - Backend: `python -m pytest backend/test_training_standalone_app.py backend/test_api_cors_config.py backend/test_api_entrypoint_boundaries.py -q` -> `11 passed`
  - Frontend: `cd frontend && npm exec vitest run vite.app.config.test.ts src/apps/AppShell.integration.test.tsx src/hooks/useTrainingReadQuery.test.tsx src/pages/TrainingInsights.integration.test.tsx` -> `15 passed`

## 当前结论
- 当前拆分 PR 还没有“全部完美实现”。
- 已经收住的部分是：双后端入口边界、共享 app factory、training-only 后端入口、前端双端口与双 app shell 基线。
- 还没有收住的部分是：训练显式 `sessionId` 读链路定型、story/training 领域实现层彻底对称拆分、双后端运行配置与运维文档单一事实源。
- 按当前代码判断：
  - 基本完成：`PR-BE-SPLIT-01`、`PR-BE-SPLIT-02`、`PR-BE-SPLIT-03`、`PR-FE-SPLIT-01`
  - 部分完成：`PR-FE-SPLIT-02`、`PR-BE-SPLIT-05`
  - 未完成：`PR-BE-SPLIT-04`

## 当前 PR 状态

| PR-ID | 当前状态 | 依据 | 仍缺什么 |
| --- | --- | --- | --- |
| `PR-BE-SPLIT-01` | 基本完成 | `backend/api/app_factory.py` 已落地，`api.app` 与 `api.training_app` 都改为复用 `create_api_app(...)` | 只剩后续随 `PR-BE-SPLIT-05` 做运行配置和文档统一，不再是入口装配缺失问题 |
| `PR-BE-SPLIT-02` | 基本完成 | `backend/api/training_app.py` 只挂 `training.router`，standalone app 测试已通过 | 需要继续和 `PR-BE-SPLIT-05` 一起补齐运维口径，而不是再改入口边界 |
| `PR-BE-SPLIT-03` | 基本完成 | `backend/api/app.py` 已不再暴露 training router，`backend/test_api_entrypoint_boundaries.py` 通过 | 主要剩文档清理和发布口径确认 |
| `PR-FE-SPLIT-01` | 基本完成 | `frontend/vite.story.config.ts`、`frontend/vite.training.config.ts`、`frontend/src/apps/story/AppStory.tsx`、`frontend/src/apps/training/AppTraining.tsx` 已拆开，配置与 app shell 测试通过 | 已不再是主要风险点 |
| `PR-FE-SPLIT-02` | 部分完成 | 训练读页已支持显式 `sessionId`，且 `query sessionId` 优先于 `activeSession` | 训练主页和读页还没有完全复用同一套 target 决策；无 query 参数时仍继续依赖内存/本地恢复 fallback |
| `PR-BE-SPLIT-04` | 未完成 | `backend/story/*` 已出现，但 story 实现仍大量经由 `api/services/game_service.py` 与 `api/dependencies.py` 过渡装配 | 还没有形成与 training 对称的 `routers / services / repository-store / policy / dto` 边界，也没有 import 约束 |
| `PR-BE-SPLIT-05` | 部分完成 | 入口边界测试、training standalone 测试、CORS helper 测试已存在并通过 | 运行配置、旧配置口径、story/training 运维文档与入口级 CORS/独立 smoke 仍未完全统一 |

## 前端 Findings
- [Major] `frontend/src/pages/Training.tsx:62`
  问题：训练主页仍自己用 `sessionView?.sessionId ?? resumeTarget?.sessionId` 拼 insight 入口，没有完全复用训练读页的 `session target` 决策。
  原因：这意味着训练主页与 `progress / report / diagnostics` 页仍可能各自维护一套 `sessionId` 选择逻辑，违反单一事实源。
  影响：当 `activeSession / resumeTarget / URL sessionId` 冲突时，主页跳转和洞察页读取可能落到不同会话，`PR-FE-SPLIT-02` 只能算部分收口。
  建议：把训练主页的 insight 跳转入口统一改为消费 `useTrainingSessionReadTarget` 或 `useTrainingSessionViewModel` 产出的同一 target，不再在页面层手工 fallback。

- [Major] `frontend/src/utils/trainingSession.ts:321`
  问题：训练场景仍在 normalizer 层兼容 `briefing -> brief`，同时 API 类型仍暴露 `briefing`。
  原因：页面层 alias 虽然已经基本被移除，但契约层还没有真正定成单字段，训练前端仍在承接后端历史脏字段。
  影响：这会继续拖住 `PR-FE-SPLIT-02` 之后的 contract-first 收口，训练前端拆成独立入口后仍无法明确哪个字段才是权威事实源。
  建议：确认 `brief` 为唯一 canonical 字段；同步清理 `frontend/src/types/api.ts` 和 `backend/api/schemas.py` 中的 `briefing` 暴露，再补一条“页面只能消费 canonical 字段”的契约测试。

- [Minor] `frontend/src/pages/TrainingProgress.tsx:18`
  问题：当前训练读页仍正式支持“无 query `sessionId` 时回落到 `activeSession / resumeTarget`”。
  原因：这对体验是友好的，但从拆分 PR 目标看，它说明“显式 `sessionId` 路由化”还不是严格契约，而是“有 URL 用 URL，没有 URL 继续兜底”。
  影响：刷新和复制链接已经稳定，但多标签页与跨应用跳转的身份边界仍带有上下文依赖，`PR-FE-SPLIT-02` 不应被判成完全关闭。
  建议：明确写死验收口径。如果目标是“读页必须显式 `sessionId`”，就继续收紧；如果接受当前策略，就在 PR 规划文档里把 fallback 定义成正式契约，不再继续模糊。

## 后端 Findings
- [Major] `backend/api/services/game_service.py:1`
  问题：story 域仍保留 `GameService` 这个过渡 facade，story 领域实现并没有像 training 一样完成对称分层。
  原因：当前 story 逻辑一部分在 `backend/story/*`，一部分仍通过 `api/services/game_service.py` 和 `api/dependencies.py` 过渡拼装，说明 `PR-BE-SPLIT-04` 还停留在“半迁移”状态。
  影响：story/training 的领域边界仍不对称，后续继续拆分时容易让 router、dependency wiring 和领域实现层相互穿透，长期维护成本会越来越高。
  建议：把 `GameService` 明确限定为短期兼容层，继续把 story 域收成对称结构，并补 import 约束或静态检查，禁止 `story` 与 `training` 互相直接依赖实现。

- [Major] `backend/config_manager.py:105`
  问题：旧配置管理仍保留单一 `ALLOWED_ORIGINS` 语义，而新入口已经在 `backend/api/cors_config.py` 中引入 `STORY_ALLOWED_ORIGINS / TRAINING_ALLOWED_ORIGINS` 双 scope。
  原因：运行配置现在存在两套 CORS 口径，说明 `PR-BE-SPLIT-05` 还没有把 story/training 双入口的运维事实源收成一处。
  影响：只要有脚本、部署说明或运维代码继续读取旧配置对象，就可能回退到单后端时代的 origin 语义，导致“代码支持双入口，但部署口径仍是单入口”。
  建议：明确废弃还是并入 `config_manager.py` 的旧 CORS 配置；若保留，就让它复用 `cors_config.py`；若废弃，就移除旧字段并同步更新 `.env.example` 与运维文档。

## Open Questions
- `PR-FE-SPLIT-02` 的目标到底是“显式 `sessionId` 为严格必需”，还是“显式优先，但允许 active/resume fallback 作为正式契约”？这会直接决定它现在是“部分完成”还是“可验收”。
- `GameService` 在 story 域拆分完成后是否还要长期保留？如果只是迁移 shim，就应尽快定义删除条件，避免过渡层永久化。

## 测试缺口
- 前端：缺少一条直接锁定训练主页与 `useTrainingSessionReadTarget` 使用同一 `sessionId` 决策的集成测试。当前 `frontend/src/pages/Training.integration.test.tsx` 还没有覆盖“主页跳转到洞察页时，目标 `sessionId` 与读页实际读取 `sessionId` 完全一致”。
- 前端：缺少“canonical `brief` 契约”回归。当前测试覆盖了 normalizer 行为，但没有一条会在 `briefing` 再次泄漏到页面层时立即报警的页面/服务契约测试。
- 后端：缺少 `story` 侧 standalone 入口或最小 smoke 测试。当前有 `backend/test_training_standalone_app.py`，但没有对称的 story app 独立启动/健康检查/边界验证测试。
- 后端：缺少入口级 CORS 行为测试。当前 `backend/test_api_cors_config.py` 只验证 helper，没有直接锁定 `api.app` 与 `api.training_app` 在实际 app 层的 CORS 返回行为。
- 后端：缺少 story/training 领域 import 边界测试。当前还没有静态检查去阻止后续再次把 story/training 互相穿透回去。

## Review Summary
- 当前拆分 PR 不能判定为“全部完美实现”，但也已经不是早期那种“只有一个 `training_app.py` 文件”的假拆分状态。
- 后端入口装配、training-only 入口和 story/training 暴露边界已经基本收住，这是这轮拆分里最实质的进展。
- 前端双端口和双 app shell 已经成型，但训练显式 `sessionId` 读链路还没有彻底定型，所以 `PR-FE-SPLIT-02` 仍应按部分完成管理。
- 后端剩余最大工作不是继续加入口，而是完成 story/training 领域实现层对称拆分，并把双入口运维配置与文档收成单一事实源。
- 因此当前最合理的推进顺序是：先收口 `PR-FE-SPLIT-02` 的身份边界，再推进 `PR-BE-SPLIT-04`，最后用 `PR-BE-SPLIT-05` 把双后端运维链路和文档彻底关门。
