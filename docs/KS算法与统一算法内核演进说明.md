# KS算法与统一算法内核演进说明

## 1. 文档目的

本文档围绕 BlazePen 当前训练系统中的“KS 算法体系”做统一说明，目标不是把现有实现包装成一个并不存在的单体算法，而是基于当前代码事实回答下面 4 个问题：

1. 当前训练系统里的“KS”到底是什么。
2. 当前已经实现了哪些算法能力，为什么它已经不是简单原型。
3. 当前为什么还不能被严格定义为“单一算法内核”。
4. 后续如果要把它演进成可单独命名、可方法论化、可白皮书化的统一算法内核，应该如何开发。

本文档以当前仓库实现为事实源，重点参考以下模块：

- `backend/training/constants.py`
- `backend/training/evaluator.py`
- `backend/training/recommendation_policy.py`
- `backend/training/phase_policy.py`
- `backend/training/round_flow_policy.py`
- `backend/training/round_transition_policy.py`
- `backend/training/branch_resolver.py`
- `backend/training/telemetry_policy.py`
- `backend/training/reporting_policy.py`
- `backend/training/session_snapshot_policy.py`
- `backend/training/training_query_service.py`
- `backend/api/services/training_service.py`

## 2. 当前对 KS 的正确理解

### 2.1 KS 不是单点打分器

当前系统中的 KS，不应再被理解成“根据用户输入打一个分，然后决定后续场景”的单一函数。更准确的表述是：

> KS 是一套以 `k_state / s_state` 为状态事实源，由评估、风险修正、阶段解析、推荐排序、分支决策、结局收束和复盘诊断共同驱动的训练推进体系。

这意味着当前 KS 的本质是一个“多策略协同的状态驱动训练引擎”，而不是一个“单次计算后直接吐答案的算法函数”。

### 2.2 K 与 S 的职责边界

- `k_state`：承载能力成长面，回答“玩家当前在哪些训练能力上偏强、偏弱、是否有提升”。
- `s_state`：承载情境与风险运行面，回答“训练局面当前被推进到了什么状态、是否进入风险路径、整体叙事张力和环境安全如何变化”。

当前这两个状态已经具备稳定配置来源：

- `SKILL_CODES`
- `S_STATE_CODES`
- `DEFAULT_K_STATE`
- `DEFAULT_S_STATE`

这说明 KS 的“状态模型底座”已经存在，而不是临时散落字段。

### 2.3 当前 KS 的业务定位

从业务上看，KS 当前承担的是训练主线推进引擎，而不是纯分析模型。它不仅负责解释本轮行为，还负责：

- 更新训练状态
- 记录风险事实
- 影响下一场景选择
- 影响分支流转
- 决定最终结局
- 生成训练报告和诊断视图

因此，KS 当前已经具备“输入 -> 状态 -> 推进 -> 结果 -> 复盘”的完整闭环。

## 3. 当前 KS 算法体系的结构

### 3.1 输入层

当前 KS 的核心输入不是单一文本，而是一个复合输入集合：

- 用户本轮决策输入：`user_input`
- 用户显式选择：`selected_option`
- 当前场景：`scenario_id` 与冻结后的 `scenario_payload`
- 历史能力状态：`k_before`
- 历史情境状态：`s_before`
- 最近风险轨迹：`recent_risk_rounds`
- 当前训练模式：`guided / adaptive / self-paced`
- 当前运行时标记：`runtime_flags`
- 当前轮次与总轮次：`round_no / total_rounds`

这意味着 KS 当前实际上已经具备较清晰的“状态机输入面”，只是这些输入尚未收敛为单一内核接口。

### 3.2 状态层

当前系统中的核心状态可分成 5 组：

#### 1. 能力状态

- `k_state`
- `skill_delta`

#### 2. 情境状态

- `s_state`
- `s_delta`

#### 3. 风险状态

- `risk_flags`
- `recent_risk_rounds`

#### 4. 阶段状态

- `phase_snapshot`
- `phase_tags`
- `window_reasons`

#### 5. 运行时与分支状态

- `runtime_flags`
- `consequence_events`
- `branch_hints`
- `branch_transition`

这说明当前系统其实已经具备比较完整的“状态簇”，只是不在一个统一的 KS 状态模型里定义。

