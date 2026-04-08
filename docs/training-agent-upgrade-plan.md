# Training 端全 Agent 化升级计划

> 基于多轮架构审查与反驳讨论收敛的最终方案

---

## 一、当前系统诊断

### 已有模块与角色

| 模块 | 实际角色 | 当前状态 |
|---|---|---|
| `StoryScriptAgent` | Generator Agent（叙事生成） | 已完成，但结构语义错误 |
| `TrainingRoundEvaluator` | Evaluator/Critic Agent（LLM+规则融合） | 已完成，工业级 |
| `ConsequenceEngine` | World Simulator（规则推演） | 已完成，保持现状 |
| `RecommendationPolicy` | 规则打分推荐 | 已完成，但未 Agent 化 |
| `RecommendationAgent` | Recommendation Agent（LLM 覆盖） | 已写，死代码，0% 生效 |
| `TrainingService` | 隐式 Orchestrator | 硬编码 pipeline，无决策能力 |
| `Director Agent` | 显式流程控制 | 不存在 |
| `Behavior Profile Agent` | 用户行为模式抽象 | 不存在 |

### 核心问题清单

1. `RecommendationAgent` 没有接入系统（死代码）
2. `TrainingRoundFlowPolicy` 里 `ranked_candidates[0]` 硬编码，LLM 覆盖永远不触发
3. `Evaluator` prompt 无状态，每轮独立评估，无历史行为感知
4. 双结构源不一致：叙事层（间隙 transition，2个）vs 训练层（延伸 extension，2~3个随机）
5. `Director Agent` 不存在，流程控制全靠硬编码

---

## 二、全 Agent 化可行性结论

| 模块 | 可行性 | 风险 | 决策 |
|---|---|---|---|
| RecommendationAgent | 高 | 中 | 做 |
| Director Agent | 高 | 低 | 做（规则版先跑） |
| TrainingRoundEvaluator | 高 | 低 | 做（加历史注入） |
| ConsequenceEngine | 低 | 高 | 不做 |
| StoryScriptAgent | 已完成 | — | 修复语义，Phase 2 重构 |
| Behavior Profile Agent | 中 | 中 | Phase 2 做 |

**ConsequenceEngine 不 Agent 化：** 其 4 个 flags 直接影响分支跳转、结局判断和审计日志，是不可逆的业务决策。LLM 不确定性与这些语义冲突，Agent 化会降低系统质量。

---

## 三、Phase 1：让现有 Agent 真正工作

### 1.1 修复场景结构一致性

**问题：** 叙事层（StoryScriptAgent）和训练层（SessionStorylinePolicy）存在双结构源：
- 叙事层：间隙插入 micro（transition 语义），2个/间隙，总计 6+10=16
- 训练层：大场景后跟随 micro（extension 语义），2~3个随机，总计 6+12~18

**目标：** 统一为 6 大 + 18 小 = 24 个场景，语义一致（extension）。

**改动 1：`session_storyline_policy.py`**
```python
micro_scene_min: int = 3   # 2 → 3
micro_scene_max: int = 3   # 保持 3，取消随机
```

**改动 2：`story_script_agent.py`**
```python
@dataclass
class StoryScriptAgentConfig:
    major_scene_count: int = 6
    micro_scenes_per_gap: int = 3   # 2 → 3
```

**改动 3：`story_script_agent.py` prompt 语义修复**
```python
# 数量计算：间隙模式 → 延伸模式
total_micro = required_major * self.config.micro_scenes_per_gap  # 6×3=18

# prompt 结构描述替换
# 原：每两个相邻大场景之间插入 X 个小场景
# 改：每个大场景之后紧跟 3 个小场景，小场景是大场景情境的延伸（extension），
#     不是大场景之间的过渡（transition）

# system_message 补充
"小场景是大场景的情境延伸，不是大场景之间的过渡桥接。"
```

---

### 1.2 重写 RecommendationAgent（接入系统）

**核心设计：继承 `RecommendationPolicy`，重写 `rank_candidates`**

继承而非重写的价值：兼容旧系统、支持 A/B test、可一键回退，`TrainingRoundFlowPolicy` 零改动。

