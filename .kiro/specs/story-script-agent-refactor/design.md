# 技术设计文档：StoryScriptAgent 结构重构

## 概述

本次重构解决叙事层与训练层之间的"双结构源"问题。当前 `StoryScriptAgent` 同时承担"定义结构"和"填充内容"两件事，导致叙事层自行维护一套 `major-1 / micro-1-1` ID 体系，与训练层 `SessionStorylinePolicy` 生成的 `scenario_payload_sequence` ID 体系不一致。

重构后：
- `StoryScriptAgent` 只负责**内容填充**，接收训练层已冻结的 `scenario_payload_sequence` 并为每个场景填充叙事内容
- 新增 `fill_scenario_narratives` 方法，旧方法 `ensure_script_for_session` 在兼容期内保留并标注 deprecation
- v2 payload 使用 `scenario_id` 为 key 的 `narratives` 字典，彻底消除 ID 不统一问题
- 提供 `resolve_narrative_for_scenario` 工具函数，支持双版本兼容读取

---

## 架构

### 整体数据流

```mermaid
flowchart TD
    A[TrainingService\n创建会话] -->|冻结场景序列| B[SessionScenarioSnapshotPolicy\nfreeze_session_snapshots]
    B -->|scenario_payload_sequence\n含 major + micro 共 24 个场景| C[session_meta 持久化]

    D[TrainingStoryScriptExecutor\n后台任务] -->|读取 session_snapshot| E[require_session_snapshots]
    E -->|完整 scenario_payload_sequence| F[StoryScriptAgent\nfill_scenario_narratives]

    F -->|allow_llm=True| G[LLM 调用\n填充 monologue/dialogue/bridge_summary/options_narrative]
    F -->|LLM 失败| H[本地 fallback\n确定性内容填充]

    G -->|v2 payload| I[TrainingStoryScript 表\nversion=training_story_script_v2]
    H -->|v2 payload + fallback_used=true| I

    J[消费方\nTrainingService/前端] -->|resolve_narrative_for_scenario| K{version?}
    K -->|v2| L[narratives\[scenario_id\]]
    K -->|v1 兼容| M[scenes\[\].scene_id 前缀匹配]
```

### 组件职责变化

| 组件 | 变化前 | 变化后 |
|---|---|---|
| `StoryScriptAgent` | 定义结构 + 填充内容 | 只填充内容，接收外部结构 |
| `TrainingStoryScriptExecutor` | 传 `major_scene_sources`（仅大场景） | 传完整 `scenario_payload_sequence`（含 micro） |
| payload 格式 | v1：`scenes` 数组，`scene_id=major-1` | v2：`narratives` 字典，key 为训练层 `scenario_id` |
| 消费方 | 按 `scenes[].scene_id` 查找 | 按 `narratives[scenario_id]` 查找，兼容 v1 |

---

## 组件与接口

### 1. v2 Pydantic 模型（新增）

```python
# backend/training/story_script_agent.py

class ScriptNarrativeLine(BaseModel):
    speaker: str
    content: str

class ScriptNarrativeOptionItem(BaseModel):
    option_id: str
    narrative_label: str   # 叙事化选项台词（区别于训练层的 label）
    impact_hint: str = ""

class ScriptNarrative(BaseModel):
    """单个场景的叙事内容，与 scenario_id 绑定。"""
    monologue: str = ""
    dialogue: List[ScriptNarrativeLine] = Field(default_factory=list)
    bridge_summary: str = ""
    options_narrative: Dict[str, ScriptNarrativeOptionItem] = Field(default_factory=dict)
    # key 为 option_id（A/B/C 或 opt-1/opt-2/opt-3）

class TrainingStoryScriptV2Payload(BaseModel):
    version: str = Field(default="training_story_script_v2")
    cast: List[Dict[str, str]] = Field(default_factory=list)
    narratives: Dict[str, ScriptNarrative] = Field(default_factory=dict)
    # key 为训练层 scenario_id
    fallback_used: bool = False
    generated_at: str = ""
```

