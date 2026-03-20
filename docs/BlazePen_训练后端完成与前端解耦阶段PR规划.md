# BlazePen 训练后端完成与前端解耦阶段 PR 规划
更新日期：2026-03-20

## 1. 现阶段目标

本阶段目标不是同时把训练前后端一次性做成完整产品，而是分成两条独立执行线：

1. 后端：把训练主线补齐到“可独立承诺、可恢复、可诊断、可测试”的稳定服务阶段。
2. 前端：继续完成故事主线的解耦收口，并把应用壳层、状态边界、契约消费方式整理到“可以开始开发训练前端”的阶段。

本阶段完成后，应达到：

1. 训练后端不再依赖前端猜测字段或 message 文本承载业务语义。
2. 前端已经具备清晰的 story/training 边界，后续可以在不污染故事主线的前提下开发训练页面。
3. `threadId` 和 `sessionId` 在前后端都不再混用。
4. localStorage/sessionStorage 只承担 UX 缓存职责，不承担故事或训练会话事实源职责。

## 2. 本阶段不做

1. 不在一个 PR 中同时推进训练后端闭环、训练前端页面、故事主线重构和视觉改版。
2. 不把“前端可开始开发训练页面”误判成“训练前端 MVP 已完成”。
3. 不继续扩故事新玩法、新页面或新媒体热路径。
4. 不让训练前端直接复用故事运行时 hook、story session 状态或 story 专用恢复逻辑。

## 3. 规划原则

1. 继续沿用现有 `PR-BE-XX / PR-FE-XX` 编号体系，不重置历史编号。
2. 前后端 PR 必须分开提交、分开 Review、分开验收。
3. 故事主线的恢复、history、ending 契约必须先收口，再开始训练前端壳层准备。
4. 后端训练服务必须按 `routers / services / repository-store / policy / dto` 分层推进，不回灌巨型 service。
5. 前端必须按 `pages / flows / hooks / services / storage / contexts` 分层推进，不把训练逻辑塞回故事 hook 或页面。

## 4. 阶段完成定义

### 4.1 后端完成定义

后端只有在以下条件都满足后，才算“训练服务完成”：

1. 训练主链路 `init / next / submit / progress / report / diagnostics` 对外契约稳定。
2. 训练会话存在明确恢复模型，前端刷新后可以依据服务端事实继续读取当前进度。
3. 训练回合提交具备幂等保护和重复提交保护。
4. 训练报告、诊断、进度返回的是产品可消费 DTO，而不是原始内部 payload。
5. 训练路由、service、repository、集成测试形成基础回归保护。

### 4.2 前端完成定义

前端只有在以下条件都满足后，才算“已到可开发训练前端阶段”：

1. 故事主线恢复策略已退出页面和 hook 的自编排，服务端快照成为唯一恢复事实源。
2. 故事 ending/history 已切到 canonical route，页面不再消费 legacy 脏契约。
3. 前端已建立训练专用 `services / types / flows / contexts` 入口，不与 story 运行时状态混用。
4. 路由和页面壳层已能容纳训练入口与训练流程开发，但不要求本阶段做完整训练 MVP 页面。

## 5. 总体执行顺序

### 阶段 A：先收口故事主线阻塞项

1. `PR-BE-05` 收尾
2. `PR-FE-03` 收尾
3. `PR-FE-04` 收尾
4. `PR-FE-05` 收尾

说明：

1. 这是训练前端准备阶段的硬前置。
2. 如果故事恢复、history、ending 契约还不稳定，训练前端接入会继续建立在错误边界上。

### 阶段 B：后端完成训练服务闭环

1. `PR-BE-06`
2. `PR-BE-07`
3. `PR-BE-08`

### 阶段 C：前端完成训练开发基线准备

1. `PR-FE-06`

说明：

1. 本阶段前端终点是“训练可开发”，不是“训练前端已交付”。
2. 真正的训练前端 MVP 和训练报告/诊断页面，应作为下一阶段单独规划。

## 6. 后端 PR 拆分

