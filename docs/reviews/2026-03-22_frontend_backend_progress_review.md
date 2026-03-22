# BlazePen 当前项目进展与前后端分离 Review

- Review date: `2026-03-22`
- Review scope: current `HEAD` (`89d2b88`, major feature set from `98ba2bb`)
- Verification:
  - Backend: `python -m pytest backend/test_api_dependencies.py backend/test_training_router.py backend/test_training_service.py backend/test_training_query_service.py backend/test_api_contract_standardization.py -q` -> `112 passed`
  - Frontend: `npm exec vitest run src/pages/Training.integration.test.tsx src/pages/TrainingInsights.integration.test.tsx src/hooks/useTrainingSessionBootstrap.test.tsx src/hooks/useTrainingReport.test.tsx src/services/trainingApi.test.ts src/utils/trainingSession.test.ts src/storage/trainingSessionCache.test.ts` -> `36 passed`

## 前端 Findings
- [Major] `frontend/src/flows/useTrainingMvpFlow.ts:290`
  问题：训练页主 flow 同时承担会话目标解析、DTO 到 view-state 投影、提交流转恢复和页面交互状态，已经形成巨型 orchestration hook。
  原因：`flow` 层本应只负责编排交互，但这个文件把 `resolveRestoreIdentity`、`buildSessionViewFrom*`、`deriveProgressAnchor` 等恢复与读模型逻辑全部内嵌，重新把 `pages / flows / hooks / services / storage / contexts` 边界耦合到一起，并形成 `sessionView / activeSession / resumeTarget` 三套重叠状态入口。
  影响：后续只要恢复优先级、summary 契约或 session view 形状有变化，就要同步修改多处逻辑，训练页与 progress/report/diagnostics 页很容易出现恢复路径分叉，前端继续演化会越来越难测。
  建议：把 session target 解析与 `TrainingSessionViewState` 映射抽到独立 hook 或 selector，`useTrainingMvpFlow` 只保留页面编排和用户交互；与 `useTrainingSessionBootstrap`、`useTrainingSessionReadTarget` 共享同一套 session target 决策逻辑。

- [Major] `frontend/src/pages/Training.tsx:339`
  问题：页面层仍直接用 `brief || briefing` 兼容双字段场景简介。
  原因：这把服务端兼容和 normalizer 归一化责任泄漏到了 `page` 层，违反“页面不能直接兼容后端脏字段”和 contract-first 的消费边界；当前 `TrainingScenario` 类型继续暴露两个近义字段，也说明契约没有真正收口。
  影响：一旦后端收口到单字段，或者 `brief` 与 `briefing` 的语义分化，训练页会静默显示错误文案，前后端都无法明确哪个字段才是事实源。
  建议：在 `frontend/src/utils/trainingSession.ts` 内统一归一成单一展示字段，并收紧 `frontend/src/types/training.ts` 的 `TrainingScenario` 类型；页面只消费规范字段，不再自己做 alias fallback。

## 后端 Findings
- [Major] `backend/training/training_query_service.py:275`
  问题：`get_diagnostics` 没有像 `summary / progress / history / report` 一样先校验 persisted session sequence 和 snapshots，就直接拼装 read model。
  原因：这让 diagnostics 成为独立于 recovery model 的“半特例”查询，破坏 training query/read-model 的一致恢复语义；同一会话在 report/progress 上可能已经被判定为 corrupted，在 diagnostics 上却仍可读。
  影响：前端 diagnostics 页不会触发终态恢复清理，用户会看到“报告/进度打不开但诊断还在工作”的分裂体验，也会掩盖真实的 session corruption。
  建议：要么让 diagnostics 与其他 training read models 一样先过 `_read_persisted_session_sequence_or_raise` 和 `_read_session_snapshots_or_raise`，要么明确把它升级为独立 operational log endpoint，并从训练恢复链路中剥离，不要保持当前半耦合状态。

