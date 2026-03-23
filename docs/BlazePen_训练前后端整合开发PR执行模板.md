# BlazePen 训练前后端整合开发 PR 执行模板

- 更新日期: `2026-03-23`
- 对应总规划: `docs/BlazePen_训练前后端整合开发完整PR规划.md`
- 适用方式: 训练主线采用前后端一体化垂直切片开发时，直接复用本文件作为每个 `PR-TRN-XX` 的执行底稿。

## 1. 使用规则

1. 一个 `PR-TRN-XX` 只对应一个分支。
2. 一个 `PR-TRN-XX` 只解决一个完整训练能力，不混多个主目标。
3. 同一个 PR 内允许同时修改前端和后端，但必须围绕同一份契约。
4. PR 描述必须显式写清楚前端范围、后端范围、明确不做、验收标准、测试范围、回滚方式。
5. Review 仍然按前端和后端分开审，不能混成一句“整体可合并”。

## 2. 统一命名建议

### 2.1 分支名

- `feature/trn-01-contract-freeze`
- `feature/trn-02-recovery-hardening`
- `feature/trn-03-submit-idempotency`
- `feature/trn-04-read-model-freeze`
- `feature/trn-05-report-productization`
- `feature/trn-06-branch-impact-loop`
- `feature/trn-07-smoke-observability`

### 2.2 PR 标题

- `[PR-TRN-01] 冻结训练契约与 sessionId 边界`
- `[PR-TRN-02] 收口训练初始化与恢复链路`
- `[PR-TRN-03] 稳定训练提交链路与幂等保护`
- `[PR-TRN-04] 冻结训练读模型并收口洞察页`
- `[PR-TRN-05] 完成训练报告页产品化`
- `[PR-TRN-06] 复原训练分支影响与自适应闭环`
- `[PR-TRN-07] 收口训练 smoke、观测与发布准入`

### 2.3 Commit 分组建议

1. `backend:` 先提交契约、service、query、store 改动。
2. `frontend:` 再提交 types、services、hooks、pages 改动。
3. `test:` 最后提交单测、集成、smoke、自检脚本。
4. `docs:` 最后补 runbook、执行说明、迁移说明。

## 3. 通用 PR 描述模板

复制以下模板到 PR 描述中使用：

```md
# PR-TRN-XX 标题

## 本次目标
- 

## 前端范围
- 

## 后端范围
- 

## 明确不做
- 

## 契约变化
- 

## 验收条件
- 

## 前端测试
- 

## 后端测试
- 

## 风险
- 

## 回滚方式
- 

## Reviewer Focus
### 前端
- 

### 后端
- 
```

## 4. PR-TRN-01 执行模板

### 4.1 目标

冻结训练 canonical DTO、`sessionId` 边界和训练最小公共字段集，阻止后续工作继续建立在漂移契约上。

### 4.2 推荐改动焦点文件

前端：

- `frontend/src/types/training.ts`
- `frontend/src/services/trainingApi.ts`
- `frontend/src/utils/trainingSession.ts`
- 训练相关测试文件

后端：

- `backend/api/schemas.py`
- `backend/api/routers/training.py`
- `backend/training/training_outputs.py`
- `backend/training/training_query_service.py`

### 4.3 PR 描述建议