| PR-ID | 名称 | 目标 | 主要范围 | 明确不做 | 依赖 |
| --- | --- | --- | --- | --- | --- |
| PR-BE-05 | 故事 query/recovery 收尾 | 关闭 story 查询侧与恢复侧对训练前端准备的阻塞 | recent sessions latest snapshot 查询收口、`/sessions` ownership/policy、history/ending/snapshot 契约测试补齐 | 不扩故事新功能 | PR-BE-04 |
| PR-BE-06 | 训练会话生命周期与提交契约完成 | 把训练主链路补齐为稳定外部服务 | `init / scenario/next / round/submit` 契约冻结，`sessionId` 唯一标识，提交幂等、重复提交保护、恢复所需会话读取接口补齐 | 不做训练前端页面 | PR-BE-02, PR-BE-05 |
| PR-BE-07 | 训练查询、报告与诊断服务完成 | 把训练查询侧补齐为前端可直接消费的服务层 | `progress / report / diagnostics / history / session summary` 的 DTO 收口，query service 与 repository-store 边界稳定化 | 不做 BI 平台化分析 | PR-BE-06 |
| PR-BE-08 | 训练后端观测性与回归收口 | 让训练服务达到可持续发布和回归的程度 | 结构化日志、traceId、错误上下文、迁移约束、route/service/repository/integration 测试、主链路 smoke | 不做前端接入 | PR-BE-07 |

### 6.1 PR-BE-05 合并门槛

1. `recent sessions` 不再通过扫描整段 snapshot 历史后在 Python 侧去重来求 latest snapshot。
2. `/api/v1/game/sessions?user_id=` 的 ownership/policy 有明确决定，并落实到 route 与测试。
3. story `history / ending / snapshot` 对外错误码和 DTO 稳定。

### 6.2 PR-BE-06 交付内容

1. 明确训练主链路的 canonical API：
   - `POST /v1/training/init`
   - `POST /v1/training/scenario/next`
   - `POST /v1/training/round/submit`
2. 明确训练前端后续开发所需的恢复读取接口，至少覆盖：
   - 会话摘要
   - 当前进度锚点
   - 当前轮次或可继续场景信息
3. `sessionId` 成为训练唯一会话标识，不接受任何 story `threadId` 兼容输入。
4. 训练回合提交具备幂等保护和重复提交保护，并有明确错误码。
5. 错误处理继续使用结构化 error code，不回退到 message 文本判定。

### 6.3 PR-BE-07 交付内容

1. `progress / report / diagnostics / history / session summary` 形成稳定 DTO。
2. 报告与诊断聚合逻辑继续留在训练域 policy/query service，不回灌 `TrainingService`。
3. 对前端暴露的是展示友好的结构，不直接暴露 recommendation、audit、observation 的原始内部拼装结果。
4. 为后续训练前端页面提供明确读取模型，而不是让前端自己从 history 重扫计算。

### 6.4 PR-BE-08 交付内容

1. 主链路结构化日志补齐：
   - 初始化训练
   - 获取下一场景
   - 提交回合
   - 读取进度
   - 读取报告
   - 读取诊断
2. traceId、错误上下文、关键输入上下文进入标准 error envelope。
3. 训练主链路有基础 route/service/repository/integration 回归。
4. 数据迁移和回滚边界明确，不让训练域表结构变更继续处于“只靠人工约定”状态。

## 7. 前端 PR 拆分

| PR-ID | 名称 | 目标 | 主要范围 | 明确不做 | 依赖 |
| --- | --- | --- | --- | --- | --- |
| PR-FE-03 | 前端解耦合与职责收敛收尾 | 把 story 运行时从“hook 已拆分”推进到“边界已稳定” | `useStoryTurnSubmission` 不再自编排恢复；页面、flow、hook、service 职责继续收口 | 不做训练页面 | PR-FE-02 |
| PR-FE-04 | 前端会话状态与服务端快照接管收尾 | 让服务端快照成为故事恢复单一事实源 | expired/not-found 恢复决策下沉，storage 降级为 UX 缓存，本地只读兜底语义稳定 | 不做训练接入 | PR-FE-03, PR-BE-05 |
| PR-FE-05 | 故事主线恢复、history、ending 产品收尾 | 完成 story 产品层对 canonical route 的消费 | canonical ending/history route 接入，transcript 与 server history 语义明确，页面级回归测试补齐 | 不做训练页面 | PR-FE-04, PR-BE-05 |
| PR-FE-06 | 训练接入前前端壳层与契约准备 | 把前端整理到“可开始开发训练页面”的状态 | `trainingApi.ts`、训练 DTO/normalizer、训练专用 flow/context、训练路由壳层、`sessionId` 类型边界 | 不做训练完整 MVP 页面，不做报告/诊断页面 | PR-FE-05, PR-BE-06 |

