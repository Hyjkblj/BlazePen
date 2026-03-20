# BlazePen PR 任务拆分与 Review 执行清单

- 文档版本: `v1.2`
- 更新日期: `2026-03-20`
- 关联主文档: `docs/BlazePen_前后端架构分析与开发规划.md`
- 状态评估基线: `0e7eda8 feat: split story query services and recovery UI`
- 使用目的: 将架构规划落成可执行的 PR 粒度、统一 review 口径与交付模板。

---

## 1. 使用方式

后续开发与 review 统一按以下方式执行:

1. 先确认当前开发属于哪一个任务包。
2. 再确认本次执行 PR 归属前端还是后端:
   - 前端使用 `PR-FE-XX`
   - 后端使用 `PR-BE-XX`
3. 如果一次需求同时涉及前后端，默认拆成配对 PR，而不是继续提交一个混合 PR。
4. 在新的分轨模板补齐前，先打开对应的 `docs/pr_templates/PR-XX_*.md` 作为任务包底稿，再按本清单补充 `FE/BE` 归属、配对 PR、契约影响和不做项。
5. 以 `.github/PULL_REQUEST_TEMPLATE.md` 作为提交模板。
6. 将本次真实改动回填到 PR 模板中。
7. review 时始终保留前端和后端两个部分输出；如果某一侧不在本次范围，明确写“本次不在 review 范围”或“未发现阻塞性问题”。

执行规则:

1. 如果一次开发跨越多个任务包，应拆成多个 PR，而不是在一个 PR 中混合推进。
2. 如果一次开发同时改动前端和后端，但两侧可以分开合并与回滚，则必须拆成 `FE` 和 `BE` 两个 PR。
3. 前端“解耦合/职责收敛”任务不允许夹带视觉改版、接口扩容和新业务功能。

---

## 2. 文件清单

### 2.1 通用模板

- `.github/PULL_REQUEST_TEMPLATE.md`

### 2.2 总览文档

- `docs/BlazePen_PR任务拆分与Review执行清单.md`

### 2.3 当前任务包模板

- `docs/pr_templates/PR-01_baseline-governance.md`
- `docs/pr_templates/PR-02_api-contract-standardization.md`
- `docs/pr_templates/PR-03_story-session-persistence.md`
- `docs/pr_templates/PR-04_story-domain-service-split.md`
- `docs/pr_templates/PR-05_frontend-session-state-refactor.md`
- `docs/pr_templates/PR-06_story-product-completion.md`
- `docs/pr_templates/PR-07_training-frontend-mvp.md`
- `docs/pr_templates/PR-08_training-report-diagnostics.md`
- `docs/pr_templates/PR-09_observability-release-regression.md`

说明:

1. 当前仓库里的模板仍按“聚合任务包”维护。
2. 本文档从现在开始按 `PR-FE-XX / PR-BE-XX` 执行。
3. 在新的分轨模板落地前，继续复用上述任务包模板，但 PR 标题、范围说明和 review 口径必须按本清单的前后端拆分方式执行。

---

## 3. 推荐 PR 顺序

### 3.1 拆分原则

任务包编号继续沿用主规划文档的 `PR-01 ~ PR-09` 语义，但执行层统一拆成前后端两条 PR 线:

1. 后端执行 PR 使用 `PR-BE-XX`
2. 前端执行 PR 使用 `PR-FE-XX`
3. 一个任务包如果同时涉及前后端，则拆成两个配对 PR
4. 只有纯单侧任务，才允许没有配对 PR

以下状态判断以 `0e7eda8` 和 `docs/reviews/2026-03-20_frontend_backend_split_review.txt` 为主，并额外计入当前工作区中 recent sessions latest snapshot 批量读取收尾改动。

### 3.2 后端线

