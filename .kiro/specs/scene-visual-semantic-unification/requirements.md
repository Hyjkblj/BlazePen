# 需求文档：场景视觉语义统一（scene-visual-semantic-unification）

## 概述

当前训练系统中，剧本 Agent（StoryScriptAgent）生成叙事内容（独白/对话/选项台词），
生图服务用场景 payload 的 `brief/mission/decisionFocus` 自行拼接 prompt 生图。
两条链路完全独立，导致"画面 ≠ 对话 ≠ 任务"的割裂体验。

本 spec 的目标是让 StoryScriptAgent 成为视觉语义的统一源头，
使生图 prompt 与叙事内容保持一致，提升训练沉浸感。

---

## 需求

### 1. ScriptNarrative 模型扩展

**1.1** `ScriptNarrative`（Pydantic 模型）必须新增 `visual_prompt` 字段（`str`，必填，默认空字符串），
用于描述该场景的视觉画面，面向图像生成模型。

**1.2** `ScriptNarrative` 应新增可选的 `visual_elements` 字段（`List[str]`，默认空列表），
列举场景中的关键视觉元素（如"废墟街道"、"烟雾"、"隐藏的记者"）。

**1.3** `visual_prompt` 必须是视觉描述，而非心理活动或叙事文本。
正确示例：`"战争废墟中的街道，昏暗天空，远处燃烧的建筑，一名记者隐藏在墙后"`
错误示例：`"我必须小心，这份情报可能暴露来源…"`（这是独白，不是视觉描述）

**1.4** `visual_prompt` 应与同场景的 `monologue`、`dialogue` 在世界观上保持一致，
即画面所呈现的环境、氛围、时代感应与叙事内容匹配。

---

### 2. StoryScriptAgent LLM 生成

**2.1** `StoryScriptAgent._fill_by_llm` 的 LLM prompt 必须要求模型为每个场景生成 `visual_prompt`。

**2.2** LLM 输出的 JSON schema 必须包含 `visual_prompt` 字段，
并在 `_try_parse_narratives` 中通过 Pydantic 校验。

**2.3** 若 LLM 未返回 `visual_prompt` 或返回空字符串，
系统必须自动降级：用场景的 `title + brief + location` 拼接一个基础视觉描述作为兜底。

**2.4** fallback 路径（`_fill_by_fallback` / `_fallback_narrative`）也必须生成合理的 `visual_prompt`，
基于场景的 `title`、`era_date`、`location`、`brief` 拼接，不得留空。

---

### 3. 生图链路接入 visual_prompt

**3.1** 后端 `TrainingMediaTaskProviderDispatcher._execute_image_task` 在构建 `scene_data` 时，
必须优先使用 payload 中的 `visual_prompt` 字段作为 `prompt`，
若不存在则降级到现有的 `brief/mission/decisionFocus` 拼接逻辑。

**3.2** 前端 `buildTrainingSceneImageMediaTaskCreateParams` 必须支持接收可选的 `visualPrompt` 参数，
若提供则将其作为 payload 的 `prompt` 和 `visual_prompt` 字段传递给后端。

**3.3** 前端 `useTrainingSceneImageFlow` 在创建 media task 时，
必须尝试从当前会话的 story script payload 中读取对应场景的 `visual_prompt`，
并将其传递给 `buildTrainingSceneImageMediaTaskCreateParams`。

**3.4** 当 story script 尚未生成完成（status 为 pending/running）或不存在时，
生图必须正常进行，使用降级 prompt，不得阻塞或报错。

---

### 4. 向后兼容

**4.1** 已存在的 story script 记录（无 `visual_prompt` 字段）必须被正常读取，
系统不得因缺少该字段而抛出异常。

**4.2** `resolve_narrative_for_scenario` 函数在返回叙事内容时，
若 `visual_prompt` 不存在，返回空字符串而非 null/undefined。

**4.3** v1 格式的 story script（`training_story_script_v1`）不包含 `visual_prompt`，
生图时必须完全降级到 brief 拼接，不得尝试读取不存在的字段。

---

### 5. 正确性属性（用于 Property-Based Testing）

**P1（一致性）**：对于任意场景，若 `visual_prompt` 非空，
则其内容必须是视觉描述（包含环境/场景词汇），而非纯心理活动文本。

**P2（覆盖性）**：`fill_scenario_narratives` 的输出中，
每个 scenario_id 对应的 narrative 必须包含非空的 `visual_prompt`（LLM 路径或 fallback 路径均须满足）。

**P3（降级安全性）**：当 story script payload 为 None、空字典、或缺少 `visual_prompt` 时，
`buildTrainingSceneImageMediaTaskCreateParams` 必须仍能生成有效的 prompt，不得抛出异常。

**P4（幂等性）**：相同的场景 payload 输入，fallback 路径生成的 `visual_prompt` 必须是确定性的（不含随机性）。