```md
# [PR-TRN-01] 冻结训练契约与 sessionId 边界

## 本次目标
- 冻结 training 对外 canonical DTO。
- 明确 training 只使用 `sessionId`，不再接受 story `threadId` 语义。
- 收口 `briefing -> brief` 兼容，禁止页面层继续扩散脏字段。

## 前端范围
- 收口 `training.ts` 的类型定义。
- 收口 `trainingApi.ts` 与 normalizer，只向页面暴露 canonical 字段。
- 清理训练页面对 legacy `briefing` 的显式消费。

## 后端范围
- 收口训练 request/response DTO。
- 固化 `session summary / progress / history / report / diagnostics` 的最小公共字段集。
- 把 `character_id` 纳入训练正式读模型字段。

## 明确不做
- 不调整训练恢复策略。
- 不调整训练主流程页面结构。
- 不改报告页产品形态。

## 契约变化
- `brief` 成为唯一 canonical 场景正文字段。
- `briefing` 仅保留后端兼容过渡，不允许前端页面层继续消费。
- training 侧统一只认 `sessionId`。

## 验收条件
- 训练前端页面层不再直接依赖 `briefing`。
- 训练接口不再混入 `threadId` 兼容语义。
- 训练主要读模型字段集一致。

## 前端测试
- `trainingApi` normalizer 测试。
- `briefing -> brief` 映射测试。

## 后端测试
- DTO contract tests。
- outputs 一致性测试。
- 路由边界测试。

## 风险
- 旧测试和旧 mock 可能依赖 legacy 字段。

## 回滚方式
- 回滚 training DTO 和 trainingApi normalizer 的本次变更，不回退其他业务逻辑。

## Reviewer Focus
### 前端
- 是否还有页面层直接兼容脏字段。
- 是否还存在 `threadId` 语义渗入 training。

### 后端
- DTO 是否稳定。
- legacy 字段是否只停留在兼容层。
```

### 4.4 合并前检查清单

- [ ] 训练前端页面层不再直接消费 `briefing`
- [ ] training 相关类型只使用 `sessionId`
- [ ] 训练读模型最小字段集一致
- [ ] DTO 测试通过

## 5. PR-TRN-02 执行模板

### 5.1 目标

把训练初始化、刷新恢复、完成态恢复统一收口到服务端读模型，移除本地缓存对恢复真相的主导。

### 5.2 推荐改动焦点文件

前端：

- `frontend/src/hooks/useTrainingSessionBootstrap.ts`
- `frontend/src/hooks/useTrainingSessionViewModel.ts`
- `frontend/src/storage/trainingSessionCache.ts`
- `frontend/src/flows/useTrainingMvpFlow.ts`

后端：

- `backend/training/training_query_service.py`
- `backend/api/routers/training.py`
- `backend/training/training_store.py`

### 5.3 PR 描述建议

```md
# [PR-TRN-02] 收口训练初始化与恢复链路

## 本次目标
- 建立服务端权威恢复模型。
- 降级 local storage 为 UX 提示，不再参与 live session 真相判断。

## 前端范围
- 重构 `useTrainingSessionBootstrap` 和 `useTrainingSessionViewModel`。
- 收口 `trainingSessionCache` 的职责。
- 清理 `useTrainingMvpFlow` 中本地恢复推断。

## 后端范围
- 固化 `get_session_summary()` 的恢复读模型职责。
- 明确 not-found / completed / corrupted-state 的稳定错误语义。
- 补齐训练恢复所需正式字段。

## 明确不做
- 不处理提交链路幂等。
- 不处理报告页产品化。

## 契约变化
- 会话摘要成为训练恢复的唯一服务端事实入口。
- `character_id` 和 `runtime_state` 必须由服务端摘要提供。

## 验收条件
- 刷新训练页可恢复。
- 完成态可恢复。
- local storage 清空后，只要有 `sessionId` 仍可从服务端恢复。

## 前端测试
- bootstrap 恢复测试。
- view model 读目标优先级测试。
- 刷新恢复集成测试。

## 后端测试
- `session_summary` route/service/store 测试。
- completed/not-found/corrupted-state 测试。

## 风险
- 旧前端缓存逻辑与新恢复逻辑可能冲突。

## 回滚方式
- 仅回滚训练恢复链路重构，不回退 PR-TRN-01 契约冻结结果。

## Reviewer Focus
### 前端
- storage 是否还在主导恢复。
- flow 是否继续手工拼接 fallback 恢复逻辑。

### 后端
- GET 恢复路径是否纯读。
- 摘要读模型是否足够支撑恢复。
```

### 5.4 合并前检查清单

- [ ] local storage 不再决定 live session 真相
- [ ] 恢复仅依赖 `session summary`
- [ ] completed / not-found / corrupted-state 路径明确
- [ ] 刷新恢复测试通过

## 6. PR-TRN-03 执行模板

### 6.1 目标

稳住训练热路径，解决重复提交、幂等、下一场景拉取失败恢复等高风险问题。

