# 烽火笔锋训练收口与报告前端双人并行 PR 排期

- 更新日期：`2026-03-20`
- 计划周期：`2026-03-23` 至 `2026-04-02`
- 计划口径：只覆盖“后端收口 + 前端成型”两项，不把鉴权、限流、监控告警、Chroma、教师侧看板纳入本轮

---

## 1. 本轮目标

本轮只解决两个问题：

1. 后端收口  
   去掉 GET 写库副作用，稳住训练 query/read-model 边界，补齐迁移、集成回归、smoke、自检。
2. 前端成型  
   把训练页从“主流程能跑”推进到“恢复事实源稳定、报告可消费、可视化页可落地”。

本轮完成后，目标状态应为：

1. `summary / progress / history / report` 全部成为纯读查询路径
2. 训练后端具备稳定迁移、自检、真实数据库回归与 smoke 链路
3. 训练前端恢复逻辑以服务端事实和内存活动会话为权威，不再让 `localStorage` 抢事实源
4. 前端能够消费训练报告 DTO，并落地第一版 `TrainingReport.tsx`
5. 前后端可以进入“训练前端 MVP 与报告交互”下一阶段，而不是继续卡在基础边界问题上

---

## 2. 本轮不做

1. 不接鉴权、限流、监控告警
2. 不把 Chroma 接入训练主流程
3. 不做教师侧看板、班级分布或统计后台
4. 不做训练推荐算法的大幅升级
5. 不做完整视觉改版，只做训练页与报告页的可交付壳层

---

## 3. 当前阻塞事实

### 3.1 后端

当前训练查询服务已经拆出 `TrainingQueryService`，但查询路径仍存在“读请求触发快照补写”的问题。  
这会导致：

1. GET 请求不再是纯读
2. `session_meta` 可能被查询流量回写覆盖
3. query/read-model 边界仍不稳定
4. 恢复模型依赖访问流量而不是显式迁移或写路径升级

### 3.2 前端

当前训练页主流程已能初始化、恢复和提交，但仍存在两个未收口问题：

1. `activeSession` 与 `resumeTarget(localStorage)` 的恢复优先级不正确，缓存仍可能覆盖当前活动会话
2. `progressPercent` 在本地 flow 和服务端 summary 归一化中量纲不一致

另外，训练报告消费链路和 `TrainingReport.tsx` 还未落地，因此当前前端只能算“训练主流程壳层已出现”，还不能算“训练前端成型”。

---

## 4. 本轮 PR 拆分

### 4.1 后端 PR

| PR-ID | 名称 | 目标 | 主要范围 | 明确不做 | 完成标准 |
| --- | --- | --- | --- | --- | --- |
| `PR-BE-07A` | 训练查询纯读收口 | 去掉 GET 写库副作用，稳住 query/read-model 边界 | `backend/training/training_query_service.py`、`backend/training/session_snapshot_policy.py`、`backend/api/services/training_service.py`、`backend/api/routers/training.py`、查询相关测试 | 不做鉴权、限流、监控、算法升级 | `summary / progress / history / report` 全部纯读；缺失恢复快照时返回 typed recovery error；新增“GET 无副作用”测试 |
| `PR-BE-08A` | 训练迁移与回归收口 | 把训练后端做到可迁移、可检查、可 smoke、可回归 | `backend/alembic/**`、`scripts/init_db.py`、`scripts/check_database_status.py`、训练路由真实 DB 集成测试、训练 smoke 文档 | 不做前端接入，不扩训练业务功能 | 新库初始化、旧库升级、数据库检查、训练 smoke 全部跑通；训练主链路具备真实 DB 回归保护 |

### 4.2 前端 PR