```python
class RecommendationAgent(RecommendationPolicy):
    def rank_candidates(self, ...) -> List[Dict[str, Any]]:
        ranked = super().rank_candidates(...)   # 规则排序先跑，保证兜底
        if not ranked or not self._should_llm_override(...):
            return ranked
        override = self._llm_override(ranked, ...)
        if override:
            override["recommendation"]["override_source"] = "llm"
            return [override] + [c for c in ranked if c.get("id") != override.get("id")]
        return ranked

    def _should_llm_override(self, k_state, s_state, recent_risk_rounds) -> bool:
        # 从 runtime_config 读阈值，不硬编码
        cfg = self.runtime_config.recommendation.llm_override
        if not cfg.enabled:
            return False
        recent = list(recent_risk_rounds or [])[-2:]
        if len(recent) >= 2 and all(r for r in recent):
            return True
        if any(v < cfg.weak_skill_threshold for v in k_state.values()):
            return True
        if s_state.get("public_panic", 0.0) > cfg.panic_threshold:
            return True
        if s_state.get("editor_trust", 0.0) < cfg.editor_trust_threshold:
            return True
        return False
```

**需要同步修改的文件：**

`training/config/training_runtime_config.json` — 新增配置节：
```json
"recommendation": {
  "...现有字段...",
  "llm_override": {
    "enabled": true,
    "weak_skill_threshold": 0.3,
    "panic_threshold": 0.7,
    "editor_trust_threshold": 0.25,
    "max_tokens": 200,
    "temperature": 0.2
  }
}
```

`training/config_loader.py` — 新增 Pydantic 模型：
```python
class RecommendationLlmOverrideConfig(BaseModel):
    enabled: bool = True
    weak_skill_threshold: float = 0.3
    panic_threshold: float = 0.7
    editor_trust_threshold: float = 0.25
    max_tokens: int = 200
    temperature: float = 0.2
```

`api/services/training_service.py` — 注入点替换：
```python
from training.recommendation_agent import RecommendationAgent
self.recommendation_policy = recommendation_policy or RecommendationAgent(
    runtime_config=self.runtime_config,
    phase_policy=self.phase_policy,
)
```

`training/__init__.py` — 新增导出 `RecommendationAgent`

**不需要改动：** `round_flow_policy.py`、`decision_context_policy.py`、API 路由层

---

### 1.3 新增 Director Agent（规则版）

**文件：** `backend/training/director_agent.py`

```python
@dataclass
class ExecutionPlan:
    needs_script_refresh: bool = False
    force_low_risk_scenario: bool = False
    eval_retry_budget: int = 1
    branch_hint: str | None = None

class TrainingDirectorAgent:
    """显式流程控制 Agent。
    第一阶段纯规则，use_llm=False 为默认，Phase 3 可配置开启。
    """

    def plan(
        self,
        *,
        session: Any,
        k_before: Dict[str, float],
        s_before: Dict[str, float],
        recent_risk_rounds: List[List[str]],
        runtime_flags: Dict[str, Any],
        training_mode: str,
        use_llm: bool = False,   # 预留接口
    ) -> ExecutionPlan:
        return ExecutionPlan(
            needs_script_refresh=self._check_script_refresh_needed(session),
            force_low_risk_scenario=self._check_force_low_risk(
                recent_risk_rounds, runtime_flags
            ),
            eval_retry_budget=self._resolve_eval_retry_budget(runtime_flags),
            branch_hint=self._resolve_branch_hint(runtime_flags),
        )
```

**接入位置：** `TrainingService.submit_round` 开头插入 `director_agent.plan()` 调用，后续流程根据 `ExecutionPlan` 调整行为。

---

### 1.4 Evaluator 历史上下文注入

**改动范围：** `training/evaluator.py`、`training/round_transition_policy.py`

```python
# evaluator.py：新增可选参数（向后兼容）
def evaluate_round(
    self,
    user_input: str,
    scenario_id: str,
    round_no: int,
    k_before: Optional[Dict[str, float]] = None,
    s_before: Optional[Dict[str, float]] = None,
    recent_history: Optional[List[Dict[str, Any]]] = None,  # 新增
) -> Dict[str, Any]: ...

# _build_llm_messages：注入历史摘要
# round_no < 3 时不注入，避免少量数据产生噪声
if recent_history and round_no >= 3:
    history_summary = "\nrecent_rounds=" + json.dumps(
        [{"round": h.get("round_no"), "risk_flags": h.get("risk_flags", [])}
         for h in recent_history[-3:]],
        ensure_ascii=False
    )
```

---

## 四、Phase 2：提升系统智能（数据积累后）

> 前提：Phase 1 完成并稳定运行，有足够历史数据（建议 > 50 个会话）

### 2.1 Behavior Profile Agent

**职责：** 从历史 round 数据中抽象用户行为模式，供 Director 和 Recommendation 使用。

**输出结构：**
```json
{
  "behavior_pattern": "aggressive_publisher",
  "risk_trend": "increasing",
  "skill_trend": {"K1": "declining", "K5": "stable"},
  "confidence": 0.7,
  "data_rounds": 6
}
```

**保护机制：** `data_rounds < 4` 时不生成 profile，返回 `null`，避免少量数据过拟合。