### 3.3 当前状态转移主链路

当前训练提交链路可以概括为下面这条主链路：

```text
用户决策输入
-> evaluator 评估 skill_delta / s_delta / risk_flags
-> round_transition_policy 更新 k_state / s_state
-> consequence_engine 生成 consequence_events / runtime_flags
-> phase_policy 解析当前阶段
-> round_flow_policy + recommendation_policy 决定下一题
-> branch_resolver 解析分支跳转
-> ending_policy 在完成时判定结局
-> reporting_policy / query_service 聚合报告与诊断
```

这条链路已经接近统一算法链，但当前仍然是“多策略串联”，而不是“单内核统一调度”。

### 3.4 当前模块映射

| 能力层 | 当前模块 | 作用 |
| --- | --- | --- |
| 状态定义 | `constants.py` | 定义 K/S 维度、默认值、权重和配置导出 |
| 评估层 | `evaluator.py` | 输出 `skill_delta / s_delta / risk_flags / confidence / eval_mode` |
| 状态推进层 | `round_transition_policy.py` | 统一更新 K/S 状态，并衔接运行时后果 |
| 后果与运行时层 | `consequence_engine.py`、`runtime_artifact_policy.py` | 计算运行时 flags 和 consequence events |
| 阶段层 | `phase_policy.py` | 统一解析训练阶段窗口 |
| 推荐层 | `recommendation_policy.py` | 基于 K/S、风险、阶段做候选排序 |
| 流程控制层 | `round_flow_policy.py` | 统一负责下一题、候选池、提交校验、完成判定 |
| 分支层 | `branch_resolver.py` | 根据运行时 flags 解析分支跳转 |
| 决策上下文层 | `decision_context_policy.py` | 生成推荐与选择的稳定决策上下文 |
| 观测层 | `telemetry_policy.py` | 生成 recommendation logs、audit events、KT observation |
| 结局层 | `ending_policy.py` | 根据状态与风险路径生成结局结果 |
| 报告层 | `reporting_policy.py` | 聚合报告、诊断、图表摘要 |
| 恢复层 | `session_snapshot_policy.py` | 冻结会话级场景快照，保证恢复事实源 |
| 读模型层 | `training_query_service.py` | 从已持久化事实构建报告和诊断读模型 |
| 编排层 | `api/services/training_service.py` | 串联各 policy 和 store，形成提交事务链 |

### 3.5 当前输出层

当前 KS 的最终输出，不是单一结果，而是三层结果模型：

#### 1. 回合输出

- `evaluation`
- `k_state`
- `s_state`
- `runtime_state`
- `consequence_events`
- `decision_context`

#### 2. 训练结束输出

- `ending`

#### 3. 复盘输出

- `report`
- `diagnostics`

从产品角度看，这意味着 KS 已经不是纯粹“做题评分算法”，而是“可解释的训练推进和结果生成体系”。

## 4. 当前 KS 已经完成到什么程度

### 4.1 工程闭环完成度较高

如果按“是否具备完整训练闭环”判断，当前完成度已经较高，大致可理解为 `85% - 90%` 的工程闭环完整性。原因是：

- 状态模型已经存在
- 单回合评估链路已经稳定
- K/S 状态更新已下沉到独立 policy
- 推荐、阶段、分支、结局、报告均已有独立模块
- 会话快照、恢复校验、读模型边界已经明确
- 诊断与观测链路已经具备结构化事实源
- 测试覆盖已经明显超出原型阶段

### 4.2 统一算法模型完成度中等偏高

如果按“是否已经抽象成统一算法模型”判断，当前完成度大致在 `70% - 75%`。原因是：

- 当前已经有统一的状态事实源
- 已经存在比较清晰的主链路
- 但仍缺少一个显式的单一 KS Core 抽象层
- 多个 policy 的协同关系，仍然需要通过代码阅读理解
- 还没有统一输入输出契约和统一状态转移接口

### 4.3 算法产品化完成度仍然偏低

如果按“是否可单独命名、可输出白皮书、可品牌化”判断，当前完成度仍然偏低，大致在 `40% - 50%`。缺口主要在：

- 缺少统一内核层
- 缺少显式算法指标体系
- 缺少 benchmark 和专项回放样本
- 缺少稳定的方法论文档体系