### 2. `StoryScriptAgent.fill_scenario_narratives`（新增方法）

```python
def fill_scenario_narratives(
    self,
    *,
    session_id: str,
    scenario_payload_sequence: List[Dict[str, Any]],
    player_profile: Dict[str, Any] | None = None,
    allow_llm: bool = True,
) -> Dict[str, Any]:
    """为训练层的场景序列填充叙事内容，返回 v2 payload。

    - 不修改 scenario_id、title、brief、mission、options 等结构字段
    - LLM 失败时降级到本地 fallback
    - 返回的 payload 以 v2 格式写入 TrainingStoryScript 表
    """
```

**LLM prompt 语义变化：**

```
# 旧 prompt（生成结构）：
"生成一个包含 6 major + 18 micro 的连续剧本，结构如下..."
输出：scenes 数组，scene_id 由 LLM 自行命名

# 新 prompt（填充内容）：
"以下是 {N} 个训练场景，请为每个场景填充叙事内容。
 不要修改 scenario_id 和 title，只填充 monologue/dialogue/bridge_summary/options_narrative。
 输出以 scenario_id 为 key 的 narratives 字典。"
输出：narratives 字典，key 为训练层 scenario_id
```

**LLM 输出 schema：**

```json
{
  "version": "training_story_script_v2",
  "cast": [{"name": "...", "role": "..."}],
  "narratives": {
    "<scenario_id>": {
      "monologue": "...",
      "dialogue": [{"speaker": "...", "content": "..."}],
      "bridge_summary": "...",
      "options_narrative": {
        "A": {"option_id": "A", "narrative_label": "...", "impact_hint": "..."},
        "B": {"option_id": "B", "narrative_label": "...", "impact_hint": "..."},
        "C": {"option_id": "C", "narrative_label": "...", "impact_hint": "..."}
      }
    }
  }
}
```

### 3. `resolve_narrative_for_scenario`（新增工具函数）

```python
def resolve_narrative_for_scenario(
    payload: Dict[str, Any],
    scenario_id: str,
) -> Dict[str, Any]:
    """根据 payload version 自动选择读取路径，返回叙事内容字典。

    - v2：从 payload["narratives"][scenario_id] 读取
    - v1 或无 version：按 scene_id 前缀匹配（major-1, micro-1-1 等）
    - 找不到时返回空字典，不抛出异常
    """
```

**v1 兼容匹配逻辑：**

```python
# scenario_id 格式：{major_id} 或 {major_id}_micro_{major_index}_{micro_index}_{suffix}
# v1 scene_id 格式：major-1, micro-1-1

def _legacy_match_scene_id(scenario_id: str) -> str:
    """把训练层 scenario_id 映射到 v1 scene_id。"""
    # 大场景：直接用 major_scene_order 字段（如果有）
    # 小场景：用 major_scene_order + micro_scene_order 字段
    # 无法映射时返回空字符串
```

### 4. `TrainingStoryScriptExecutor._generate`（修改）

```python
def _generate(self, session_id: str) -> None:
    # 旧：只取前 6 个大场景
    major_scene_sources = snapshot_bundle.scenario_payload_sequence[:6]

    # 新：传完整序列（含 major + micro）
    full_sequence = list(snapshot_bundle.scenario_payload_sequence or [])
    if not full_sequence:
        logger.error("story script: empty scenario_payload_sequence session_id=%s", session_id)
        self.training_store.update_story_script_by_session_id(session_id, {"status": "failed", ...})
        return

    payload = agent.fill_scenario_narratives(
        session_id=session_id,
        scenario_payload_sequence=full_sequence,
        player_profile=player_profile,
        allow_llm=True,
    )
```

### 5. `ensure_script_for_session`（保留，标注 deprecation）

```python
def ensure_script_for_session(self, ...) -> Dict[str, Any]:
    """[DEPRECATED] 使用 fill_scenario_narratives 替代。
    
    兼容期内保留，不立即删除。
    新会话应使用 fill_scenario_narratives。
    """
```