- [Major] `backend/api/routers/training.py:123`
  问题：训练路由仍把 `ValueError` 文本交给 `infer_training_error_code(message)` 推断业务错误码。
  原因：错误契约依赖文案字符串而不是稳定的 domain exception / error enum，直接违反“错误处理不能依赖 message 文本承载业务语义”；当前 scenario mismatch 等校验仍以 free-text `ValueError` 形式泄出。
  影响：文案调整、国际化或重构后会静默改变 `error.code`，前端恢复分支、提示文案和回归测试都会变得不稳定，后端也无法可靠统计具体业务失败类型。
  建议：把 training 域剩余 `ValueError` 收口为显式 domain exception，router 只做类型到 `error_code` 的映射，删除 training message inference 分支。

## Open Questions
- `brief` 和 `briefing` 在训练场景 DTO 中到底是历史 alias，还是两个有意保留的不同语义字段？如果不是同义字段，前端不能再用 fallback 混读。
- diagnostics 是否有意在 session recovery facts 已损坏时仍继续可读？如果答案是“是”，它就不应继续复用训练恢复页的同一套 read-model / UX 语义。

## 测试缺口
- 前端：`frontend/src/flows/useTrainingMvpFlow.ts` 目前没有独立测试文件，`frontend/src/pages/Training.integration.test.tsx` 也没有锁定 `sessionView / activeSession / resumeTarget` 三者优先级一致性，无法保护这套巨型 flow 后续继续膨胀时的恢复分叉风险。
- 前端：`frontend/src/pages/Training.integration.test.tsx` 的场景 fixture 同时提供了 `brief` 与 `briefing`，但没有“只允许页面消费 canonical 字段”的契约测试，当前页面层 alias fallback 没有测试会把它拦住。
- 后端：`backend/test_training_query_service.py` 与 `backend/test_training_router.py` 还没有 `diagnostics` 在缺失 `scenario_sequence / snapshots` 时返回 `TRAINING_SESSION_RECOVERY_STATE_CORRUPTED` 的回归测试，当前 diagnostics 的恢复语义分叉没有保护。
- 后端：`backend/test_api_contract_standardization.py` 还没有约束训练路由不得通过 message 文本推断业务错误码的契约测试，`infer_training_error_code(...)` 这条过渡层目前缺少反向约束。
- 后端：本次只复核了训练相关单测与前端 Vitest，没有执行真实数据库初始化、自检和 smoke，所以 `backend/alembic/**`、`scripts/init_db.py`、`scripts/check_database_status.py`、训练 CLI/local smoke 这条发布前链路仍缺现场验证。

## Review Summary
- 训练后端主链路和前端训练页/洞察页都已经明显前进，当前训练相关自动化回归是绿的，基础可用性没有问题。
- 之前最危险的 GET 写库副作用和 `progress_percent` 语义漂移已经被修掉，这一轮主要剩的是边界一致性问题。
- 前端现在的问题不再是“有没有训练页”，而是训练页内部还没有真正完成边界收口，巨型 flow 和页面层脏字段兼容会继续拖慢后续演进。
- 后端现在的问题不再是“有没有 query service”，而是 query/read-model 的恢复语义还没有完全统一，同时 router 仍保留了 message-driven 的错误码推断。
- 因此当前项目可以判断为“训练主链路已成型，但还不能宣称训练后端已完全收口、前端已完全解耦”。

## 当前项目进展
- 按 `docs/BlazePen_训练后端完成与前端解耦阶段PR规划.md` 与 `docs/烽火笔锋_训练收口与报告前端双人并行PR排期.md` 的阶段口径粗估：
  - 后端进展约 `80%-85%`
  - 前端进展约 `70%-75%`
  - 当前阶段整体进展约 `75%-80%`
- 后端已完成的部分：
  - `init / scenario/next / round/submit / session summary / progress / history / report / diagnostics` 主链路都已存在。
  - 训练 query service、typed recovery error、`sessionId` 边界、`progress_percent` 契约和主要训练自动化测试已经落地。
  - `backend/alembic/**`、`scripts/init_db.py`、`scripts/check_database_status.py` 已经存在，不再是空白脚手架。