## 5. 当前为什么还不是单一算法内核

### 5.1 当前更像多策略协同系统

当前训练系统已经做了大量模块化拆分，但这些模块之间仍然是“服务层串联调用”的关系。也就是说，今天的 KS 更像：

```text
evaluator
+ recommendation_policy
+ phase_policy
+ branch_resolver
+ ending_policy
+ reporting_policy
+ round_flow_policy
```

而不是：

```text
ks_kernel.run(input) -> unified result
```

这两者的区别在于：

- 前者是工程上可维护的协同体系
- 后者是理论上可命名、可验证、可独立传播的统一算法内核

### 5.2 统一输入输出契约还未收口

当前很多状态和上下文已经存在，但它们分散在不同函数参数和 payload 中。当前系统尚未形成类似下面这种单一契约：

```python
result = ks_kernel.run(
    session_state=...,
    round_input=...,
    scenario_context=...,
    mode_context=...,
)
```

这导致：

- 算法主链条不够一眼可见
- 不利于对外解释
- 不利于建立 benchmark 回放机制
- 不利于后续做统一调参和回归验证

### 5.3 核心算法与业务策略边界还不够清晰

当前系统中仍存在一些“算法能力”和“产品模式能力”交织的情况，例如：

- `guided / adaptive / self-paced`
- 强制轮次规则
- 推荐候选池数量
- 报告展示摘要

其中有些属于 KS 内核，有些属于产品策略。若不先分层，后续就很难明确：

- 哪些是统一算法核心
- 哪些只是当前训练产品的策略外壳

### 5.4 还没有统一验证基线

当前测试已经覆盖了很多功能点，但还缺少真正面向 KS 内核的验证体系，例如：

- 固定输入是否得到稳定状态转移
- 推荐排序是否符合预期基线
- 风险路径是否被正确纠偏
- 相同历史输入在不同模式下的差异是否仍可解释
- 报告解释是否与状态变化一致

没有这些，就很难把 KS 进一步包装成“统一算法资产”。

## 6. 单一算法内核的目标状态

如果后续目标是把 KS 演进成一个可单独命名、可独立讲述的方法论内核，那么建议目标状态定义为以下 5 条。

### 6.1 有统一算法名字

KS 不再只是 `k_state / s_state` 的简称，而是一个明确的算法名，例如：

- `KS State Engine`
- `KS Narrative Training Engine`
- `KS Decision Progression Model`

名字本身不是重点，重点是名字背后必须对应稳定定义。

### 6.2 有统一输入输出模型

对内对外都能明确表达：

- 输入：用户决策、当前场景、历史状态、风险上下文、模式上下文
- 中间状态：`k_state / s_state / risk_flags / phase_snapshot / branch_context`
- 输出：状态增量、更新后状态、推荐结果、分支流转、结局结果、复盘事实

### 6.3 有统一状态转移逻辑

统一内核的核心链路应能收敛成一条明确逻辑链：

```text
输入
-> 评估
-> 状态增量
-> 风险修正
-> 运行时后果
-> 阶段解析
-> 推荐排序
-> 分支决策
-> 结果收束
```

### 6.4 有统一验证基线

需要建立稳定的指标、样本和回放机制，保证 KS 不是“感觉合理”，而是“可回归、可比较、可调优”。

### 6.5 有统一文档体系

至少需要形成：

- 术语定义文档
- 算法框架文档
- 指标与验证文档
- benchmark 文档
- 业务落地案例文档
- 白皮书大纲

## 7. 建议的单一内核形态

### 7.1 建议新增 `ks_core` 模块

建议在 `backend/training/` 下新增独立目录：

```text
backend/training/ks_core/
  __init__.py
  input_model.py
  state_model.py
  transition_model.py
  policy_context.py
  result_model.py
  kernel.py
  metrics.py
```

### 7.2 建议的核心对象

#### 1. `KSRoundInput`

用于描述本轮统一输入：

- `session_id`
- `round_no`
- `scenario_id`
- `user_input`
- `selected_option`
- `training_mode`
- `media_tasks`

#### 2. `KSStateSnapshot`

用于描述输入前状态：

- `k_state`
- `s_state`
- `runtime_flags`
- `recent_risk_rounds`
- `current_scene_id`
- `completed_scenario_ids`

