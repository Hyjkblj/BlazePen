# Implementation Plan: Training Multi-Agent Upgrade

## Overview

按四个独立 Step 组织实现任务，每个 Step 可独立合并、独立回滚，不破坏现有 API 契约。
所有代码使用 Python 实现，测试使用 pytest + Hypothesis。

## Tasks

- [x] 1. Step 1：场景结构一致性修复
  - [x] 1.1 修改 `session_storyline_policy.py`：将默认参数 `micro_scene_min` 从 `2` 改为 `3`
    - 修改 `SessionStorylinePolicy.__init__` 签名，将 `micro_scene_min: int = 2` 改为 `micro_scene_min: int = 3`
    - `micro_scene_max` 保持 `3` 不变，两者相等使每个大场景后固定生成 3 个小场景
    - 内部 `build_session_sequence` 逻辑不需要改动，`rng.randint(3, 3)` 始终返回 3
    - _Requirements: 1.1, 1.2_

  - [x]* 1.2 为 `SessionStorylinePolicy` 编写属性测试（Property 1）
    - **Property 1: 场景总数不变量**
    - **Validates: Requirements 1.2**
    - 使用 `@given(st.integers(min_value=1, max_value=10))` 生成任意大场景数
    - 验证 `major_scenes == major_count`，`micro_scenes == major_count * 3`

  - [x] 1.3 修改 `story_script_agent.py`：更新 `StoryScriptAgentConfig` 默认值与计算公式
    - 将 `StoryScriptAgentConfig.micro_scenes_per_gap` 默认值从 `2` 改为 `3`
    - 在 `_call_llm_generate_payload` 中将 `total_micro` 计算公式从间隙模式改为延伸模式：`total_micro = required_major * self.config.micro_scenes_per_gap`
    - 修改 LLM prompt 中小场景的语义描述：将"过渡"改为"延伸"，将"每两个相邻大场景之间插入"改为"每个大场景之后紧跟"，并补充"小场景是大场景情境的延伸（extension），不是大场景之间的过渡（transition）"
    - 修改 `_build_local_fallback_payload` 中的 micro 生成逻辑：将 `if major_index < required_major:` 改为无条件生成（每个大场景后都生成 micro）
    - _Requirements: 1.3, 1.4, 1.5_

  - [x]* 1.4 为 `StoryScriptAgent` 编写属性测试（Property 2）
    - **Property 2: 延伸模式总场景数公式**
    - **Validates: Requirements 1.4**
    - 使用 `@given(st.integers(min_value=1, max_value=10), st.integers(min_value=1, max_value=5))` 生成任意参数组合
    - 验证 prompt 中 `total_scenes` 使用延伸公式 `major_count + major_count * micro_per_gap`

  - [x]* 1.5 为 Step 1 编写单元测试
    - 验证 `SessionStorylinePolicy()` 默认参数 `micro_scene_min=3, micro_scene_max=3`（Requirements 1.1）
    - 验证 `StoryScriptAgentConfig()` 默认 `micro_scenes_per_gap=3`（Requirements 1.3）
    - 通过 mock `text_model_service` 捕获 prompt 内容，验证包含"延伸"而非"过渡"语义（Requirements 1.5）