### 7.1 PR-FE-03 合并门槛

1. `useStoryTurnSubmission` 不再自编排 `initGame -> initializeStory` 恢复链路。
2. 恢复策略由结构化服务契约或专门 recovery service 承接，页面和 hook 只消费结果。
3. 页面不再直接兼容服务端脏字段。

### 7.2 PR-FE-04 合并门槛

1. 服务端 snapshot 成为恢复唯一事实源。
2. `storage` 只保留 UX 缓存与只读兜底职责，不再决定 live session 命运。
3. 刷新、失败、超时、恢复、只读降级路径有明确产品反馈。

### 7.3 PR-FE-05 交付内容

1. `ending` 完成从 legacy `/v1/game/check-ending/{threadId}` 到 canonical `/v1/game/sessions/{thread_id}/ending` 的迁移。
2. 页面明确区分：
   - 当前设备已加载 transcript
   - 服务端持久化 history
3. 页面级测试覆盖 ending/history 的成功、失败、重试、恢复场景。

### 7.4 PR-FE-06 交付内容

1. 新增训练专用服务与契约层：
   - `frontend/src/services/trainingApi.ts`
   - `frontend/src/types/training.ts`
   - 训练 DTO normalizer / serviceError 映射
2. 明确前端会话标识边界：
   - story 只使用 `threadId`
   - training 只使用 `sessionId`
3. 新增训练专用壳层与状态入口：
   - `flows/useTrainingSessionFlow.ts`
   - `contexts/trainingFlowCore.ts`
   - 训练页面壳层或路由占位页
4. 明确故事与训练的共享边界：
   - 允许复用基础展示组件
   - 不允许复用 story 业务 hook、story session store、story 恢复逻辑
5. 页面层不直接访问 storage API，不直接拼装训练接口 payload。

## 8. 并行执行建议

### 可以并行

1. `PR-BE-05` 与 `PR-FE-03 / PR-FE-04 / PR-FE-05` 可以并行，但必须围绕同一套 story canonical contract 收口。
2. `PR-BE-06` 可以在 `PR-BE-05` 接近完成时提前设计 DTO 和错误码，但不要提前把未冻结契约交给前端消费。

### 不建议并行

1. 不要在 `PR-FE-05` 未完成前直接开始训练前端页面开发。
2. 不要在 `PR-BE-06` 未冻结训练 session/round 契约前开始大规模训练前端联调。
3. 不要把训练报告/诊断页面和训练主流程接入放在同一个 PR。

## 9. Review 重点

### 9.1 后端 Review Focus

1. `TrainingService` 是否继续膨胀。
2. 训练会话、回合、快照、报告、诊断是否存在明确事实源。
3. 是否存在 `sessionId / threadId` 混用。
4. DTO 与错误码是否稳定。
5. 是否具备幂等保护、恢复模型和基础可观测性。

### 9.2 前端 Review Focus

1. story 与 training 的 `flows / hooks / services / contexts / storage` 是否分轨。
2. 是否仍存在双事实源或 localStorage 主导恢复。
3. 页面是否继续直接兼容后端脏字段。
4. 是否把训练业务建立在 story 运行时状态复用之上。
5. 是否已经形成训练接入壳层，而不是继续在故事页面里横向塞功能。

## 10. 下一阶段入口条件

只有在以下条件同时满足后，才进入“训练前端 MVP”阶段：

1. `PR-BE-05` 已完成。
2. `PR-FE-03 / PR-FE-04 / PR-FE-05` 已完成。
3. `PR-BE-06` 已完成，训练主链路契约已冻结。
4. `PR-FE-06` 已完成，前端 story/training 边界已建立。

下一阶段再启动：

1. 训练前端 MVP 页面开发。
2. 训练报告与诊断产品化页面。
3. 故事与训练统一产品壳层的进一步整合。

