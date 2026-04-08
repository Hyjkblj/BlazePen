# 设计文档：场景视觉语义统一（scene-visual-semantic-unification）

## 架构概览

```
StoryScriptAgent（会话初始化后异步运行）
  └── fill_scenario_narratives()
        └── 每个场景生成：monologue / dialogue / bridge_summary
                         / visual_prompt ← 新增
                         / visual_elements ← 新增（可选）

生图链路（用户进入场景时触发）
  前端 useTrainingSceneImageFlow
    └── 读取 storyScriptPayload[scenario_id].visual_prompt
    └── buildTrainingSceneImageMediaTaskCreateParams({ visualPrompt })
    └── POST /v1/training/media/tasks
          └── TrainingMediaTaskProviderDispatcher._execute_image_task()
                └── payload["visual_prompt"] → scene_data["prompt"]  ← 优先
                └── fallback: brief + mission + decisionFocus 拼接
```

---

## 1. 后端：ScriptNarrative 模型扩展

### 1.1 Pydantic 模型变更

文件：`backend/training/story_script_agent.py`

```python
class ScriptNarrative(BaseModel):
    monologue: str
    dialogue: List[ScriptNarrativeLine]
    bridge_summary: str
    options_narrative: Dict[str, ScriptNarrativeOptionItem]
    visual_prompt: str = ""          # 新增：视觉描述，面向图像生成模型
    visual_elements: List[str] = []  # 新增：关键视觉元素列表（可选）
```

`visual_prompt` 默认空字符串，保证向后兼容（老数据反序列化不报错）。

### 1.2 fallback 视觉描述生成器

新增纯函数 `_build_fallback_visual_prompt`，确定性地从场景 payload 拼接视觉描述：

```python
def _build_fallback_visual_prompt(scenario: Dict[str, Any]) -> str:
    title = str(scenario.get("title") or "").strip()
    era_date = str(scenario.get("era_date") or scenario.get("eraDate") or "").strip()
    location = str(scenario.get("location") or "").strip()
    brief = str(scenario.get("brief") or "").strip()
    parts = [p for p in [era_date, location, title] if p]
    base = "、".join(parts) if parts else title or "训练场景"
    visual = f"{base}。{brief[:60]}" if brief else base
    return f"{visual}。视觉风格：纪实新闻叙事，环境细节真实，无人物特写。"
```

### 1.3 LLM prompt 扩展

`_build_prompt` 中在填充要求里增加 `visual_prompt` 字段说明：

```
- 为每个场景填充：monologue、dialogue、bridge_summary、options_narrative、
  visual_prompt（视觉描述，20-60字，描述画面环境/氛围/构图，不含心理活动）、
  visual_elements（3-5个关键视觉元素，字符串列表）
```

JSON schema 输出示例扩展：
```json
{
  "narratives": {
    "<scenario_id>": {
      "monologue": "...",
      "dialogue": [...],
      "bridge_summary": "...",
      "options_narrative": {...},
      "visual_prompt": "战争废墟中的街道，昏暗天空，远处燃烧的建筑，一名记者隐藏在墙后",
      "visual_elements": ["废墟街道", "烟雾", "隐藏的记者", "远处火光"]
    }
  }
}
```

### 1.4 fallback narrative 补充 visual_prompt

`_fallback_narrative` 函数在构建 `ScriptNarrative` 时调用 `_build_fallback_visual_prompt`：

```python
def _fallback_narrative(scenario: Dict[str, Any]) -> Dict[str, Any]:
    ...
    return ScriptNarrative(
        monologue=...,
        dialogue=[...],
        bridge_summary=...,
        options_narrative={...},
        visual_prompt=_build_fallback_visual_prompt(scenario),
        visual_elements=[],
    ).model_dump()
```

### 1.5 LLM 输出后处理：visual_prompt 兜底

在 `_fill_by_llm` 的 merge 阶段，对每个 narrative 检查 `visual_prompt`：

```python
for scenario in scenario_payload_sequence:
    sid = ...
    narrative = merged_narratives.get(sid, {})
    if not str(narrative.get("visual_prompt") or "").strip():
        narrative["visual_prompt"] = _build_fallback_visual_prompt(scenario)
    merged_narratives[sid] = narrative
```

---

## 2. 后端：生图链路接入 visual_prompt

文件：`backend/training/media_task_executor.py`

`_execute_image_task` 中，在构建 `scene_data` 前优先读取 `visual_prompt`：

```python
def _execute_image_task(self, payload: dict[str, Any]) -> dict[str, Any]:
    ...
    # 优先使用 visual_prompt，降级到现有拼接逻辑
    visual_prompt = self._optional_str(payload.get("visual_prompt"))
    prompt = visual_prompt or self._optional_str(payload.get("prompt")) or ""
    if not prompt:
        raise TrainingMediaTaskExecutionFailedError(...)
    ...
```