#### 3. `KSScenarioContext`

用于描述当前回合相关场景事实：

- `scenario_payload`
- `scenario_payload_sequence`
- `scenario_payload_catalog`
- `session_sequence`

#### 4. `KSTransitionResult`

用于统一导出内核结果：

- `evaluation_payload`
- `updated_k_state`
- `updated_s_state`
- `phase_snapshot`
- `decision_context`
- `recommendation_bundle`
- `branch_transition`
- `runtime_state`
- `consequence_events`
- `audit_payloads`
- `kt_observation_payload`
- `ending_payload`

### 7.3 建议的核心执行接口

统一内核最终应暴露稳定接口：

```python
result = ks_kernel.run(
    round_input=round_input,
    state_snapshot=state_snapshot,
    scenario_context=scenario_context,
)
```

这个接口的意义在于：

- 把服务层里分散的参数组装成一个统一算法入口
- 让算法主链条清晰显式
- 让 benchmark 回放可以直接复用
- 让未来调参、A/B、基线验证都围绕一套接口展开

### 7.4 `kernel.py` 内部建议流程

建议 `kernel.py` 内部按固定顺序调度各子能力：

```text
1. validate_input
2. evaluate_round
3. apply_state_delta
4. apply_consequence
5. resolve_phase
6. resolve_flow_and_recommendation
7. resolve_branch
8. assemble_decision_context
9. resolve_ending_if_completed
10. build_telemetry_payloads
11. return unified_result
```

这里的关键点不是把所有代码重写，而是把当前已存在的 policy 变成统一调度链中的“子能力”。

## 8. 当前模块如何收口到单一内核

### 8.1 保留现有 policy，不做推倒重来

当前模块拆分整体方向是正确的，不建议为了做“单一内核”而把所有逻辑重新塞回一个巨型 service。正确做法是：

- 保留当前 evaluator、phase、recommendation、branch、telemetry、reporting 等 policy
- 在它们之上新增 `ks_core/kernel.py`
- 由 `kernel.py` 统一调度这些 policy
- 服务层只负责事务、持久化和接口出入参转换

### 8.2 模块收口映射建议

| 当前模块 | 后续定位 |
| --- | --- |
| `evaluator.py` | KS Core 的评估子能力 |
| `round_transition_policy.py` | KS Core 的状态推进子能力 |
| `phase_policy.py` | KS Core 的阶段解析子能力 |
| `recommendation_policy.py` | KS Core 的推荐排序子能力 |
| `round_flow_policy.py` | 拆出“流程控制壳”和“内核决策调用”两部分 |
| `branch_resolver.py` | KS Core 的分支解析子能力 |
| `telemetry_policy.py` | KS Core 的观测装配子能力 |
| `ending_policy.py` | KS Core 的结局收束子能力 |
| `reporting_policy.py` | 继续作为读模型聚合层，不强行塞入热路径内核 |
| `training_service.py` | 降为编排、事务、持久化壳层 |

### 8.3 服务层未来应保留的职责

`TrainingService` 后续仍然应保留以下职责：

- 读取会话
- 读取冻结快照
- 调用 `ks_kernel.run(...)`
- 将 `KSTransitionResult` 持久化
- 处理并发冲突和幂等
- 组装接口 DTO

这可以避免“算法收口”再次演化成“巨型 service 回潮”。

## 9. 开发路线建议

建议按 4 个阶段推进，而不是一次性重构。

### 阶段一：统一术语与边界

目标：先把 KS 说清楚。

建议动作：

1. 固定 KS 正式定义。
2. 固定输入、状态、输出术语表。
3. 明确 KS 内核与产品策略边界。
4. 明确哪些字段属于算法内核，哪些属于接口包装。

建议产出：

- `docs/KS术语定义.md`
- `docs/KS输入输出契约说明.md`

### 阶段二：建立显式 `KS Core`

目标：把当前分散在多处的主链路收口到统一调度接口。

建议动作：

1. 新增 `backend/training/ks_core/`
2. 提供 `ks_kernel.run(...)`
3. 让 `TrainingService.submit_round(...)` 改为调用内核
4. 让 `round_transition_policy`、`phase_policy`、`recommendation_policy`、`branch_resolver` 成为内核子能力