### 6.2 推荐改动焦点文件

前端：

- `frontend/src/hooks/useTrainingRoundRunner.ts`
- `frontend/src/flows/useTrainingMvpFlow.ts`
- `frontend/src/pages/Training.tsx`

后端：

- `backend/api/services/training_service.py`
- `backend/api/routers/training.py`
- `backend/training/training_store.py`

### 6.3 PR 描述建议

```md
# [PR-TRN-03] 稳定训练提交链路与幂等保护

## 本次目标
- 稳定训练提交流程。
- 建立 duplicate submit / completed submit / next fetch failed 的恢复闭环。

## 前端范围
- 收口 round runner。
- 增加提交防重入。
- 拆出提交态与恢复态处理，不再全部堆在同一个 flow。

## 后端范围
- 固化 submit 幂等。
- 固化 next 场景读取边界。
- 增补 duplicate/completed/current-round mismatch 等错误码。

## 明确不做
- 不处理报告页。
- 不升级推荐算法。

## 契约变化
- submit 错误分支必须用 typed error code 表达。
- submit 成功与 next 失败后的恢复路径必须可由服务端事实重建。

## 验收条件
- 双击提交不重复落库。
- 网络重试不产生重复 round。
- next 获取失败可恢复到权威状态。
- completed session 不允许继续提交。

## 前端测试
- 提交防重入测试。
- duplicate submit 恢复测试。
- next fetch failed 恢复测试。

## 后端测试
- submit 幂等测试。
- duplicate submit 测试。
- completed session submit reject 测试。

## 风险
- 提交结果和数据库状态不一致会导致恢复路径异常。

## 回滚方式
- 回滚训练 submit 和 next 链路改动，不回退恢复模型与契约冻结。

## Reviewer Focus
### 前端
- 是否还依赖 message 文本判断业务语义。
- 是否仍存在双事实源。

### 后端
- submit 是否真正幂等。
- GET 路由是否继续写库。
```

### 6.4 合并前检查清单

- [ ] 双击提交不重复写入
- [ ] duplicate submit 可恢复
- [ ] next 失败可恢复
- [ ] completed session 无法继续提交

## 7. PR-TRN-04 执行模板

### 7.1 目标

冻结训练读模型，让训练洞察页只消费服务端正式读模型。

### 7.2 推荐改动焦点文件

前端：

- `frontend/src/hooks/useTrainingReadQuery.ts`
- `frontend/src/pages/TrainingProgress.tsx`
- `frontend/src/pages/TrainingReport.tsx`
- `frontend/src/pages/TrainingDiagnostics.tsx`

后端：

- `backend/training/training_query_service.py`
- `backend/training/training_outputs.py`
- `backend/api/routers/training.py`

### 7.3 PR 描述建议

```md
# [PR-TRN-04] 冻结训练读模型并收口洞察页

## 本次目标
- 让 progress/history/report/diagnostics 成为正式读模型。
- 让洞察页停止自行扫描 history 重算业务摘要。

## 前端范围
- 统一 `useTrainingReadQuery`。
- 收口 Progress/Report/Diagnostics 三个页面的加载、失败、空态、直达访问。

## 后端范围
- 冻结 query service 产出的正式读模型。
- 增补前端展示必需字段。
- 保持 query path 纯读。

## 明确不做
- 不改推荐策略。
- 不做报告视觉重构。

## 契约变化
- `progress / history / diagnostics / report` 字段结构冻结。

## 验收条件
- 三个洞察页支持通过 `sessionId` 直达。
- 页面不再自行重算主要统计值。
- query path 不写库。

## 前端测试
- 洞察页直达访问测试。
- 空态/失败态测试。

## 后端测试
- query service DTO 测试。
- query path pure-read 测试。

## 风险
- 页面原有本地计算逻辑和正式读模型可能发生冲突。

## 回滚方式
- 回滚读模型页面消费和 query 输出改动，不回退 submit/recovery 主链路。

## Reviewer Focus
### 前端
- 页面是否仍在二次拼装原始 payload。
- 是否存在多个 query 入口并存。

### 后端
- 读模型是否真正产品化。
- query 路径是否纯读。
```