| 执行 PR | 对应任务包 | 任务名 | 当前状态 | 已落地进展 | 当前主要风险/未完成项 | 下一步 | 依赖 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PR-BE-01 | PR-01 | 基线治理与命名规范（后端） | 已完成 | 术语、边界、review 口径已进入文档基线 | 后续新增 story/training 路由仍可能出现边界回退 | 继续作为 review 守线，不再扩范围 | 无 |
| PR-BE-02 | PR-02 | API 契约统一与错误模型标准化（后端） | 已完成 | DTO、错误码、响应 envelope、traceId 基线已建立 | 新 query route 仍需防止回退到 message 文本承载业务语义 | 新接口继续沿用 DTO/error code 规范，不再引入页面兼容字段 | PR-BE-01 |
| PR-BE-03 | PR-03 | 故事会话持久化与幂等化 | 已完成 | story session、snapshot、restore、幂等提交已成为故事主线基础设施 | 查询侧与 policy 侧还在 `PR-BE-05` 收尾 | 只补 query/read-model/test，不回头扩大会话事实源 | PR-BE-02 |
| PR-BE-04 | PR-04 | 故事域服务拆分与异步媒体流水线 | 主体已完成，收尾观察中 | `GameService` 已不再承担会话、回合、结局和媒体合同全部职责；`StorySessionService`、`StoryTurnService`、`StoryEndingService`、`StoryHistoryService` 已形成主边界；结局判断已回到持久化事实 | 后续 query/read-model 能力存在被重新倒灌到巨型 service 的风险；媒体异步链路仍需持续观察 | 保持 story query/read model 继续落在 `story/*service` 与 `repository-store` 边界 | PR-BE-03 |
| PR-BE-05 | PR-06 | 故事恢复、历史与结局后端支持 | 进行中 | `/sessions`、`/sessions/{thread_id}/history`、`/sessions/{thread_id}/ending` 已落地；恢复/查询 smoke 已补；当前工作区正在消除 recent sessions latest snapshot N+1 | `/api/v1/game/sessions?user_id=` ownership/policy 未明确；recent sessions read model 仍需批量 latest snapshot；需与前端收口 transcript 和 server history 语义 | 完成 policy 决策、批量查询优化、route/service/repository tests，再推进前端全量接入 | PR-BE-04, PR-FE-04 |
| PR-BE-06 | PR-07 / PR-08 | 训练前端接入支撑与报告 DTO 稳定化 | 未开始 | 无 | story 主线 query/recovery 未完全收口前，不宜并行扩训练契约 | 待 `PR-BE-05` 稳定后启动 | PR-BE-02 |
| PR-BE-07 | PR-09 | 后端观测性、发布治理与回归体系 | 未开始 | 无 | 结构化日志、trace、迁移规范、集成测试仍未系统收口 | 依赖 `PR-BE-05`、`PR-BE-06` 后统一推进 | PR-BE-05, PR-BE-06 |

### 3.3 前端线

| 执行 PR | 对应任务包 | 任务名 | 当前状态 | 已落地进展 | 当前主要风险/未完成项 | 下一步 | 依赖 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PR-FE-01 | PR-01 | 基线治理与命名规范（前端） | 已完成 | `pages / flows / hooks / services / storage / contexts` 边界已进入 review 基线 | 后续开发仍可能在页面层引入跨层兼容逻辑 | 继续作为 review 守线 | 无 |
| PR-FE-02 | PR-02 | 前端契约消费标准化 | 已完成主体 | normalizer、serviceError、snake_case 到 camelCase 的收敛方向已建立 | story read model 仍有 legacy contract 残留，尤其是 ending query 仍未完全切到 canonical route | 新增页面禁止直接兼容脏字段；继续把迁移留在 `services/normalizer` | PR-FE-01, PR-BE-02 |
| PR-FE-03 | 新增 | 前端解耦合与职责收敛 | 主体已落地，但不能视为完全收口 | story 运行时已拆出 `useStoryEnding`、`useStorySessionTranscript`、`useGameInit`、`useStorySessionRestore`、`useStoryTurnSubmission` 等职责单元；角色选择链路也已继续细分 | `useStoryTurnSubmission` 仍持有 `initGame -> initializeStory` 恢复编排，说明 hook/service 边界尚未完全稳定 | 先把恢复策略统一下沉为结构化契约或专门 recovery service，再判定本 PR 收口 | PR-FE-02 |
| PR-FE-04 | PR-05 | 前端会话状态重构与服务端快照接管 | 进行中 | 服务端快照恢复、active-session 与 resume-save 分层、本地只读兜底已进入代码事实 | expired/not-found 等恢复决策仍有一部分留在 hook fallback，服务端 snapshot 还不是唯一恢复事实源 | 改成 contract-driven recovery，页面和 hook 只消费结构化恢复结果 | PR-BE-03, PR-FE-03 |
| PR-FE-05 | PR-06 | 故事主线恢复、历史与结局产品完善 | 进行中 | transcript dialog 和 ending dialog 已有产品容器，恢复入口已开始产品化 | `frontend/src/services/gameApi.ts` 仍调用 legacy `/v1/game/check-ending/{threadId}`；前端还未真正消费 `/sessions/{thread_id}/history`；当前 transcript 只代表当前设备已加载消息 | 切换 canonical ending/history route，明确 transcript 与 history 语义，并补页面级回归 | PR-BE-05, PR-FE-04 |
| PR-FE-06 | PR-07 | 训练主线前端 MVP 接入 | 未开始 | 无 | story 主线会话、恢复、ending 未收口前不宜扩大范围 | 待 `PR-FE-04`、`PR-FE-05` 稳定后启动 | PR-BE-06, PR-FE-03 |
| PR-FE-07 | PR-08 | 训练报告与诊断产品化 | 未开始 | 无 | 依赖训练主线前端 MVP 和稳定 DTO | 待 `PR-FE-06` 完成后启动 | PR-BE-06, PR-FE-06 |
| PR-FE-08 | PR-09 | 前端观测性与回归体系 | 未开始 | 无 | story/training 主路径尚未全部稳定，不适合先做最终收口 | 依赖 `PR-FE-05`、`PR-FE-07`、`PR-BE-07` | PR-FE-05, PR-FE-07, PR-BE-07 |