建议产出：

- `kernel.py`
- `input_model.py`
- `state_model.py`
- `result_model.py`

### 阶段三：建立验证与 benchmark 体系

目标：让 KS 可验证，而不是只可运行。

建议动作：

1. 建立标准回放样本集
2. 固化关键指标
3. 增加专项测试
4. 建立策略调参前后对比报告

建议测试文件：

- `backend/test_ks_kernel.py`
- `backend/test_ks_state_transition.py`
- `backend/test_ks_recommendation_consistency.py`
- `backend/test_ks_benchmark.py`

### 阶段四：方法论与品牌化沉淀

目标：把 KS 从工程能力沉淀成可对外表达的方法论资产。

建议动作：

1. 输出 KS 核心算法说明
2. 输出 KS 验证指标文档
3. 输出业务案例文档
4. 输出白皮书大纲
5. 统一品牌表达

## 10. 具体开发任务拆解

### 10.1 第一批可直接开发的任务

这批任务不需要推翻现有训练系统，可直接进入开发：

1. 新增 `ks_core` 目录和基础模型文件
2. 把当前提交链路里的关键输入收口成 `KSRoundInput`
3. 把当前状态快照收口成 `KSStateSnapshot`
4. 把当前回合结果收口成 `KSTransitionResult`
5. 在 `TrainingService.submit_round()` 中插入 `ks_kernel.run()` 调用
6. 为现有 policy 提供统一适配层

### 10.2 第二批应同步做的任务

1. 固化统一术语
2. 给每个 policy 输出稳定的标准结构，而不是临时字典
3. 把指标和回放样本写入测试工程
4. 给关键参数变化建立回归报告模板

### 10.3 暂时不要做的事情

为了避免架构反复，以下动作当前不建议优先：

1. 不建议把所有 policy 重新并回 `TrainingService`
2. 不建议先写白皮书再倒推实现
3. 不建议先做复杂机器学习化改造
4. 不建议把报告聚合层强行并入热路径内核

当前最重要的是先把“统一算法调度层”建立起来。

## 11. 验证与评估建议

### 11.1 核心验证维度

建议至少建立以下 6 类算法指标：

1. 状态更新稳定性
   - 同一输入回放时，`k_state / s_state` 更新结果是否稳定。

2. 风险识别准确性
   - 高风险输入是否能稳定触发同类 `risk_flags`。

3. 推荐排序合理性
   - 在固定状态下，推荐场景排序是否符合预期。

4. 分支跳转一致性
   - 相同运行时 flags 下，分支路径是否一致。

5. 结局区分度
   - 不同训练路径是否能形成可解释的不同结局。

6. 报告解释一致性
   - 报告摘要是否与真实状态变化、风险轨迹、关键轮次相一致。

### 11.2 benchmark 样本建议

每条 benchmark 样本至少包含：

- 初始 `k_state`
- 初始 `s_state`
- 固定场景序列
- 固定用户输入序列
- 预期 `risk_flags`
- 预期推荐结果
- 预期分支结果
- 预期结局范围

### 11.3 验证结果的使用方式

后续每次以下变更都应跑 benchmark：

- 权重调整
- 风险阈值调整
- 阶段窗口调整
- 推荐 boost 调整
- 分支规则调整
- 结局阈值调整

否则 KS 会长期停留在“能跑，但不知道是否变坏”的状态。

## 12. 结论

当前 BlazePen 训练系统中的 KS，已经不是简单原型，而是一套具备较强工程闭环能力的状态驱动训练体系。它已经具备：

- 稳定的 `k_state / s_state` 状态底座
- 单回合评估与状态推进能力
- 风险标记与运行时后果能力
- 阶段解析、推荐排序、分支跳转能力
- 结局收束、报告聚合、诊断解释能力
- 会话快照、恢复校验和读模型边界

但当前它仍然更接近“多策略协同系统”，还不是“统一单一算法内核”。后续的正确方向不是推倒重来，而是在保留当前模块化成果的基础上，新增一层显式 `KS Core` 抽象，把输入、状态、状态转移、结果输出和验证基线统一起来。只有完成这一步，KS 才能真正从工程实现进一步沉淀为可命名、可方法论化、可白皮书化的核心算法产品。