`_generate_single_scene_image` 中 `scene_data["prompt"]` 使用上述 `prompt`，不变。

---

## 3. 前端：buildTrainingSceneImageMediaTaskCreateParams 扩展

文件：`frontend/src/services/trainingApi.ts`

```typescript
export const buildTrainingSceneImageMediaTaskCreateParams = (options: {
  sessionId: string;
  roundNo: number;
  scenario: TrainingScenario;
  attemptNo?: number;
  generateStorylineSeries?: boolean;
  characterId?: number;
  visualPrompt?: string | null;  // 新增
}): TrainingMediaTaskCreateParams => {
  const fallbackPrompt = buildTrainingSceneImagePrompt(options.scenario);
  const prompt = options.visualPrompt?.trim() || fallbackPrompt;

  const payload: Record<string, unknown> = {
    ...
    prompt,
    scenario_prompt: fallbackPrompt,  // 保留原始 brief 拼接供后端参考
    visual_prompt: options.visualPrompt?.trim() || '',
    ...
  };
  ...
};
```

---

## 4. 前端：useTrainingSceneImageFlow 读取 visual_prompt

文件：`frontend/src/hooks/useTrainingSceneImageFlow.ts`

hook 需要接收 `storyScriptPayload` 作为额外参数（或通过 context 获取），
在创建 media task 时提取对应场景的 `visual_prompt`：

```typescript
// 从 storyScriptPayload 中读取当前场景的 visual_prompt
const visualPrompt = useMemo(() => {
  if (!storyScriptPayload || !sceneImageContext?.scenarioId) return null;
  try {
    const narrative = resolveNarrativeForScenario(storyScriptPayload, sceneImageContext.scenarioId);
    return (narrative?.visual_prompt as string) || null;
  } catch {
    return null;
  }
}, [storyScriptPayload, sceneImageContext?.scenarioId]);
```

在 `createTrainingMediaTask` 调用处传入：
```typescript
buildTrainingSceneImageMediaTaskCreateParams({
  ...
  visualPrompt,
})
```

### 接口变更

`useTrainingSceneImageFlow` 的参数类型扩展：
```typescript
export function useTrainingSceneImageFlow(
  sessionView: TrainingSessionViewState | null,
  storyScriptPayload?: unknown,  // 新增可选参数
): UseTrainingSceneImageFlowResult
```

调用方 `useTrainingMvpFlow` 传入 `storyScriptPayload`：
```typescript
const { payload: storyScriptPayload } = useStoryScriptPayload(sessionView?.sessionId);
const { sceneImageStatus, ... } = useTrainingSceneImageFlow(sessionView, storyScriptPayload);
```

---

## 5. 前端：resolveNarrativeForScenario 类型扩展

文件：`frontend/src/utils/trainingSession.ts`

`resolveNarrativeForScenario` 返回的对象中，`visual_prompt` 和 `visual_elements` 作为可选字段透传，
不需要修改函数签名，调用方直接读取 `narrative?.visual_prompt`。

---

## 6. 数据流时序

```
init_training
  └── story_script_executor.submit_session()  [异步]
        └── StoryScriptAgent.fill_scenario_narratives()
              └── 每个场景生成 visual_prompt（LLM 或 fallback）
              └── 存入 story_scripts 表

用户进入场景（currentScenario 变化）
  └── useStoryScriptPayload 拉取 story script（已缓存）
  └── useTrainingSceneImageFlow 触发
        └── resolveNarrativeForScenario → visual_prompt
        └── buildTrainingSceneImageMediaTaskCreateParams({ visualPrompt })
        └── POST /v1/training/media/tasks
              └── 后端优先用 visual_prompt 生图
```

---

## 7. 幂等键不变

`idempotencyKey` 格式不变：`training-scene-image:{sessionId}:{scenarioId}:attempt:{attemptNo}`

`visual_prompt` 的变化不影响幂等键，因为同一场景的 `visual_prompt` 在会话生命周期内是稳定的。
若 story script 尚未就绪时已创建了 task（用 fallback prompt），
后续 story script 就绪后不会重新生图（幂等保护），这是可接受的权衡。

---

## 8. 向后兼容策略

| 场景 | 处理方式 |
|------|---------|
| 老会话，story script 无 visual_prompt | `ScriptNarrative.visual_prompt` 默认 `""` 不报错，生图降级到 brief 拼接 |
| v1 格式 story script | `resolve_narrative_for_scenario` 返回 v1 scene dict，无 visual_prompt，生图降级 |
| story script 未生成完成 | `visualPrompt` 为 null，使用 fallback prompt，不阻塞生图 |
| LLM 未返回 visual_prompt | merge 阶段自动补 fallback visual_prompt |