---

## 数据模型

### v2 payload 完整结构

```json
{
  "version": "training_story_script_v2",
  "cast": [
    {"name": "陈编辑", "role": "总编把关"},
    {"name": "赵川", "role": "前线通讯员"},
    {"name": "林岚", "role": "摄影记者"},
    {"name": "老何", "role": "印刷与发布"},
    {"name": "周联络", "role": "群众反馈联络"}
  ],
  "narratives": {
    "scenario-001": {
      "monologue": "我知道每一句话都可能改变局势...",
      "dialogue": [
        {"speaker": "旁白", "content": "..."},
        {"speaker": "陈编辑", "content": "..."}
      ],
      "bridge_summary": "你把已核实与待核验分层归档，准备进入下一步。",
      "options_narrative": {
        "A": {"option_id": "A", "narrative_label": "先发布已核实事实", "impact_hint": "降低失真"},
        "B": {"option_id": "B", "narrative_label": "补强证据链后再发布", "impact_hint": "更稳但更慢"},
        "C": {"option_id": "C", "narrative_label": "先内部汇总", "impact_hint": "协同更顺"}
      }
    },
    "scenario-001_micro_1_1_abc12345": {
      "monologue": "...",
      "dialogue": [...],
      "bridge_summary": "...",
      "options_narrative": {...}
    }
  },
  "fallback_used": false,
  "generated_at": "2026-04-07T10:00:00"
}
```

### v1 → v2 兼容读取映射

| 训练层 scenario_id | v1 scene_id | 映射方式 |
|---|---|---|
| `scenario-001`（major） | `major-1` | 按 `major_scene_order` 字段 |
| `scenario-001_micro_1_1_xxx`（micro） | `micro-1-1` | 按 `major_scene_order` + `micro_scene_order` 字段 |

---

## 正确性属性

### Property A：v2 payload round-trip 不变性

*For any* 合法的 v2 payload，序列化为 JSON 后再反序列化，应得到等价的 payload 对象。

**Validates: Requirements 3.5**

### Property B：fill_scenario_narratives 不修改结构字段

*For any* `scenario_payload_sequence`，调用 `fill_scenario_narratives` 后，每个场景的 `id`、`title`、`brief`、`mission`、`options` 字段应与输入完全一致。

**Validates: Requirements 1.3, 1.4**

### Property C：resolve_narrative_for_scenario 不抛出异常

*For any* payload（包括 v1、v2、空字典、格式错误）和任意 `scenario_id`，`resolve_narrative_for_scenario` 应不抛出异常，找不到时返回空字典。

**Validates: Requirements 5.4**

### Property D：fallback 覆盖所有场景

*For any* `scenario_payload_sequence`，当 LLM 不可用时，fallback 路径应为序列中的每一个场景生成非空的叙事内容。

**Validates: Requirements 1.7**

---

## 错误处理

| 场景 | 处理方式 |
|---|---|
| LLM 返回空内容 | 记录 warning，进入重试（最多 2 次） |
| LLM JSON 解析失败 | 调用 JSON 修复流程，修复失败则降级 fallback |
| LLM 输出缺少某个 scenario_id | 对该场景使用 fallback 内容，记录 warning |
| `scenario_payload_sequence` 为空 | 记录 error，将剧本状态标记为 failed，不生成 |
| `resolve_narrative_for_scenario` 找不到 scenario_id | 返回空字典，不抛出异常 |

---

## 测试策略

### 单元测试

- `TrainingStoryScriptV2Payload` schema 校验（合法/非法输入）
- `fill_scenario_narratives` fallback 路径覆盖所有场景
- `resolve_narrative_for_scenario` v1/v2 双版本读取
- `ensure_script_for_session` 兼容期内仍可调用

### 属性测试（Hypothesis）

- Property A：v2 payload round-trip
- Property B：fill_scenario_narratives 不修改结构字段
- Property C：resolve_narrative_for_scenario 不抛出异常
- Property D：fallback 覆盖所有场景