### 3.4 前端新增解耦合任务说明

`PR-FE-03` 是在原始任务包基础上新增的前端结构治理任务，目标不是扩功能，而是把后续 `PR-FE-04 ~ PR-FE-07` 的实现风险提前消掉。

本任务必须覆盖:

1. `GameFlowContext` 收敛为跨页面入口态，不再承载过多运行时细节和存储细节。
2. `useGameInit`、`useGameSessionFlow`、`useGameState` 按“初始化 / 恢复 / 提交 / 展示状态 / 资源状态”拆分职责，避免继续膨胀。
3. 故事主线和训练主线的 `flows / hooks / services` 明确分轨，不共用一套可变业务状态。
4. 页面不再直接处理 restore/reselect/dirty field 兼容逻辑，统一下沉到 `services` 和 `normalizer`。
5. `storage` 只保留 UX 缓存职责，不再被 flow/hook 当成 live session 的事实源。
6. 巨型 hook、巨型流程脚本、上下文直出 storage API 的实现必须在这一阶段优先拆掉。

### 3.5 当前必须强调的问题（2026-03-20）

1. 不得把 `PR-FE-03` 标记为完成，除非 `frontend/src/hooks/useStoryTurnSubmission.ts` 不再自编排 `initGame -> initializeStory` 恢复链路。
2. 不得把 `PR-FE-05` 标记为完成，除非 `frontend/src/services/gameApi.ts` 完成从 `/v1/game/check-ending/{threadId}` 到 `/v1/game/sessions/{thread_id}/ending` 的迁移，并由页面消费 canonical ending DTO。
3. 不得把 `PR-BE-05` 标记为完成，除非 recent sessions read model 去掉 latest snapshot 的 N+1 读取，并明确 `/api/v1/game/sessions?user_id=` 的 ownership/policy。
4. transcript dialog 当前只代表“当前设备已加载消息”，不能在 PR 说明、review 结论或产品描述中表述成“服务端完整历史”。

---

## 4. PR 粒度规则

每个 PR 必须满足以下要求:

1. 只解决一类问题。
2. 必须明确是 `FE` 还是 `BE` 执行 PR。
3. 可以一句话说清“本次不解决什么”。
4. 契约变更必须显式列出。
5. 测试范围必须按前端、后端分开填写。
6. 风险与回滚方式必须可执行。
7. 如果存在配对 PR，必须写明“当前 PR 依赖哪个配对 PR”以及“未随本 PR 提交的另一侧改动是什么”。

不合格 PR 的典型表现:

1. 同时修改故事接口、训练页面、前端状态管理和样式系统。
2. 没有列出契约变更，却改了返回字段。
3. 没有列出不做项，导致 review 范围无限膨胀。
4. 前端和后端改动混在一起，但没有分开说明。
5. 前端解耦合 PR 顺手夹带页面视觉改版、交互改写或新业务入口。
6. 后端契约 PR 顺手修改前端页面行为，却没有拆成配对 PR。

---

## 5. 统一 Review 输出格式

后续 review 统一使用如下结构:

```md
## 前端 Findings
- Finding 1
- Finding 2

## 后端 Findings
- Finding 1
- Finding 2

## Open Questions
- ...

## 测试缺口
- ...

## Review Summary
- ...
```

如果某一侧无问题，应明确写:

- `前端: 未发现阻塞性问题。`
- `后端: 未发现阻塞性问题。`

如果某一侧不在本次改动范围，应明确写:

- `前端: 本次不在 review 范围。`
- `后端: 本次不在 review 范围。`

---

## 6. 通用前端 Review 清单

### 6.1 状态与职责