- 后端尚未达到“完全收口”的原因：
  - diagnostics 读模型恢复语义仍与其他 read models 分叉。
  - training route 仍保留 message-driven 的错误码推断。
  - 本次没有执行真实数据库初始化、自检和 smoke，`PR-BE-08A` 口径还不能算关闭。
- 前端已完成的部分：
  - 训练专用 `services / types / storage / contexts / hooks / pages` 已经拆出，`Training.tsx`、`TrainingProgress.tsx`、`TrainingReport.tsx`、`TrainingDiagnostics.tsx` 已落地。
  - 训练页主流程、恢复入口、报告页和诊断页基础消费链路都已存在，并有对应 Vitest 回归。
- 前端尚未达到“完全解耦”的原因：
  - 主训练 flow 仍过大，恢复和 view-model 逻辑没有真正收口成单一事实源。
  - 页面层仍在兼容场景脏字段 alias，说明 DTO 消费边界没有彻底定型。
  - 这意味着前端已经从“训练壳层可用”进入“可以继续开发训练 MVP”的阶段，但还不适合宣称“训练前端已完成”。

## PR 拆分原则
- 前后端 PR 严格分开，不做跨层大杂烩提交。
- 一个 PR 只收口一个职责边界，只引入一个新的事实源决策，不同时改读模型、写路径、页面编排和视觉层。
- 每个 PR 必须自带对应测试，避免“代码改完再补测试”的尾债。
- 页面不直接兼容后端脏字段，路由不通过 message 文本推断业务错误码，localStorage 不承担权威状态。
- 优先顺序遵循“先稳事实源和契约，再拆页面与交互，再做发布链路”。

## 后端 PR 规划

| PR-ID | 名称 | 目标 | 核心边界 | 主要文件 | 明确不做 | 合并门槛 |
| --- | --- | --- | --- | --- | --- | --- |
| `PR-BE-07B` | 训练 Query 恢复语义收口 | 统一 `summary / progress / history / report / diagnostics` 的恢复前置校验 | 只动 query/read-model，不碰 round write-path 业务 | `backend/training/training_query_service.py`、`backend/api/routers/training.py`、`backend/test_training_query_service.py`、`backend/test_training_router.py` | 不改前端，不改训练推荐算法，不新增页面字段 | `diagnostics` 与其他 read-model 一样基于 persisted `scenario_sequence + snapshots` 决定可读性；缺失时稳定返回 `TRAINING_SESSION_RECOVERY_STATE_CORRUPTED`；新增 route/query 回归测试 |
| `PR-BE-07C` | 训练错误契约类型化 | 去掉 training route 对 `ValueError.message` 的错误码推断，收口为 typed domain exception | 只动 training 错误契约和 router 映射，不混入 read-model 重构 | `backend/api/routers/training.py`、`backend/api/error_codes.py`、相关 policy/service 抛错点、`backend/test_api_contract_standardization.py`、`backend/test_training_router.py` | 不改数据库，不改 query DTO，不做前端联调 | training 域不再依赖 `infer_training_error_code(message)`；`scenario mismatch`、模式校验、提交校验都有稳定异常类型和 `error.code`；契约测试锁定 |
| `PR-BE-08A` | 训练迁移、自检与 Smoke 收口 | 把训练后端补到可初始化、可升级、可自检、可 smoke 的发布前状态 | 只动迁移、自检、真实 DB 验证链路，不混入业务字段变更 | `backend/alembic/**`、`scripts/init_db.py`、`scripts/check_database_status.py`、`backend/run_training_service_local.py`、`backend/run_training_service_cli.py`、新增 smoke/集成测试 | 不改前端，不改训练页面，不改业务契约字段 | `init_db`、`check_database_status`、真实 DB 回归、训练 smoke 可以执行；补充 README 或 docs 操作步骤；新增验证测试文件并跑通 |
| `PR-BE-08B` | 双前端接入契约与运行配置收口 | 配合 story/training 双前端端口拆分，补齐后端对双前端独立接入的运行配置、跨应用启动契约和联调文档 | 只动后端接入层与运行配置，不回灌训练/故事领域逻辑 | `backend/main.py`、`backend/api/dependencies.py`、CORS/配置文件、训练与故事启动/读取相关 router 文档、联调说明与对应测试 | 不改训练评分逻辑，不改 story/training 核心领域模型，不做前端页面改版 | 明确支持 `3000/3001` 双前端 origin；story 入口只依赖 `threadId` 相关契约，training 入口只依赖 `sessionId` 相关契约；如需跨应用跳转，只暴露显式启动字段而不共享 live session；联调文档和最小验证测试补齐 |

