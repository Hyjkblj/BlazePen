# BlazePen 训练前后端整合开发完整 PR 规划

- 更新日期: `2026-03-23`
- 适用范围: `training` 主线，采用前后端一体化联动开发，不再沿用“前端 PR / 后端 PR 长期并行、最后再对接”的方式。
- 目标文档:
  - `docs/烽火笔锋_当前训练系统架构设计.md`
  - `docs/烽火笔锋_抗战记者KT训练系统方案.md`
  - `docs/BlazePen_训练后端完成与前端解耦阶段PR规划.md`
  - `docs/BlazePen_PR任务拆分与Review执行清单.md`
  - `docs/runbooks/story_training_dual_backend_runbook.md`
  - `docs/frontend/Frontend_状态职责与命名基线.md`

## 1. 这份规划解决什么问题

当前仓库已经不是“训练从零开始”的状态，而是已经具备了独立训练前端、独立训练后端、独立训练路由、训练读写分层和训练报告页雏形。问题不在于有没有模块，而在于还没有把这些模块收口成一个可稳定联调、可恢复、可提交、可解释、可回归的完整训练产品。

因此，本规划不再按“前端先解耦、后端先实现、最后对接”推进，而是按垂直切片拆成一组可以直接联调、直接验收、直接回滚的整合 PR。每个 PR 都允许同时改前端和后端，但必须满足三个条件：

1. 只交付一个完整用户能力，不混多个主目标。
2. 前端和后端围绕同一份契约落地，不留“等对方再适配”的半成品。
3. 单个 PR 可以独立回滚，不把多个切片捆成一个大分支。

## 2. 当前代码基线

### 2.1 已经落地的结构事实

训练前端已经独立成单独应用和单独端口：

- `frontend/src/apps/training/AppTraining.tsx`
- `frontend/src/router/trainingRouter.tsx`
- `frontend/vite.training.config.ts`
- 默认训练前端端口: `3001`
- 默认训练后端目标: `http://localhost:8010`

训练后端已经独立成单独入口和单独路由域：

- `backend/run_training_api.py`
- `backend/api/routers/training.py`
- 路由前缀: `/v1/training`
- 默认训练后端端口: `8010`

训练前端主流程已经具备基础闭环：

- `frontend/src/flows/useTrainingMvpFlow.ts`
- `frontend/src/hooks/useTrainingSessionBootstrap.ts`
- `frontend/src/hooks/useTrainingRoundRunner.ts`
- `frontend/src/hooks/useTrainingReadQuery.ts`
- `frontend/src/pages/Training.tsx`
- `frontend/src/pages/TrainingProgress.tsx`
- `frontend/src/pages/TrainingReport.tsx`
- `frontend/src/pages/TrainingDiagnostics.tsx`
- `frontend/src/services/trainingApi.ts`

训练后端已经有明确的读写分层：

- 写路径编排: `backend/api/services/training_service.py`
- 读模型查询: `backend/training/training_query_service.py`
- 输出装配: `backend/training/training_outputs.py`
- 持久化适配: `backend/training/training_store.py`

当前代码已经明确区分 story 与 training：

- story 只使用 `threadId`
- training 只使用 `sessionId`
- 双前端和双后端可以并行启动
- 运行方式已有 runbook，不需要再回到单端口、单服务混跑

### 2.2 当前已经具备但还未“完成”的能力

已经具备：

1. 训练初始化 `init`
2. 下一场景获取 `next`
3. 回合提交 `submit`
4. 会话摘要恢复 `session summary`
5. 进度查询 `progress`
6. 历史查询 `history`
7. 报告查询 `report`
8. 诊断查询 `diagnostics`

尚未收口为完整产品的点：

1. `frontend/src/flows/useTrainingMvpFlow.ts` 仍然是偏大的应用层流程，初始化、恢复、提交、展示状态仍然过度集中。
2. 恢复路径仍然携带 `characterId` 的本地缓存语义，说明训练恢复的事实源还没有完全收束到服务端。
3. 后端输出层仍保留 `briefing` 兼容字段，说明训练契约还没有完全冻结到 canonical `brief`。
4. 训练读模型虽然已经独立，但还需要统一冻结 `character_id / player_profile / runtime_state / progress_anchor` 这一组产品级读模型字段。
5. 训练报告页已经存在，但还需要补齐真正面向用户的完成态，而不是只把后端结果渲染出来。
6. 训练“剧情影响/分支影响”已经有 `decisionContext / consequenceEvents / branchTransition` 结构基础，但还没有完全形成稳定的产品链路。
7. smoke、自检、迁移、观测和发布回归还没有作为训练主线的最终准入门槛收口。

