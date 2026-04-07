# StoryScriptAgent 结构重构方案设计

## 背景与问题

当前 `StoryScriptAgent` 同时承担两件事：
1. **定义结构**：自己决定有几个 major、几个 micro、scene_id 怎么命名
2. **填充内容**：为每个场景生成独白、对话、选项

这导致叙事层（StoryScriptAgent）和训练层（SessionStorylinePolicy）存在**双结构源**：
- 叙事层自己生成 `major-1 / micro-1-1` 这套 ID 体系
- 训练层有自己的 `scenario_payload_sequence`，ID 体系不同

两套结构松耦合，叙事内容无法精确对应训练场景，是 Phase 2 的核心技术债。

---

## 重构目标

让 `StoryScriptAgent` 只做**内容填充**，不再定义结构：

- **输入**：`scenario_payload_sequence`（训练层已冻结的完整场景序列，含 major + micro）
- **输出**：为每个 scenario 填充 `monologue`、`dialogue`、`bridge_summary`、`options`
- **不再做**：自己决定场景数量、scene_id、结构顺序

---

## 改动范围

### 1. `StoryScriptAgent`（核心改动）

**现在：**
```python
def _call_llm_generate_payload(self, session_id, major_scene_sources, player_profile):
    # 自己构造 6 major + 18 micro 的结构
    # 自己定义 scene_id = major-1, micro-1-1
    # 生成完整剧本
```

**改后：**
```python
def fill_scenario_narratives(
    self,
    *,
    session_id: str,
    scenario_payload_sequence: List[Dict[str, Any]],  # 训练层传入
    player_profile: Dict[str, Any] | None = None,
    allow_llm: bool = True,
) -> Dict[str, Any]:
    """为训练层的场景序列填充叙事内容。
    
    输入的 scenario_payload_sequence 已经包含完整结构（id、title、brief、mission 等），
    本方法只负责填充 monologue、dialogue、bridge_summary、options_narrative。
    """
```

**prompt 语义变化：**
```
# 现在：
"生成一个包含 6 major + 18 micro 的连续剧本，结构如下..."

# 改后：
"为以下 {N} 个场景填充叙事内容（独白、对话、选项台词），
 场景结构和顺序已固定，不要修改 scene_id 和 title，
 只填充 monologue / dialogue / bridge_summary / options_narrative"
```

### 2. `TrainingStoryScriptExecutor`（调用方改动）

**现在：**
```python
# 传 major_scene_sources（只有大场景摘要）
agent.ensure_script_for_session(
    session_id=session_id,
    major_scene_sources=major_scene_sources,
)
```

**改后：**
```python
# 传完整序列（含 micro）
agent.fill_scenario_narratives(
    session_id=session_id,
    scenario_payload_sequence=full_sequence,  # 包含 major + micro
)
```

### 3. `TrainingStoryScript` 表（数据迁移）

payload 结构从：
```json
{
  "version": "training_story_script_v1",
  "scenes": [{"scene_id": "major-1", ...}, {"scene_id": "micro-1-1", ...}]
}
```

变为：
```json
{
  "version": "training_story_script_v2",
  "narratives": {
    "<scenario_id>": {
      "monologue": "...",
      "dialogue": [...],
      "bridge_summary": "...",
      "options_narrative": {...}
    }
  }
}
```

key 直接用训练层的 `scenario_id`，彻底消除 ID 不统一问题。

### 4. 前端适配

前端消费 story script 的地方需要从 `scenes[].scene_id` 改为按 `scenario_id` 查找 `narratives[scenario_id]`。

---

## 迁移策略

### 双版本兼容期

新旧 payload 版本共存，通过 `version` 字段区分：
- `training_story_script_v1`：旧结构，继续支持读取
- `training_story_script_v2`：新结构，新会话使用

```python
def _resolve_narrative_for_scenario(payload: dict, scenario_id: str) -> dict:
    version = payload.get("version", "training_story_script_v1")
    if version == "training_story_script_v2":
        return payload.get("narratives", {}).get(scenario_id, {})
    # v1 兼容：按 scene_id 前缀匹配
    return _legacy_match_scene(payload, scenario_id)
```

### 数据迁移

旧会话的 v1 payload 不做强制迁移，按需读取时走兼容路径。
新会话从创建时就写 v2 格式。

---

## 实施顺序

```
Step 1  定义 v2 payload schema（Pydantic 模型）
        新增 TrainingStoryScriptNarrativePayload

Step 2  重写 StoryScriptAgent.fill_scenario_narratives
        新方法，旧方法保留（兼容期）

Step 3  修改 TrainingStoryScriptExecutor
        传完整序列，调用新方法

Step 4  修改前端消费层
        按 scenario_id 查找 narratives

Step 5  写数据迁移脚本（可选）
        把旧 v1 payload 转换为 v2 格式

Step 6  删除旧方法和 v1 兼容路径（清理期）
```

---

## 风险与注意事项

| 风险 | 说明 | 缓解 |
|---|---|---|
| 前端改动范围 | 需要适配新的 payload 结构 | 双版本兼容期保证旧会话不受影响 |
| LLM prompt 变化 | 从"生成结构"改为"填充内容"，prompt 质量需要验证 | 先用 fallback 路径验证，再开 LLM |
| 数据迁移 | 旧会话 v1 payload 无法自动升级 | 兼容路径保留，不强制迁移 |
| 场景 ID 对齐 | micro 场景的 ID 在训练层是 `{major_id}_micro_1_1_xxx`，需要确保 LLM 能正确引用 | prompt 里明确传入 scenario_id，不让 LLM 自己命名 |

---

## 前置条件

- Phase 1 稳定运行（场景结构已统一为 6+18=24）
- `scenario_payload_sequence` 在会话创建时已冻结（`session_snapshot_policy` 已实现）
- 前端有足够的测试覆盖，能验证 narrative 消费逻辑

**建议独立立项，不与 Phase 2 其他任务混合。**
