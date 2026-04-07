# Requirements Document

## Introduction

本需求文档描述新闻职业技能训练系统（`backend/training/`）的 Phase 1 多 Agent 升级方案。
该升级包含四个独立步骤：场景结构一致性修复、RecommendationAgent 重写接入、新增 Director Agent（规则版）、以及 Evaluator 历史上下文注入。
升级目标是在不破坏现有 API 契约的前提下，使训练系统的叙事层与训练层结构对齐，并为后续 LLM 驱动的智能决策预留可注入接口。

## Glossary

- **StoryScriptAgent**：叙事层 Agent，负责为训练会话生成连续剧本（`backend/training/story_script_agent.py`）。
- **SessionStorylinePolicy**：训练层策略，负责将大场景序列扩展为大场景 + 小场景的连续路线（`backend/training/session_storyline_policy.py`）。
- **Major Scene（大场景）**：训练序列中的主线场景，`scene_type=major`，共 6 个。
- **Micro Scene（小场景）**：附属于大场景的延伸场景，`scene_type=micro`，语义为"延伸"而非"过渡"。
- **RecommendationAgent**：推荐 Agent，继承 `RecommendationPolicy`，在规则排序基础上可选接入 LLM 覆盖（`backend/training/recommendation_agent.py`）。
- **RecommendationPolicy**：规则推荐策略基类，负责对候选场景排序（`backend/training/recommendation_policy.py`）。
- **TrainingDirectorAgent**：新增的 Director Agent，负责在每轮提交前生成执行计划（`backend/training/director_agent.py`，待新增）。
- **ExecutionPlan**：Director Agent 输出的执行计划 dataclass，包含 `needs_script_refresh`、`force_low_risk_scenario`、`eval_retry_budget`、`branch_hint` 字段。
- **TrainingRoundEvaluator**：训练回合评估器，负责 LLM 评估、规则校准与失败回退（`backend/training/evaluator.py`）。
- **TrainingRoundTransitionPolicy**：回合状态推进策略，负责编排评估、状态演化和工件回写（`backend/training/round_transition_policy.py`）。
- **TrainingService**：训练服务层，负责业务编排与持久化（`backend/api/services/training_service.py`）。
- **training_runtime_config.json**：训练系统运行时配置文件（`backend/training/config/training_runtime_config.json`）。
- **RecommendationLlmOverrideConfig**：新增的 Pydantic 配置模型，描述 LLM 覆盖触发条件（`backend/training/config_loader.py`，待新增）。
- **recent_history**：最近若干轮的历史摘要列表，格式为 `List[Dict[str, Any]]`，用于注入 Evaluator 上下文。

---

## Requirements

### Requirement 1：场景结构一致性修复

**User Story：** 作为训练系统维护者，我希望叙事层和训练层使用相同的场景结构（6 大 + 18 小 = 24 个场景），并且小场景的语义统一为"延伸"，以便两层的剧情逻辑保持一致，避免场景数量和语义双重不一致导致的训练体验断裂。

#### Acceptance Criteria

1. THE `SessionStorylinePolicy` SHALL 在初始化时使用 `micro_scene_min=3, micro_scene_max=3`，使每个大场景后固定跟随 3 个小场景。
2. WHEN `SessionStorylinePolicy.build_session_sequence` 被调用时，THE `SessionStorylinePolicy` SHALL 为 6 个大场景各生成恰好 3 个小场景，总场景数为 24。
3. THE `StoryScriptAgent` SHALL 在 `StoryScriptAgentConfig` 中使用 `micro_scenes_per_gap=3`，使每两个相邻大场景之间生成 3 个小场景。
4. WHEN `StoryScriptAgent` 计算总场景数时，THE `StoryScriptAgent` SHALL 使用延伸模式计算公式：`total_micro = major_scene_count * micro_scenes_per_gap`，而非间隙模式公式 `(major_scene_count - 1) * micro_scenes_per_gap`。
5. WHEN `StoryScriptAgent` 生成 LLM prompt 时，THE `StoryScriptAgent` SHALL 将小场景的语义描述从"过渡"改为"延伸"，确保生成的剧本内容与训练层语义一致。
6. IF `SessionStorylinePolicy` 或 `StoryScriptAgent` 的场景数量计算结果不一致，THEN THE System SHALL 在单元测试中检测到差异并报告失败。

---

### Requirement 2：RecommendationAgent 重写接入

**User Story：** 作为训练系统架构师，我希望 `RecommendationAgent` 能够继承 `RecommendationPolicy` 并直接替换注入点，以便在不改变调用方代码结构的前提下，将 LLM 覆盖能力无缝接入现有推荐流程。

#### Acceptance Criteria