### 后端实施顺序
1. 先做 `PR-BE-07B`，因为 read-model 恢复语义必须先统一，否则前端无法稳定消费 report/diagnostics。
2. 再做 `PR-BE-07C`，因为错误契约不稳定会继续污染前端恢复分支和测试。
3. 再做 `PR-BE-08A`，把迁移、自检、smoke 作为发布前收口，而不是混进业务重构 PR。
4. 最后做 `PR-BE-08B`，把双前端端口拆分需要的后端接入配置、origin 策略和跨应用启动契约收口，避免前端拆出双入口后仍靠隐式约定联调。

### 后端拆分理由
- `PR-BE-07B` 只负责“读模型事实源”，高内聚。
- `PR-BE-07C` 只负责“错误契约”，避免和 query/DTO 改动耦合。
- `PR-BE-08A` 只负责“运行与发布链路”，避免迁移脚本和业务重构互相放大风险。
- `PR-BE-08B` 只负责“双前端接入边界”，把 CORS、origin、启动字段和联调文档从业务 PR 里拆开，避免前端端口拆分和训练领域改动互相污染。

## 前端 PR 规划

| PR-ID | 名称 | 目标 | 核心边界 | 主要文件 | 明确不做 | 合并门槛 |
| --- | --- | --- | --- | --- | --- | --- |
| `PR-FE-06B` | 训练会话恢复与 ViewModel 拆分 | 把 `useTrainingMvpFlow` 中的 session target 解析、summary 到 view-state 映射、恢复优先级决策拆成独立模块 | 只动训练主流程编排，不改 report/diagnostics 页面结构 | `frontend/src/flows/useTrainingMvpFlow.ts`、新增 `frontend/src/hooks/useTrainingSessionViewModel.ts` 或 `selectors`、`frontend/src/hooks/useTrainingSessionBootstrap.ts`、`frontend/src/hooks/useTrainingSessionReadTarget.ts`、相关测试 | 不改后端接口，不做视觉改版，不改训练报告页内容 | `activeSession` 成为第一事实源，`resumeTarget` 只做 fallback；训练页不再在 flow 内维护重复恢复决策；新增针对恢复优先级和重复状态的测试 |
| `PR-FE-06C` | 训练场景 DTO 消费收口 | 去掉页面层对 `brief || briefing` 之类 alias 的直接兼容，统一由 normalizer 输出 canonical 字段 | 只动 DTO/normalizer/页面消费边界，不混入恢复逻辑重构 | `frontend/src/types/training.ts`、`frontend/src/utils/trainingSession.ts`、`frontend/src/pages/Training.tsx`、`frontend/src/services/trainingApi.test.ts`、`frontend/src/utils/trainingSession.test.ts`、`frontend/src/pages/Training.integration.test.tsx` | 不改后端，不改 report 图表，不改 contexts | 页面只消费规范字段；`TrainingScenario` 类型收紧；补“页面不得消费脏字段 alias”的测试 |
| `PR-FE-07A` | 训练洞察页稳定化与报告消费收口 | 在已有 progress/report/diagnostics 基础上统一 read-query UX 和 report 消费边界，确保 report 页成为稳定产品层 | 只动训练洞察页与共享壳层，不回灌主训练流程 | `frontend/src/components/training/TrainingInsightShell.tsx`、`frontend/src/pages/TrainingProgress.tsx`、`frontend/src/pages/TrainingReport.tsx`、`frontend/src/pages/TrainingDiagnostics.tsx`、`frontend/src/hooks/useTrainingReadQuery.ts`、相关 integration tests | 不改训练提交流程，不新增复杂图表平台化能力 | 三个洞察页对 corrupted/not-found/timeout 的行为一致；report 页只消费 DTO，不二次重算后端聚合字段；页面测试补齐 |
| `PR-FE-07B` | 训练前端独立端口与故事主线复原 | 把 training 从当前 story 单应用壳层中拆成独立前端入口和独立 dev 端口，恢复 story app 的独立路由、独立 Provider 和独立恢复边界 | 只动前端应用壳层、入口、路由、Provider、dev/build 配置，不改训练/故事后端接口契约 | `frontend/package.json`、`frontend/vite.config.ts` 或拆分出的 `vite.story.config.ts` / `vite.training.config.ts`、`frontend/src/App.tsx`、`frontend/src/router/index.tsx`、新增 `AppStory` / `AppTraining` 与对应入口文件、相关 smoke tests | 不改后端，不新增跨应用共享 live session，不把训练页面业务重构和独立端口拆分塞进同一个 PR | story 与 training 可以分别在 `3000/3001` 独立启动；story app 不再注册 training route/`TrainingFlowProvider`；training app 不再引用 `GameFlowContext` 或 story runtime hook；story/training 主链路 smoke 都通过 |