## 3. 训练完整模式定义

本规划默认的训练完成态，不是“能打开一个训练页面”，而是下面这条完整链路：

1. 玩家以记者或其他训练角色进入训练。
2. 训练由六个大历史锚点场景和多个小场景分支构成。
3. 大历史事件必须固定锚定，不能被玩家改写。
4. 玩家每一轮决策会影响下一步的小场景分支、风险状态、能力状态、后续推荐和最终报告。
5. 训练引擎同时保留规则评估和 LLM 评估，不允许仅凭 message 文本判断业务结果。
6. 刷新、重进、重复提交、提交失败、下一场景拉取失败都可以恢复到服务端权威状态。
7. 训练结束后可以生成完整报告，至少包含能力变化、状态变化、关键证据、风险分布、分支转移摘要和复盘建议。

换句话说，训练完整模式的核心不是“剧情能跑”，而是：

- 有稳定事实源
- 有清晰契约
- 有可恢复模型
- 有可解释报告
- 有可回归测试

## 4. 架构与开发原则

### 4.1 前端原则

1. 严守 `pages / flows / hooks / services / storage / contexts` 边界。
2. 页面层不直接消费脏字段，不直接兼容后端历史残留字段。
3. `storage` 只做 UX 提示和手动恢复入口，不得成为训练会话事实源。
4. 训练主线不得回退去复用 story 的运行时会话状态或恢复逻辑。
5. 训练主流程可以拆分多个 hook，但不能再制造新的巨型 hook。

### 4.2 后端原则

1. 严守 `routers / services / repository-store / policy / async-task / dto` 边界。
2. GET 读路径不得修数据、补数据、写数据。
3. `TrainingService` 不得继续膨胀成巨型 service。
4. 不允许把会话真相长期放在进程内内存中。
5. 报告、图片、音频等重任务不得无控制地塞进同步热路径。

### 4.3 整合 PR 原则

1. 允许一个 PR 同时改前端和后端。
2. 但每个 PR 只对应一个可验收用户能力。
3. 一个 PR 只冻结一组契约，不允许多个契约面同时漂移。
4. Review 仍需按“前端 / 后端”两个部分分别审。
5. 单个 PR 的完成标准必须包含代码、测试、联调、回滚点。

## 5. PR 编号与执行方式

本轮训练整合开发不再沿用 `PR-FE-XX / PR-BE-XX` 的拆分方式，改为使用一组训练垂直切片编号：

- `PR-TRN-01` 到 `PR-TRN-07`

单个 PR 的推荐提交顺序：

1. 先提交后端契约或读写边界改动。
2. 再提交前端消费与页面行为改动。
3. 最后补测试、runbook、联调说明。

分支策略：

1. 一个 PR 一条分支。
2. 不允许在一个分支里串多个 `PR-TRN-XX`。
3. 如发现某个 PR 过大，应继续在该 PR 内按“契约冻结 / 产品接入 / 测试补齐”拆 commit，而不是继续扩大 PR 目标。

## 6. 整合 PR 总表

| PR | 主题 | 目标 | 依赖 |
| --- | --- | --- | --- |
| `PR-TRN-01` | 契约冻结与身份边界冻结 | 冻结训练 canonical DTO、`sessionId` 边界和 canonical 字段集 | 无 |
| `PR-TRN-02` | 初始化与恢复链路收口 | 建立服务端权威恢复模型，去掉本地缓存对恢复决策的主导 | `PR-TRN-01` |
| `PR-TRN-03` | 提交链路、下一场景与幂等保护 | 稳定回合提交、重复提交、失败恢复和下一场景流转 | `PR-TRN-02` |
| `PR-TRN-04` | 训练读模型冻结与洞察页收口 | 让 `progress / history / diagnostics / report` 成为前端可直接消费的稳定读模型 | `PR-TRN-03` |
| `PR-TRN-05` | 报告页产品化完成 | 交付真正可用的训练报告页和完成态 | `PR-TRN-04` |
| `PR-TRN-06` | 分支影响复原与自适应闭环 | 补齐玩家决策对训练路径的影响展示与解释闭环 | `PR-TRN-05` |
| `PR-TRN-07` | 观测、smoke、迁移与发布收口 | 让训练主线具备持续联调、持续回归和上线准入条件 | `PR-TRN-06` |