### 7.4 合并前检查清单

- [ ] 洞察页支持 `sessionId` 直达
- [ ] 页面不再重算核心摘要
- [ ] query path 不写库
- [ ] 读模型 DTO 测试通过

## 8. PR-TRN-05 执行模板

### 8.1 目标

完成训练报告页产品化，把 `TrainingReport.tsx` 从技术页推进到用户可消费页面。

### 8.2 推荐改动焦点文件

前端：

- `frontend/src/pages/TrainingReport.tsx`
- `frontend/src/hooks/useTrainingReport.ts`
- `frontend/src/components/training/` 下的报告相关组件

后端：

- `backend/training/training_query_service.py`
- `backend/training/training_outputs.py`
- 报告相关 policy

### 8.3 PR 描述建议

```md
# [PR-TRN-05] 完成训练报告页产品化

## 本次目标
- 交付真正可用的训练报告页。
- 报告从“展示数据”升级为“解释训练结果”。

## 前端范围
- 模块化报告页。
- 增加摘要、雷达、成长曲线、高风险回合、证据和复盘建议区块。

## 后端范围
- 固化报告读模型。
- 确保报告字段直接面向展示。
- 如有必要，前移重计算，避免把重任务塞进同步 GET 热路径。

## 明确不做
- 不做导出 PDF。
- 不做教师端管理页。

## 契约变化
- 报告字段正式冻结。

## 验收条件
- 完成训练后可稳定查看报告。
- 报告页刷新不丢状态。
- 页面不再自行补业务语义。

## 前端测试
- 报告页渲染测试。
- 完成态/未完成态/失败态测试。

## 后端测试
- 报告装配测试。
- report route contract tests。

## 风险
- 报告输出过大或过慢会拖慢查询路径。

## 回滚方式
- 回滚报告页模块化和报告读模型改动，不回退其他训练读模型。

## Reviewer Focus
### 前端
- 报告页是否仍像调试页而不是产品页。
- 是否继续手工拼接后端原始结构。

### 后端
- 报告 DTO 是否真的面向展示。
- 是否把重任务留在同步热路径。
```

### 8.4 合并前检查清单

- [ ] 报告页模块化完成
- [ ] 报告页具备完成态/失败态/未完成态
- [ ] 报告字段冻结
- [ ] 报告查询路径性能可接受

## 9. PR-TRN-06 执行模板

### 9.1 目标

复原训练最重要的业务特色: 玩家决策影响训练路径，自适应推荐与分支跳转形成可解释闭环。

### 9.2 推荐改动焦点文件

前端：

- `frontend/src/pages/Training.tsx`
- `frontend/src/pages/TrainingProgress.tsx`
- `frontend/src/pages/TrainingReport.tsx`
- 训练相关展示组件

后端：

- `backend/api/services/training_service.py`
- `backend/training/training_query_service.py`
- recommendation / branch / consequence 相关 policy

### 9.3 PR 描述建议

```md
# [PR-TRN-06] 复原训练分支影响与自适应闭环

## 本次目标
- 把玩家决策如何影响训练路径真正展示出来。
- 固定大历史锚点，可变小场景分支。

## 前端范围
- 展示 decisionContext、consequenceEvents、branchTransition。
- 让用户看见推荐项、实际选择、偏差原因、后果和分支跳转。

## 后端范围
- 固化 branch transition 和 consequence event 输出。
- 固化推荐链路、自适应候选池和解释字段。
- 把 branch transition 纳入 report/diagnostics 正式统计。

## 明确不做
- 不引入新的 story 会话模型。
- 不把 training 混回 story 会话体系。

## 契约变化
- decisionContext / consequenceEvents / branchTransition 成为正式展示字段。

## 验收条件
- 玩家决策对路径影响可见。
- 六个大历史场景固定，小场景路径可变。
- 报告可解释训练为何走到当前路径。

## 前端测试
- 分支影响展示测试。
- 推荐与实际选择偏差展示测试。

## 后端测试
- branch transition policy tests。
- recommendation log / diagnostics 汇总测试。

## 风险
- 分支逻辑与固定历史锚点可能产生冲突。

## 回滚方式
- 回滚分支影响展示和 branch transition 统计，不回退核心训练主流程。

## Reviewer Focus
### 前端
- 是否只是把内部字段堆到页面，而不是产品化表达。
- 是否存在 story/training 状态混用。

### 后端
- 历史锚点是否仍固定。
- 分支链路是否具备可解释性和可统计性。
```