### 前端实施顺序
1. 先做 `PR-FE-06B`，先收口恢复事实源和主流程编排。
2. 再做 `PR-FE-06C`，把 DTO 消费边界收紧，阻断页面层脏字段扩散。
3. 然后做 `PR-FE-07A`，在稳定的会话事实源和 DTO 边界上继续打磨洞察页。
4. 最后做 `PR-FE-07B`，把 training 从 story 单应用中物理拆出为独立前端端口，同时把 story 主线复原为不受 training 污染的独立 app 壳层。

### 前端拆分理由
- `PR-FE-06B` 只解决“状态从哪里来”，避免恢复逻辑和展示逻辑再搅在一起。
- `PR-FE-06C` 只解决“页面读什么字段”，避免页面和 normalizer 双重兼容。
- `PR-FE-07A` 只解决“洞察页如何稳定消费”，避免 report/progress/diagnostics 再去反向影响训练主流程。
- `PR-FE-07B` 只解决“应用从哪里启动、路由和 Provider 怎么分域”，避免训练前端继续寄生在 story app 里，导致端口分离了但业务边界没有分离。

## 推荐并行方式
- 后端开发者优先负责 `PR-BE-07B` 与 `PR-BE-07C`，前端开发者优先负责 `PR-FE-06B`。
- `PR-FE-06C` 必须在 `PR-BE-07C` 的字段和错误契约不再漂移后再合并，避免前端刚收口又被接口打回。
- `PR-BE-08A` 可以与 `PR-FE-07A` 并行，因为一个负责发布链路，一个负责页面消费层，写集基本可分离。
- `PR-FE-07B` 可以在 `PR-FE-07A` 收口后与 `PR-BE-08A` 部分并行，因为它主要影响前端入口、路由、Provider 和端口配置，不直接改变训练 API 契约。
- `PR-BE-08B` 应与 `PR-FE-07B` 配对推进：前端负责双入口/双端口壳层，后端负责双 origin、联调契约和运行配置；两边都不应借机改动 story/training 核心业务逻辑。

## 不建议的拆法
- 不要把 `query 恢复语义`、`错误契约`、`迁移脚本` 放进同一个后端 PR。
- 不要把 `训练主流程拆分`、`DTO 字段收口`、`报告页视觉改动` 放进同一个前端 PR。
- 不要再出现“前端为了兼容后端未收口字段而在页面层继续兜底”的做法。
- 不要把真实 DB smoke 和业务字段重构放在同一提交里，否则一旦失败无法快速定位是迁移链路问题还是领域逻辑问题。