- [ ] 页面状态、上下文状态、服务端状态、本地缓存状态是否边界清晰
- [ ] 是否继续把 localStorage 当成事实源
- [ ] 是否在页面层混入后端会话恢复逻辑细节
- [ ] 故事与训练业务状态是否被错误复用

### 6.2 接口与契约消费

- [ ] 页面或 flow 是否直接消费后端脏字段
- [ ] snake_case 到 camelCase 的兼容是否全部收敛到 service/normalizer
- [ ] 错误处理是否基于稳定错误码而非字符串包含判断
- [ ] 是否出现未文档化的字段依赖

### 6.3 页面流程与恢复路径

- [ ] 首次初始化路径是否清晰
- [ ] 刷新恢复路径是否清晰
- [ ] 会话过期路径是否清晰
- [ ] “需要重新选择”与“自动恢复成功”是否被区分

### 6.4 解耦合与结构治理

- [ ] 页面是否承担过多业务编排
- [ ] hook 是否职责单一
- [ ] 是否把领域逻辑散落在组件事件处理器中
- [ ] 是否引入新的重复状态字段
- [ ] `GameFlowContext` 是否继续暴露存储/恢复细节
- [ ] `useGameInit` / `useGameSessionFlow` 是否继续膨胀为多职责巨型 hook
- [ ] 故事与训练是否仍共用同一套运行时状态或流程脚本
- [ ] `services / normalizer / serviceError` 是否成为唯一契约兼容入口

### 6.5 测试与交互质量

- [ ] 是否覆盖关键主流程
- [ ] 是否覆盖恢复、失败、超时、空状态
- [ ] 是否存在明显的加载态和错误态缺失
- [ ] 是否破坏既有用户主路径

---

## 7. 通用后端 Review 清单

### 7.1 领域边界

- [ ] 路由归属是否正确
- [ ] 服务是否继续跨域承担职责
- [ ] 角色域、故事域、训练域、媒体域是否发生穿透
- [ ] 是否引入新的巨型 service

### 7.2 会话与数据一致性

- [ ] 会话是否具备单一事实源
- [ ] 故事或训练回合是否具备幂等性
- [ ] 是否支持恢复、重试和重复提交保护
- [ ] 状态迁移是否明确可审计

### 7.3 DTO 与错误模型

- [ ] 请求 DTO 和响应 DTO 是否稳定
- [ ] 字段命名是否统一
- [ ] 错误码是否明确且可供前端消费
- [ ] 是否仍依赖 message 文本承载业务语义

### 7.4 性能与热路径

- [ ] 是否把图片、音频、报告等重任务塞进同步热路径
- [ ] 是否存在无必要的大量文件查找或重复 DB 读取
- [ ] 是否明确区分同步返回与异步任务

### 7.5 可维护性与可观测性

- [ ] 是否补齐日志、trace、错误上下文
- [ ] 是否补齐测试
- [ ] 是否保留历史兼容而未标注废弃策略
- [ ] 数据迁移、配置变更、回滚方式是否清楚

---

## 8. Review 结论等级

为避免 review 语义混乱，建议统一采用以下等级:

### `Blocker`

必须修改，否则不应合并。

适用场景:

- 契约破坏
- 会话一致性错误
- 关键恢复路径失效
- 明显的领域边界穿透
- 数据错误或幂等性缺失

### `Major`

建议本轮修复，否则会快速形成技术债或高概率缺陷。

适用场景:

- hook/service 职责过重
- 错误处理不稳定
- 状态边界不清
- 测试覆盖缺口大

### `Minor`

不阻塞合并，但建议跟进。

适用场景:

- 命名不统一
- 注释不足
- 文档遗漏
- 小范围结构重复

---

## 9. 每个 PR 必填信息

所有 PR 描述至少必须包含:

1. 执行 PR 编号
2. `FE` / `BE` 归属
3. 对应任务包
4. 配对 PR 编号
5. 任务名
6. 本次目标
7. 本次范围
8. 明确不做项
9. 契约影响
10. 前端测试
11. 后端测试
12. 风险
13. 回滚方式
14. 希望 reviewer 重点关注的前端问题
15. 希望 reviewer 重点关注的后端问题

---

## 10. 结论

从现在开始，规划文档负责回答“为什么这样做”，本清单负责回答“每次具体怎么做、怎么提、怎么审”。本次更新后，执行层不再允许把前后端长期捆绑成一个 PR，同时前端新增了一条“解耦合与职责收敛”治理线，用来先解决状态边界和结构退化问题，再继续推进 story 恢复、training 接入和产品完善。这样做的目标不是增加流程，而是让后续每个 PR 都能被清晰 review、独立回滚、独立验收。