## 7. 详细 PR 规划

### PR-TRN-01 契约冻结与身份边界冻结

**目标**

把训练前后端的对外契约冻结成一套稳定模型，先解决“字段到底是什么、身份到底怎么传、页面到底该消费什么”的问题。

**前端范围**

1. 收口 `frontend/src/types/training.ts`，只保留前端真正消费的 canonical 类型。
2. 收口 `frontend/src/services/trainingApi.ts` 和 `frontend/src/utils/trainingSession.ts`，把历史兼容集中在 `service/normalizer`，不向页面层继续扩散。
3. 核查训练页面和 hooks 不再直接使用任何 `threadId` 语义。
4. 把场景正文统一消费 `brief`，禁止页面和 flow 层再关心 `briefing`。
5. 冻结训练会话最小事实字段：`sessionId / trainingMode / status / roundNo / totalRounds / playerProfile / runtimeState / progressAnchor`。

**后端范围**

1. 收口 `backend/api/schemas.py` 中训练相关 request/response DTO。
2. 收口 `backend/training/training_outputs.py` 中训练场景、会话摘要、进度、历史、报告、诊断的输出结构。
3. 明确 `sessionId` 是训练唯一会话标识，不接受 story `threadId` 兼容输入。
4. 把 `character_id` 纳入训练读模型的正式字段集，不能再依赖前端缓存补齐。
5. 明确 `brief` 为 canonical 字段，`briefing` 降级为过渡兼容字段，并标记最终移除计划。

**明确不做**

1. 不修改训练业务流程。
2. 不做恢复策略重构。
3. 不做报告页面视觉重做。

**验收条件**

1. 训练前端所有页面、flows、hooks 只消费 canonical training types。
2. 训练前端代码中除测试外，不再依赖 `briefing`。
3. 训练后端所有训练接口都不再混入 `threadId` 兼容语义。
4. `session summary / progress / history / report / diagnostics` 的最小公共字段集一致。

**必须补的测试**

前端：

1. `trainingApi` normalizer 测试，覆盖 `briefing -> brief` 兼容收口。
2. 类型与 normalizer 测试，覆盖 `sessionId / playerProfile / runtimeState` 的稳定映射。

后端：

1. 训练 DTO contract tests。
2. `training_outputs` 输出一致性测试。
3. 路由参数边界测试，确保 training 不接收 story 身份语义。

**合并门槛**

1. 合并后不允许再新增页面层脏字段兼容。
2. 合并后所有后续 PR 都必须建立在这套 canonical DTO 上。

### PR-TRN-02 初始化与恢复链路收口

**目标**

把训练的初始化、刷新、重进、恢复、完成态恢复统一收口到服务端事实源，不让 local storage 再参与“会话真假判断”。

**前端范围**

1. 重构 `frontend/src/hooks/useTrainingSessionBootstrap.ts`。
2. 重构 `frontend/src/hooks/useTrainingSessionViewModel.ts`。
3. 收口 `frontend/src/storage/trainingSessionCache.ts`，降级为 UX 提示和手动恢复入口。
4. 在 `frontend/src/flows/useTrainingMvpFlow.ts` 中去掉本地缓存主导的恢复推断。
5. 让 `characterId` 优先来自服务端会话摘要或初始化响应，而不是本地草稿和本地缓存。

**后端范围**

1. 固化 `TrainingQueryService.get_session_summary()` 的恢复读模型职责。
2. 保证恢复接口只读，不修数据，不补写。
3. 确保会话摘要中包含恢复所需的完整最小事实：`status / current_round_no / total_rounds / resumable_scenario / scenario_candidates / runtime_state / player_profile / character_id`。
4. 明确 completed / not-found / corrupted-recovery-state 的错误码与返回语义。
5. 验证训练恢复不依赖进程内临时状态。

**明确不做**

1. 不修改提交链路。
2. 不修改报告内容。

**验收条件**