**接入点：**
- `Director.plan()` 接收 `behavior_profile`，调整 `force_low_risk` 判断
- `RecommendationAgent._llm_override()` 的 prompt 注入 profile 摘要
- `Evaluator._build_llm_messages()` 注入 `behavior_pattern`

### 2.2 Evaluator 行为模式注入升级

在 Phase 1 基础上，将历史注入从 `risk_flags` 升级为结构化行为摘要：

```python
# Phase 1（已做）
"recent_rounds=[{round_no, risk_flags}, ...]"

# Phase 2（升级）
"behavior_profile={pattern, risk_trend, skill_trend, confidence}"
```

### 2.3 StoryScriptAgent 结构重构（独立立项）

**目标：** 让 StoryScriptAgent 消费 `scenario_payload_sequence`，为每个 scenario 填充叙事内容，不再自己定义结构。

**涉及改动（跨层级，必须独立立项）：**
- `TrainingStoryScriptExecutor`：传完整序列（含 micro）
- `StoryScriptAgent`：prompt 从"生成结构"改为"填充内容"
- `TrainingStoryScript` 表：payload 结构变更，需要数据迁移
- 前端：适配新的 payload 结构

---

## 五、Phase 3：高级阶段（按需）

### 3.1 Director 部分 LLM 化

在 `use_llm=False` 接口基础上，对复杂决策场景开启 LLM：
- 多风险叠加（`source_exposed` + `panic_triggered` + `editor_locked` 同时触发）
- 用户行为模式突变（Behavior Profile 置信度骤降）

通过 `training_runtime_config.json` 的 `director.use_llm` 开关控制，默认 `false`。

### 3.2 RecommendationAgent top-k 重排

将 LLM 从"覆盖 top-1"升级为"对全部候选打分重排"。

**前置条件：** 需要同步修改 `validate_submission` 的校验逻辑，让校验以 LLM 排序为准（当前 `adaptive` 模式下校验的是规则 top-1）。

---

## 六、改动影响范围

### Phase 1 改动清单

| 文件 | 改动类型 | 破坏性 |
|---|---|---|
| `training/session_storyline_policy.py` | 参数默认值修改 | 无 |
| `training/story_script_agent.py` | 参数默认值 + prompt 修改 | 无 |
| `training/recommendation_agent.py` | 完整重写（继承 RecommendationPolicy） | 无 |
| `training/config/training_runtime_config.json` | 新增 `recommendation.llm_override` 节 | 无 |
| `training/config_loader.py` | 新增 Pydantic 模型 | 无 |
| `training/director_agent.py` | 新增文件 | 无 |
| `training/__init__.py` | 新增导出 | 无 |
| `training/evaluator.py` | 新增可选参数 | 向后兼容 |
| `training/round_transition_policy.py` | 透传新参数 | 向后兼容 |
| `api/services/training_service.py` | 注入点替换 + Director 插入 | 最小改动 |

**不改动：** `round_flow_policy.py`、`consequence_engine.py`、`contracts.py`、API 路由层

### 系统级风险

**延迟：** Director（规则，<1ms）+ RecommendationAgent（仅触发条件下约 300ms）+ Evaluator（已有 LLM）。正常情况下只有 Evaluator 调 LLM，触发条件下增加 Recommendation 的 LLM 调用。

**故障隔离：** 每个 Agent 的 LLM 调用都有独立 fallback，任何一个失败不影响其他 Agent 和主流程。

---

## 七、实施顺序

```
Step 1  修复场景结构一致性（1.1）
        session_storyline_policy.py + story_script_agent.py

Step 2  重写 RecommendationAgent（1.2）
        recommendation_agent.py + config + config_loader + __init__

Step 3  注入 TrainingService（1.2 + 1.3）
        training_service.py 替换注入点 + director_agent.py 新增

Step 4  Evaluator 历史注入（1.4）
        evaluator.py + round_transition_policy.py

─── Phase 1 完成，系统进入真正多 Agent 状态 ───

Step 5  Behavior Profile Agent（2.1）
        等 Phase 1 稳定 + 数据积累后

Step 6  StoryScriptAgent 结构重构（2.3）
        独立立项，单独排期
```

---

## 八、技术债记录

| 债务 | 影响 | 优先级 |
|---|---|---|
| StoryScriptAgent 与训练层 ID 不统一 | UX debt（叙事与训练路径松耦合） | Phase 2 |
| Director 是规则版（高级 if-else） | 复杂决策场景规则会膨胀 | Phase 3 |
| RecommendationAgent 只覆盖 top-1 | 无法做策略性路径规划 | Phase 3 |
| Evaluator 历史注入只有 risk_flags | 看不到行为模式 | Phase 2 |