- [x] 2. Step 2：RecommendationAgent 重写接入
  - [x] 2.1 修改 `config_loader.py`：新增 `RecommendationLlmOverrideConfig` Pydantic 模型并嵌入 `RecommendationConfig`
    - 新增 `RecommendationLlmOverrideConfig(BaseModel)`，包含字段：`enabled: bool = False`、`min_consecutive_risk_rounds: int = Field(default=2, ge=1)`、`min_weak_skill_threshold: float = Field(default=0.3, ge=0.0, le=1.0)`、`max_public_panic: float = Field(default=0.7, ge=0.0, le=1.0)`、`min_editor_trust: float = Field(default=0.25, ge=0.0, le=1.0)`
    - 在 `RecommendationConfig` 中新增字段 `llm_override: RecommendationLlmOverrideConfig = Field(default_factory=RecommendationLlmOverrideConfig)`
    - _Requirements: 2.6, 2.8_

  - [x] 2.2 修改 `training_runtime_config.json`：在 `recommendation` 节新增 `llm_override` 配置
    - 在 `backend/training/config/training_runtime_config.json` 的 `recommendation` 对象中新增 `llm_override` 子对象
    - 包含字段：`"enabled": false`、`"min_consecutive_risk_rounds": 2`、`"min_weak_skill_threshold": 0.3`、`"max_public_panic": 0.7`、`"min_editor_trust": 0.25`
    - _Requirements: 2.7_

  - [x] 2.3 重写 `recommendation_agent.py`：继承 `RecommendationPolicy`，实现 `rank_candidates` 覆盖与 LLM 降级逻辑
    - 将 `RecommendationAgent` 改为继承 `RecommendationPolicy`（而非当前实现）
    - 重写 `rank_candidates` 方法：先调用 `super().rank_candidates(...)` 获得规则排序，再为所有候选标记 `override_source="rules"`
    - 实现 `_should_llm_override` 方法：从 `self.recommendation_config.llm_override` 读取触发条件，判断连续高风险轮次、技能极低、公众恐慌过高、编辑信任极低四个条件
    - 实现 LLM 覆盖路径：触发时调用 `_llm_select_top1`，仅替换 top-1，其余顺序不变，top-1 的 `override_source` 改为 `"llm"`
    - 实现异常降级：LLM 调用失败时 try/except 捕获，记录 warning，返回规则排序原始结果
    - 实现 `_try_init_llm`：初始化失败时静默设置 `_llm_service = None`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.11_

  - [x]* 2.4 为 `RecommendationAgent` 编写属性测试（Property 3、4、5）
    - **Property 3: LLM 未触发时推荐结果与规则一致**
    - **Validates: Requirements 2.2, 2.3**
    - **Property 4: LLM 覆盖仅替换 top-1，其余顺序不变**
    - **Validates: Requirements 2.4, 2.11**
    - **Property 5: LLM 失败时静默降级**
    - **Validates: Requirements 2.5**
    - 使用 `@given(st.lists(...))` 生成任意候选场景列表

  - [x] 2.4 修改 `backend/training/__init__.py`：导出 `RecommendationAgent`
    - 在 `__init__.py` 中新增 `from training.recommendation_agent import RecommendationAgent`
    - 将 `"RecommendationAgent"` 加入 `__all__` 列表
    - _Requirements: 2.9_

  - [x] 2.5 修改 `training_service.py`：将 `recommendation_policy` 默认实例替换为 `RecommendationAgent`
    - 将 `from training.recommendation_policy import RecommendationPolicy` 替换为 `from training.recommendation_agent import RecommendationAgent`
    - 在 `__init__` 中将 `self.recommendation_policy = recommendation_policy or RecommendationPolicy(...)` 替换为 `self.recommendation_policy = recommendation_policy or RecommendationAgent(...)`
    - `recommendation_policy` 参数类型注解保持 `RecommendationPolicy | None`（`RecommendationAgent` 是其子类，类型兼容）
    - _Requirements: 2.1, 2.10_

  - [x]* 2.6 为 Step 2 编写单元测试
    - 验证 `isinstance(RecommendationAgent(), RecommendationPolicy)`（Requirements 2.1）
    - 验证 `from training import RecommendationAgent` 可正常导入（Requirements 2.9）
    - 验证 `TrainingService(db_manager=mock_db).recommendation_policy` 是 `RecommendationAgent` 实例（Requirements 2.10）

- [x] 3. Step 2 Checkpoint — 确保所有测试通过
  - 确保 Step 1 和 Step 2 的所有测试通过，如有问题请告知。

- [x] 4. Step 3：新增 Director Agent
  - [x] 4.1 新增 `director_agent.py`：实现 `ExecutionPlan` dataclass 和 `TrainingDirectorAgent` 类
    - 新建文件 `backend/training/director_agent.py`
    - 定义 `ExecutionPlan` dataclass，包含字段：`needs_script_refresh: bool = False`、`force_low_risk_scenario: bool = False`、`eval_retry_budget: int = 1`、`branch_hint: Optional[str] = None`
    - 实现 `TrainingDirectorAgent.__init__(*, use_llm: bool = False, runtime_config: Any = None)`
    - 实现 `plan(session, round_no, k_state, s_state, recent_risk_rounds, runtime_flags) -> ExecutionPlan` 方法：`use_llm=False` 时调用 `_plan_by_rules`；`use_llm=True` 时记录 debug 日志后同样回退到规则（预留接口）
    - 实现 `_plan_by_rules`：连续 2 轮高风险时 `force_low_risk=True`；任意技能 < 0.25 时 `needs_refresh=True`；`public_panic > 0.65` 时 `eval_retry_budget=2`，否则为 1
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x]* 4.2 为 `TrainingDirectorAgent` 编写属性测试（Property 10）
    - **Property 10: Director Agent 在任意输入下返回合法 ExecutionPlan**
    - **Validates: Requirements 3.4, 3.9**
    - 使用 `@given(st.dictionaries(...), st.dictionaries(...), st.integers(...))` 生成任意 k_state、s_state、round_no
    - 验证返回值是 `ExecutionPlan` 实例，所有字段类型合法，不抛出异常

  - [x] 4.3 修改 `training_service.py`：注入 `TrainingDirectorAgent` 并在 `submit_round` 开头调用
    - 在 `__init__` 中新增 `from training.director_agent import ExecutionPlan, TrainingDirectorAgent`
    - 在 `__init__` 中新增 `self.director_agent = TrainingDirectorAgent(runtime_config=self.runtime_config)`（支持外部注入覆盖）
    - 在 `submit_round` 方法开头（评估和推荐逻辑之前）插入 Director Agent 调用块：try 调用 `self.director_agent.plan(...)`，获取 `execution_plan`；当 `needs_script_refresh=True` 时记录 info 日志；当 `force_low_risk_scenario=True` 时记录 info 日志；except 捕获任意异常，记录 warning，使用 `ExecutionPlan()` 默认值继续
    - _Requirements: 3.6, 3.7, 3.8, 3.9_

  - [x]* 4.4 为 Step 3 编写单元测试
    - 验证 `ExecutionPlan` 包含四个必要字段（Requirements 3.2）
    - 验证 `submit_round` 调用 `director_agent.plan`（mock 注入验证，Requirements 3.6）
    - 验证 `director_agent.plan` 抛出异常时 `submit_round` 不中断（Requirements 3.9）