| PR-ID | 名称 | 目标 | 主要范围 | 明确不做 | 完成标准 |
| --- | --- | --- | --- | --- | --- |
| `PR-FE-06A` | 训练页主流程稳定化 | 把训练页从“能跑”收口到“恢复路径稳定” | `frontend/src/hooks/useTrainingSessionBootstrap.ts`、`frontend/src/flows/useTrainingMvpFlow.ts`、`frontend/src/utils/trainingSession.ts`、`frontend/src/pages/Training.tsx`、相关测试 | 不做完整训练报告 UI，不引入新的业务域 | `activeSession` 成为权威恢复源；`localStorage` 仅作 fallback；`progressPercent` 统一量纲；刷新、恢复、失败、重试路径稳定 |
| `PR-FE-07A` | 训练报告接入与可视化首版 | 接上报告消费链路并落第一版 `TrainingReport.tsx` | `frontend/src/services/trainingApi.ts`、训练 DTO normalizer、训练报告页面与路由壳层、页面测试 | 不做教师侧看板，不做复杂图表平台化 | 能消费 `summary / ability_radar / state_radar / growth_curve / history / kt_observations`；页面有加载、空态、失败态与基础可视化 |

---

## 5. 文件互斥建议

为降低并行冲突，建议按以下范围分工：

### 5.1 后端开发者

优先负责：

1. `backend/training/training_query_service.py`
2. `backend/training/session_snapshot_policy.py`
3. `backend/api/services/training_service.py`
4. `backend/api/routers/training.py`
5. `backend/api/dependencies.py`
6. `backend/alembic/**`
7. `scripts/init_db.py`
8. `scripts/check_database_status.py`
9. `backend/test_training_router.py`
10. 新增训练数据库集成测试文件

### 5.2 前端开发者

优先负责：

1. `frontend/src/hooks/useTrainingSessionBootstrap.ts`
2. `frontend/src/flows/useTrainingMvpFlow.ts`
3. `frontend/src/utils/trainingSession.ts`
4. `frontend/src/services/trainingApi.ts`
5. `frontend/src/pages/Training.tsx`
6. `frontend/src/pages/TrainingReport.tsx`
7. `frontend/src/types/training.ts`
8. `frontend/src/types/api.ts`
9. 训练页与训练报告相关测试文件

说明：

1. 后端不要顺手改训练前端主流程
2. 前端不要顺手改训练接口字段语义
3. 如果报告字段需要调整，先在 `PR-BE-07A` 冻结 DTO，再让 `PR-FE-07A` 接入

---

## 6. 9 个工作日排期

### Day 1-2：`2026-03-23` 至 `2026-03-24`

后端：

1. 拆掉 GET 写库路径
2. 确认快照缺失时的 typed recovery error 策略
3. 让 `TrainingQueryService` 只读持久化事实，不再承担修复写回

前端：

1. 修正 `activeSession / resumeTarget` 恢复优先级
2. 统一 `progressPercent` 内部量纲
3. 补缓存冲突与恢复优先级测试

阶段门槛：

1. 后端查询路径不再调用写回逻辑
2. 前端恢复路径不再让缓存覆盖活动会话

### Day 3-4：`2026-03-25` 至 `2026-03-26`

后端：

1. 补 `summary / progress / history / report` 无副作用测试
2. 补缺失快照、恢复损坏、并发读取的回归测试
3. 收紧 `TrainingQueryService` 依赖面，避免继续穿透私有 helper

前端：

1. 收稳训练页主流程
2. 补刷新、恢复、失败、重试路径测试
3. 整理训练页状态边界，保证 `page / flow / hook / service / storage` 职责清楚

阶段门槛：

1. 前后端测试都能覆盖当前两个主要风险点
2. 主流程状态机不再依赖脏缓存维持运行

### Day 5-6：`2026-03-27` 至 `2026-03-30`

后端：

1. 收口 Alembic 迁移链路
2. 验证新库初始化、旧库升级
3. 固化 `init_db / check_database_status / smoke` 路径

前端：

1. 接入训练报告 API
2. 完成报告 DTO normalizer
3. 准备报告页路由壳层与页面状态模型