1. 刷新训练主页后，能仅凭服务端会话摘要恢复到正确训练状态。
2. completed 会话进入训练页时不会回到可继续提交的错误状态。
3. 会话不存在、会话损坏、恢复失败都有稳定错误分支。
4. local storage 即使被清空，也不影响已有 `sessionId` 会话的服务端恢复。

**必须补的测试**

前端：

1. `useTrainingSessionBootstrap` 恢复路径测试。
2. `useTrainingSessionViewModel` 读目标优先级测试。
3. 训练页刷新恢复集成测试。

后端：

1. `session_summary` route/service/store 测试。
2. corrupted state 边界测试。
3. completed 会话恢复测试。

**合并门槛**

1. `resumeTarget` 只能做提示，不得继续决定当前 live session 真相。
2. 前端训练恢复必须能脱离本地缓存工作。

### PR-TRN-03 提交链路、下一场景与幂等保护

**目标**

稳住训练热路径，即“提交本轮 -> 更新状态 -> 拉取下一场景 / 进入完成态”的主链路，避免重复提交、并发提交、失败回退不一致。

**前端范围**

1. 收口 `frontend/src/hooks/useTrainingRoundRunner.ts`。
2. 在 `frontend/src/flows/useTrainingMvpFlow.ts` 中拆出提交态与恢复态，避免所有逻辑压在一个 flow 里。
3. 训练页提交按钮需要显式防重入、防双击、防多次重试。
4. 提交失败、下一场景拉取失败、发现 duplicate submit、发现 completed session 都必须走 typed branch，而不是 message 文本匹配。

**后端范围**

1. 收口 `TrainingService.submit_round()` 的幂等与重复提交保护。
2. 固化 `scenario/next` 的只读边界，不允许借 GET/查询动作修改进度。
3. 明确回合校验：当前回合、当前场景、completed session、重复提交等错误必须有稳定错误码。
4. 保证提交成功后数据库状态和返回结果一致，不允许“写成功但返回假失败”导致前端继续补写。
5. 补齐当前回合与下一场景之间的边界测试。

**明确不做**

1. 不做训练报告页完善。
2. 不做场景推荐策略升级。

**验收条件**

1. 双击提交不会产生重复 round。
2. 网络抖动导致前端重试时，不会重复落库。
3. 下一场景拉取失败时，前端可以按服务端权威状态恢复，而不是停留在半完成状态。
4. completed session 不再允许继续提交。

**必须补的测试**

前端：

1. 提交防重入测试。
2. duplicate submit 恢复测试。
3. submit 成功但 next 获取失败后的恢复测试。

后端：

1. `submit_round` 幂等测试。
2. 重复提交测试。
3. completed session 提交拒绝测试。
4. `scenario/next` 边界测试。

**合并门槛**

1. 提交主链路必须成为训练最稳定的一条路径。
2. 合并后禁止再用 message 文本判断 duplicate/completed/restore 语义。

### PR-TRN-04 训练读模型冻结与洞察页收口

**目标**

让训练洞察页直接消费服务端读模型，不再让前端自己重算一套“伪报告”和“伪进度”。

**前端范围**

1. 统一 `frontend/src/hooks/useTrainingReadQuery.ts` 和训练洞察页查询约定。
2. 收口 `TrainingProgress`、`TrainingReport`、`TrainingDiagnostics` 的加载、空态、失败、重试、直接访问路径。
3. 允许直接通过 `sessionId` 打开进度页、报告页、诊断页。
4. 页面层只做展示映射，不再重新扫描历史自己推导关键统计值。

**后端范围**

1. 冻结 `TrainingQueryService` 的四类稳定读模型：
   - `session summary`
   - `progress`
   - `history`
   - `diagnostics`
   - `report`
2. 补齐训练读模型的产品字段，而不是只返回内部中间结果。
3. 把场景标题、branch transition、风险分布、能力观察等展示必需字段纳入正式读模型。
4. 防止 query service 回退到“查询时顺便修状态”的坏模式。

**明确不做**

1. 不改训练推荐算法。
2. 不做报告视觉重构。

**验收条件**

1. `progress / report / diagnostics` 可以独立打开并完成刷新恢复。
2. 页面不再依赖读取 raw history 后二次重算关键摘要。
3. query/read-model 边界稳定，不引入 GET 写库副作用。

**必须补的测试**

前端：

1. 三个洞察页直达访问测试。
2. 洞察页空态、失败态、未完成会话态测试。