1. THE `RecommendationAgent` SHALL 继承 `RecommendationPolicy`，使其可在 `TrainingService.__init__` 和 `TrainingRoundFlowPolicy.__init__` 的 `recommendation_policy` 注入点直接替换。
2. THE `RecommendationAgent` SHALL 重写 `rank_candidates` 方法：规则排序始终先执行，仅在满足触发条件时用 LLM 覆盖 top-1 结果。
3. WHEN `RecommendationAgent.rank_candidates` 被调用时，THE `RecommendationAgent` SHALL 先调用父类 `RecommendationPolicy.rank_candidates` 获得规则排序结果，再判断是否触发 LLM 覆盖。
4. WHEN LLM 覆盖被触发时，THE `RecommendationAgent` SHALL 仅替换排序列表中的 top-1 场景，其余候选顺序保持不变。
5. WHEN LLM 调用失败或返回无效结果时，THE `RecommendationAgent` SHALL 静默降级，返回规则排序的原始 top-1，不抛出异常。
6. THE `RecommendationAgent` SHALL 从 `training_runtime_config.json` 的 `recommendation.llm_override` 配置节读取触发条件，而非硬编码在代码中。
7. THE `training_runtime_config.json` SHALL 新增 `recommendation.llm_override` 配置节，包含触发条件字段（如 `min_consecutive_risk_rounds`、`min_weak_skill_threshold`、`max_public_panic`、`min_editor_trust`）。
8. THE `config_loader.py` SHALL 新增 `RecommendationLlmOverrideConfig` Pydantic 模型，并将其嵌入 `RecommendationConfig`，使配置加载时自动校验触发条件字段类型与范围。
9. THE `backend/training/__init__.py` SHALL 导出 `RecommendationAgent`，使调用方可通过统一入口引用。
10. THE `TrainingService` SHALL 在 `__init__` 中将 `recommendation_policy` 的默认实例替换为 `RecommendationAgent`，使 LLM 覆盖能力在不传入自定义策略时自动生效。
11. IF `RecommendationAgent` 的 `rank_candidates` 返回结果，THEN THE 返回列表中每个场景的 `recommendation` 元信息 SHALL 包含 `override_source` 字段，值为 `"llm"` 或 `"rules"`，以便审计链路可区分决策来源。

---

### Requirement 3：新增 Director Agent（规则版）

**User Story：** 作为训练系统架构师，我希望在每轮提交前插入一个 Director Agent，由其生成执行计划并指导后续流程，以便为未来接入 LLM 决策预留标准化接口，同时当前版本以纯规则实现保证稳定性。

#### Acceptance Criteria

1. THE System SHALL 新增文件 `backend/training/director_agent.py`，包含 `ExecutionPlan` dataclass 和 `TrainingDirectorAgent` 类。
2. THE `ExecutionPlan` SHALL 包含以下字段：`needs_script_refresh: bool`、`force_low_risk_scenario: bool`、`eval_retry_budget: int`、`branch_hint: Optional[str]`。
3. THE `TrainingDirectorAgent` SHALL 提供 `plan(session, round_no, k_state, s_state, recent_risk_rounds, runtime_flags) -> ExecutionPlan` 方法，作为统一的执行计划生成入口。
4. WHILE `use_llm=False`（默认值），THE `TrainingDirectorAgent.plan` SHALL 使用纯规则逻辑生成 `ExecutionPlan`，不调用任何 LLM 服务。
5. WHERE `use_llm=True` 被配置，THE `TrainingDirectorAgent` SHALL 预留 LLM 决策接口，但当前版本可返回与规则版相同的结果或抛出 `NotImplementedError`。
6. THE `TrainingService.submit_round` SHALL 在方法开头（评估和推荐逻辑之前）调用 `TrainingDirectorAgent.plan`，获取 `ExecutionPlan`。
7. WHEN `ExecutionPlan.needs_script_refresh` 为 `True` 时，THE `TrainingService` SHALL 记录日志标记本轮需要剧本刷新，供后续扩展使用（当前版本不需要实际触发刷新）。
8. WHEN `ExecutionPlan.force_low_risk_scenario` 为 `True` 时，THE `TrainingService` SHALL 将该标记传递给推荐流程，供后续扩展使用（当前版本不需要实际过滤场景）。
9. IF `TrainingDirectorAgent.plan` 抛出异常，THEN THE `TrainingService` SHALL 捕获异常并使用默认 `ExecutionPlan`（所有字段为安全默认值），不中断 `submit_round` 主流程。

---

### Requirement 4：Evaluator 历史上下文注入

**User Story：** 作为训练系统架构师，我希望 Evaluator 在评估时能够感知最近几轮的历史摘要，以便 LLM 评估可以结合上下文做出更准确的判断，同时保证向后兼容，不传历史时行为与现在完全一致。

#### Acceptance Criteria

1. THE `TrainingRoundEvaluator.evaluate_round` SHALL 新增可选参数 `recent_history: Optional[List[Dict[str, Any]]] = None`，默认值为 `None`，保证向后兼容。
2. WHEN `recent_history` 为 `None` 或空列表时，THE `TrainingRoundEvaluator` SHALL 与当前行为完全一致，不修改任何评估逻辑或输出结构。
3. WHEN `recent_history` 非空且 `round_no >= 3` 时，THE `TrainingRoundEvaluator._build_llm_messages` SHALL 将历史摘要注入 LLM prompt，以提升上下文感知能力。
4. WHEN `round_no < 3` 时，THE `TrainingRoundEvaluator` SHALL 不注入历史摘要，即使 `recent_history` 非空。
5. THE `TrainingRoundTransitionPolicy.build_round_transition_artifacts` SHALL 新增可选参数 `recent_history: Optional[List[Dict[str, Any]]] = None`，并将其透传给 `evaluator.evaluate_round`。
6. THE `TrainingService.submit_round` SHALL 构建 `recent_history` 列表（从已落库的历史回合中提取摘要），并在调用 `round_transition_policy.build_round_transition_artifacts` 时传入该参数。
7. IF `recent_history` 中的某条记录格式不合法（缺少必要字段），THEN THE `TrainingRoundEvaluator` SHALL 跳过该条记录，不抛出异常，并继续处理其余记录。
8. THE `TrainingRoundEvaluator._build_llm_messages` 注入的历史摘要 SHALL 只包含对评估有意义的字段（如 `round_no`、`scenario_id`、`risk_flags`、`evidence` 摘要），不包含原始用户输入全文，以控制 token 消耗。