阶段门槛：

1. 数据库初始化与升级不再依赖运行时补表
2. 报告接口字段在前端有明确消费入口

### Day 7-8：`2026-03-31` 至 `2026-04-01`

后端：

1. 补真实数据库集成测试
2. 补 smoke 说明和回归说明
3. 验证训练主链路在真实 DB 环境下可回归

前端：

1. 落地 `TrainingReport.tsx`
2. 渲染基础报告结构：
   - 总结摘要
   - 能力雷达区
   - 成长曲线区
   - 训练历史区
   - `kt_observations` 事实区
3. 处理加载态、空态、失败态

阶段门槛：

1. `TrainingReport.tsx` 可以直接消费结构化 DTO
2. 后端真实 DB 集成测试可以保护主链路

### Day 9：`2026-04-02`

联调与收口：

1. 前后端联调训练主流程与报告链路
2. 修正接口字段与页面消费的收口缺陷
3. 跑完整回归、smoke、自检
4. 输出收口说明

最终门槛：

1. 训练查询路径纯读
2. 训练页恢复路径稳定
3. 报告页可用
4. 迁移、自检、smoke、测试可执行

---

## 7. 各 PR 合并门槛

### 7.1 `PR-BE-07A`

1. `GET /summary`、`GET /progress`、`GET /history`、`GET /report` 不产生持久化副作用
2. 不再通过查询请求补写 `session_meta`
3. 缺失恢复快照时返回 typed recovery error，而不是静默修复
4. 有直接测试证明 query 路径不会调用 `update_training_session`

### 7.2 `PR-BE-08A`

1. `alembic upgrade head` 可执行
2. 新库与旧库都能通过 `init_db`
3. `check_database_status` 输出稳定
4. 训练主链路 smoke 可在标准步骤下复现

### 7.3 `PR-FE-06A`

1. `activeSession` 优先级高于 `resumeTarget`
2. `localStorage` 不再决定 live training session 命运
3. `progressPercent` 在 init / restore / submit / next 全路径下量纲一致
4. 训练页补齐恢复、失败、重试相关测试

### 7.4 `PR-FE-07A`

1. 页面不直接兼容脏字段
2. 报告 DTO 兼容收敛在 `services / normalizer`
3. `TrainingReport.tsx` 具备加载、空态、失败态、正常态
4. 报告页不通过扫描 history 自己重算后端已聚合字段

---

## 8. 风险与兜底

### 8.1 最大风险

1. GET 纯读改造后，如果发现当前恢复模型强依赖查询时补快照，后端需要补一个显式 repair/migration 入口
2. Alembic baseline 与现存数据库不一致时，可能导致本轮后半程卡在迁移校准
3. 报告 DTO 如果继续变化，前端报告页会反复返工

### 8.2 兜底策略

1. 若查询纯读改造暴露恢复缺口，优先补显式 repair，不回退到“GET 顺手修库”
2. 若迁移链路阻塞，先保证新库初始化与测试库升级稳定，再收旧库兼容
3. 若报告可视化时间不足，先交付结构化文本版报告页，不引入重型图表依赖

---

## 9. 完成后的状态判断

如果本轮 4 个 PR 都按门槛完成，则可认为：

1. 训练后端已经从“主链路基本可跑”进入“查询边界稳定、可迁移、可回归”的状态
2. 训练前端已经从“页面壳层出现”进入“恢复逻辑稳定、报告可消费、可继续做 MVP”的状态
3. 下一阶段可以进入：
   - 训练前端 MVP 深化
   - 报告交互增强
   - 鉴权、限流、监控治理

如果未完成，则优先级顺序必须保持为：

1. 先修 `PR-BE-07A`
2. 再收 `PR-FE-06A`
3. 然后补 `PR-BE-08A`
4. 最后推进 `PR-FE-07A`

原因是：没有纯读查询边界和稳定恢复事实源，报告页只会建立在不可靠状态之上。