后端：

1. `TrainingQueryService` 读模型测试。
2. report/history/diagnostics DTO 一致性测试。
3. query path 不写库的保护测试。

**合并门槛**

1. 洞察页必须变成标准读模型消费者。
2. 所有训练读页面必须共享同一套读取入口和错误语义。

### PR-TRN-05 报告页产品化完成

**目标**

把现有 `TrainingReport.tsx` 从“能显示数据”推进到“能交付用户的完整训练报告”。

**前端范围**

1. 收口 `frontend/src/pages/TrainingReport.tsx`，必要时拆到 `components/training/report/*`。
2. 报告页至少完成以下模块：
   - 总结摘要
   - 能力雷达
   - 状态雷达
   - 成长曲线
   - 高风险回合摘要
   - 关键证据与复盘建议
   - 分支转移摘要
3. 未完成会话、空报告、报告加载失败要有明确产品反馈。

**后端范围**

1. 冻结报告输出结构。
2. 如果报告装配成本变高，则把重计算前移到提交完成时或落成稳定工件，不把未来可能的重任务塞进同步 GET 热路径。
3. 确保报告输出直接服务页面，不要求页面再拼装二次结构。

**明确不做**

1. 不做教师端、管理端导出。
2. 不做图片、音频、PDF 生成。

**验收条件**

1. 完成训练后，报告页能稳定展示用户完整结果。
2. 报告页展示内容和后端读模型一一对应，没有页面自己补业务语义。
3. 报告页刷新不丢失状态，不依赖前一个页面内存。

**必须补的测试**

前端：

1. 报告页渲染测试。
2. 完成态、未完成态、失败态测试。
3. 报告核心区块快照或结构测试。

后端：

1. 报告装配策略测试。
2. report route contract tests。
3. 报告摘要字段回归测试。

**合并门槛**

1. 报告页达到用户可读、可解释、可复盘，而不是仅技术调试页。

### PR-TRN-06 分支影响复原与自适应闭环

**目标**

补齐训练最关键的产品差异化能力：玩家决策会影响训练路径，但历史大事件仍固定锚定；系统要能把这种影响展示出来，也要能解释为什么推荐下一场景。

**前端范围**

1. 在训练主页面、进度页和报告页展示 `decisionContext / consequenceEvents / branchTransition`。
2. 让用户能看见：
   - 本轮选择了什么
   - 推荐本来是什么
   - 为什么偏离
   - 偏离后引发了哪些后果
   - 之后进入了哪条分支
3. 把“剧情影响”还原为训练产品语义，而不是继续停留在内部字段存在但页面无展示的状态。

**后端范围**

1. 固化训练的 branch transition 与 consequence event 产出。
2. 保证六个大历史场景是固定锚点，小场景和路径分支可变。
3. 自适应模式下，推荐策略、候选池、最终选中项、分支跳转和原因解释要形成完整链路。
4. 把 branch transition 纳入 report 和 diagnostics 的正式统计口径。

**明确不做**

1. 不引入新的故事会话模型。
2. 不把 training 和 story 后端重新混回一个会话体系。

**验收条件**

1. 玩家决策对训练路径的影响可以在页面上被明确看见。
2. 六个大历史锚点固定不变，小场景和路径分支可变化。
3. 报告可以解释训练为何走到了当前路径，而不是只给最终分数。

**必须补的测试**

前端：

1. 分支影响展示测试。
2. 推荐与实际选择偏差展示测试。
3. consequence events 展示测试。

后端：

1. branch transition policy tests。
2. recommendation log 与 diagnostics 汇总测试。
3. 历史锚点固定、分支路径可变的策略测试。

**合并门槛**

1. 训练必须从“顺序答题”升级为“有分支影响、可解释路径”的训练系统。

### PR-TRN-07 观测、smoke、迁移与发布收口

**目标**

把训练主线收口到可持续开发、可持续联调、可持续发布的程度。

**前端范围**

1. 补齐训练主链路 smoke。
2. 补齐训练洞察页 smoke。
3. 固化 `npm run dev:training`、`npm run dev:all`、训练测试命令与联调说明。
4. 关键页面补用户路径级回归用例。

**后端范围**