- [x] 5. Step 4：Evaluator 历史上下文注入
  - [x] 5.1 修改 `evaluator.py`：为 `evaluate_round` 新增 `recent_history` 可选参数并实现注入逻辑
    - 在 `evaluate_round` 签名中新增 `recent_history: Optional[List[Dict[str, Any]]] = None`
    - 将 `recent_history` 透传给 `_evaluate_by_llm`（同步更新 `_evaluate_by_llm` 签名）
    - 在 `_build_llm_messages` 签名中新增 `recent_history: Optional[List[Dict[str, Any]]] = None`
    - 在 `_build_llm_messages` 中实现历史注入逻辑：仅当 `round_no >= 3` 且 `recent_history` 非空时注入；遍历时跳过非 dict 记录（`isinstance` 检查）；每条记录只提取 `round_no`、`scenario_id`、`risk_flags`、`evidence`（最多 2 条）字段；将历史摘要以 `recent_history=<json>` 格式插入 user_prompt
    - `recent_history=None` 或空列表时行为与现有完全一致
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.7, 4.8_

  - [x]* 5.2 为 `TrainingRoundEvaluator` 编写属性测试（Property 6、7、8、9）
    - **Property 6: recent_history=None 时评估行为不变**
    - **Validates: Requirements 4.2**
    - **Property 7: 历史注入当且仅当 round_no >= 3 且 recent_history 非空**
    - **Validates: Requirements 4.3, 4.4**
    - **Property 8: 非法历史记录被跳过，不抛出异常**
    - **Validates: Requirements 4.7**
    - **Property 9: 历史摘要不包含原始用户输入全文**
    - **Validates: Requirements 4.8**

  - [x] 5.3 修改 `round_transition_policy.py`：为 `build_round_transition_artifacts` 新增 `recent_history` 参数并透传
    - 在 `build_round_transition_artifacts` 签名中新增 `recent_history: Optional[List[Dict[str, Any]]] = None`
    - 在调用 `evaluator.evaluate_round(...)` 时传入 `recent_history=recent_history`
    - _Requirements: 4.5_

  - [x] 5.4 修改 `training_service.py`：构建 `recent_history` 并传入 `build_round_transition_artifacts`
    - 新增辅助方法 `_build_recent_history(session_id, round_no, window=3) -> List[Dict[str, Any]]`：`round_no < 3` 时直接返回空列表；调用 `self.training_store.get_round_evaluations_by_session(session_id)` 获取历史回合；取最近 `window` 条，提取 `round_no`、`scenario_id`、`risk_flags`、`evidence[:2]` 字段；异常时记录 warning 并返回空列表
    - 在 `submit_round` 中调用 `self._build_recent_history(session_id=session_id, round_no=round_no)` 构建 `recent_history`
    - 在调用 `self.round_transition_policy.build_round_transition_artifacts(...)` 时传入 `recent_history=recent_history`
    - _Requirements: 4.6_

  - [x]* 5.5 为 Step 4 编写单元测试
    - 验证 `evaluate_round("test", "S1", 1)` 不传 `recent_history` 时正常返回（向后兼容，Requirements 4.1）
    - 验证 `round_no=2` 时即使传入非空 `recent_history` 也不注入历史（Requirements 4.4）
    - 验证 `_build_recent_history` 在 `round_no < 3` 时返回空列表（Requirements 4.6）

- [x] 6. Final Checkpoint — 确保所有测试通过
  - 确保所有 Step 的测试通过，如有问题请告知。

## Notes

- 标记 `*` 的子任务为可选测试任务，可跳过以加快 MVP 进度
- 每个子任务引用具体需求条款以保证可追溯性
- 属性测试使用 Hypothesis，每个属性最少运行 100 次（`@settings(max_examples=100)`）
- 每个属性测试通过注释标注对应设计文档属性编号，格式：`# Feature: training-multi-agent-upgrade, Property N: <property_text>`
- 四个 Step 相互独立，可按顺序逐步合并，每步均可独立回滚