### 9.4 合并前检查清单

- [ ] 玩家能看见推荐与实际选择差异
- [ ] 玩家能看见 consequence events 与 branch transition
- [ ] 大历史锚点固定
- [ ] report / diagnostics 纳入分支统计

## 10. PR-TRN-07 执行模板

### 10.1 目标

把训练主线收口到可持续联调、可持续回归、可持续上线的工程状态。

### 10.2 推荐改动焦点文件

前端：

- `frontend/package.json`
- 训练 smoke 测试文件
- 训练 runbook 相关文档

后端：

- `backend/run_training_api.py`
- 训练相关 smoke / entry / route / query tests
- `docs/runbooks/story_training_dual_backend_runbook.md`

### 10.3 PR 描述建议

```md
# [PR-TRN-07] 收口训练 smoke、观测与发布准入

## 本次目标
- 建立训练主线 smoke、自检、观测和发布准入门槛。

## 前端范围
- 补训练主链路 smoke。
- 补洞察页 smoke。
- 固化 `dev:training` / `dev:all` / 测试命令。

## 后端范围
- 补 route/query smoke。
- 补结构化日志、trace、错误上下文。
- 补迁移与回滚说明。
- 在前端完全不消费后，移除 training legacy `briefing` 字段。

## 明确不做
- 不新增业务功能。
- 不改训练产品逻辑。

## 契约变化
- 清退 legacy training `briefing`。

## 验收条件
- 可按 runbook 启动双前端/双后端。
- 训练主链路和洞察页均有 smoke。
- 上线前具备最小自检命令。

## 前端测试
- main path smoke。
- progress/report/diagnostics smoke。

## 后端测试
- training route smoke。
- training query smoke。
- entrypoint / runbook 自检测试。

## 风险
- 清退 legacy 字段可能影响遗漏的旧消费者。

## 回滚方式
- 回滚 smoke / self-check / legacy 清退，不回退已经稳定的训练业务逻辑。

## Reviewer Focus
### 前端
- smoke 是否覆盖真实主路径。
- 是否仍有页面依赖 legacy 字段。

### 后端
- 日志、trace、错误上下文是否够用。
- 清退 legacy 字段是否彻底。
```

### 10.4 合并前检查清单

- [ ] 训练主链路 smoke 通过
- [ ] 训练洞察页 smoke 通过
- [ ] runbook 已更新
- [ ] legacy `briefing` 已完成清退

## 11. Review 输出模板

每个 `PR-TRN-XX` 的 review 统一建议使用：

```md
## 前端 Findings
- [Blocker/Major/Minor] 文件路径:行号
  问题：
  原因：
  影响：
  建议：

## 后端 Findings
- [Blocker/Major/Minor] 文件路径:行号
  问题：
  原因：
  影响：
  建议：

## Open Questions
- 

## 测试缺口
- 前端：
- 后端：

## Review Summary
- 
```

## 12. 完整执行顺序

1. `PR-TRN-01` 契约冻结
2. `PR-TRN-02` 恢复链路收口
3. `PR-TRN-03` 提交链路与幂等
4. `PR-TRN-04` 读模型与洞察页
5. `PR-TRN-05` 报告页产品化
6. `PR-TRN-06` 分支影响与自适应闭环
7. `PR-TRN-07` smoke、观测、迁移、发布收口

## 13. 结论

这份模板的目的不是增加流程，而是防止训练主线再次退化成“前端先写一半、后端再补一半、最后一起返工”的开发方式。后续只要按 `PR-TRN-01` 到 `PR-TRN-07` 逐个执行，并强制使用本模板补齐目标、契约、测试和回滚说明，训练主线就能保持高内聚、低耦合、可恢复、可测试的推进节奏。