1. 补齐训练服务的结构化日志、trace、错误上下文。
2. 补齐训练独立入口、健康检查、最小回归命令、自检脚本。
3. 如果训练 schema 有变更，补齐迁移和回滚说明。
4. 在确认前端不再消费后，正式移除 `briefing` 这类训练 legacy 契约残留字段。

**明确不做**

1. 不新增业务功能。
2. 不改动训练产品逻辑。

**验收条件**

1. 训练前后端可以按 runbook 稳定启动。
2. 训练主链路、洞察页、报告页都有最小 smoke 保障。
3. 训练相关契约残留字段完成清退。
4. 上线前可以用统一命令完成最小自检。

**必须补的测试**

前端：

1. `TrainingMainPathSmoke.integration.test.tsx`
2. 进度/报告/诊断页 smoke
3. 训练恢复主路径 smoke

后端：

1. route smoke
2. query/read-model smoke
3. entrypoint/runbook 自检测试
4. migration / rollback 验证

**合并门槛**

1. 没有 smoke 和自检，不算训练主线完成。

## 8. PR 之间的关键依赖关系

### 8.1 不能跳过的顺序

1. `PR-TRN-01` 必须先做，否则后续恢复、洞察、报告会继续建立在漂移契约上。
2. `PR-TRN-02` 必须早于 `PR-TRN-05`，否则报告页仍会受错误恢复模型污染。
3. `PR-TRN-03` 必须早于 `PR-TRN-06`，否则“分支影响”建立在不稳定提交链路上，没有意义。
4. `PR-TRN-04` 必须早于 `PR-TRN-05`，否则报告页没有稳定读模型基座。
5. `PR-TRN-07` 必须最后做，因为它是收口，不是开路。

### 8.2 可以局部并行但不建议拆开的内容

1. `PR-TRN-02` 中前端恢复重构和后端恢复读模型必须同 PR 联动完成，不建议再拆开。
2. `PR-TRN-03` 中前端提交态改造和后端幂等保护必须同 PR 联动完成，不建议再拆开。
3. `PR-TRN-05` 中报告输出结构和报告页模块化必须同 PR 联动完成，不建议再拆开。

## 9. 每个整合 PR 的统一模板要求

每个 `PR-TRN-XX` 描述至少包含以下内容：

1. 本次目标
2. 前端范围
3. 后端范围
4. 明确不做
5. 契约变化
6. 验收条件
7. 前端测试
8. 后端测试
9. 风险
10. 回滚方式
11. 需要 reviewer 重点看的前端问题
12. 需要 reviewer 重点看的后端问题

Review 输出格式仍建议保持：

```md
## 前端 Findings
## 后端 Findings
## Open Questions
## 测试缺口
## Review Summary
```

## 10. 当前不建议再做的事情

1. 不要再把训练拆回“前后端长期并行、最后再对接”的排期。
2. 不要为了省事把 story 的 `threadId` 语义重新带回 training。
3. 不要让页面直接兼容后端脏字段。
4. 不要让 `useTrainingMvpFlow.ts` 继续无限增大。
5. 不要让 local storage 再承担恢复事实源。
6. 不要在 GET 路由上做状态修复。
7. 不要把未来的报告生成、媒体生成、导出生成塞进同步热路径。

## 11. 训练整合完成的最终判定标准

只有同时满足以下条件，才算“训练前后端整合完成”：

1. 训练前端和训练后端都能独立启动，并按 runbook 联调。
2. 训练会话以 `sessionId` 为唯一事实标识，恢复由服务端读模型主导。
3. 初始化、恢复、提交、下一场景、完成态、失败态、重复提交都稳定。
4. `progress / history / diagnostics / report` 全部建立在稳定读模型上。
5. 玩家决策对训练路径的影响可见、可解释、可进入最终报告。
6. 训练报告达到用户可读、可复盘，而不是调试面板。
7. smoke、自检、回归、迁移和回滚说明齐备。

## 12. 结论

训练主线现在最适合的推进方式，不是再做一轮“先前端、先后端、最后对接”的并行排期，而是按本文件定义的 `PR-TRN-01` 到 `PR-TRN-07` 做前后端一体化垂直切片开发。这样做的价值很直接：每个 PR 都是一个真实可运行能力，而不是一半前端、一半后端的中间态；每个 PR 都能独立 review、独立回滚、独立验收；训练主线最终交付的是完整产品链路，而不是接口和页面的松散拼装。
