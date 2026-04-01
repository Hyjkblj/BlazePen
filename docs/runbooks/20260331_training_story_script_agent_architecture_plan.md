# Training 剧情 Agent 优化方案（标准型架构，保持核心逻辑不变）

更新日期：2026-03-31  
适用范围：training 域 “story script / 剧情脚本”能力（agent + service + store + API）  
目标约束：**不改变核心业务逻辑**（已有→返回；池够大→复用；否则→生成；最终固化到 session），仅按标准型 agent 架构补齐“契约/状态机/幂等/可观测/热路径治理/测试”。

---

## 0. 当前核心问题（链路级）

- **热路径重任务**：`GET /v1/training/story-scripts/{session_id}` 内部可能触发 ensure（LLM + 校验 + 写库）。
- **读写语义混乱**：GET 隐式写入，缓存/重试/并发变得危险。
- **吞错假成功**：失败时返回空 payload，下游无法区分 “missing/pending/failed/缺表”。
- **耦合过高**：story script service 依赖 training service 内部 policy（依赖方向错误）。
- **复用策略风险**：从真实 session 抽样克隆，缺分桶/脱敏/溯源，存在隔离与一致性风险。
- **mapper 强契约缺失**：options=3、顺序/数量、映射键不稳（title 作为 key）。

---

## 1. 标准型 Agent 架构（推荐分层）

以“契约优先 + 单一事实源 + 可恢复 + 可观测”为标准，建议采用以下层次（保持现有目录习惯，新增少量模块）：

### 1.1 Router（`api/routers/`）
- 只做：参数校验、调用 service、返回 DTO（稳定结构）。
- **禁止**：在 router 中直接执行 LLM/复杂编排/写库循环。

### 1.2 Service（`api/services/`）
- 只做：业务编排（ensure 流程、状态机推进、幂等/并发保护调用）。
- 对外：提供稳定错误码与状态字段。

### 1.3 Agent（`training/story_script_agent.py`）
- 只做：**生成/复用决策与 payload 构建**（保持现有逻辑不变）。
- 不做：数据库细节、HTTP 细节、线程/队列细节、路由语义。

### 1.4 Store/Repository（`training/training_store.py` + `training/training_repository.py`）
- 单一事实源：`training_story_scripts` 表及其状态字段。
- 统一幂等：以 `session_id` 为唯一约束，保证同 session 只有一个脚本记录。

### 1.5 Async-task（建议新增 `training/async_tasks/` 或复用现有执行器）
- 负责：后台执行 ensure（LLM 调用、校验、落库），避免阻塞同步热路径。
- 最少形态：先用进程内任务队列/后台线程（开发期），上线后可切到 Celery/RQ/内置任务系统。

---

## 2. 契约（Contract）设计：状态机 + 错误码（前后端不冲突）

### 2.1 记录状态（建议新增到表字段；Phase A 可先放 payload.meta 兼容）
- `status`: `missing | running | ready | failed`
- `error_code`: 稳定常量（禁止依赖 message）
- `error_message`: 可选（展示用）
- `fallback_used`: bool（可选）
- `provider/model/source_script_id`: 现有字段保留

### 2.2 API（Phase A/B 双轨，避免断链）

#### Phase A（兼容旧前端）
- **GET** `/v1/training/story-scripts/{session_id}`
  - 暂时允许保留旧行为（可配置开关），但必须返回 `status/error_code` 字段（optional）。
- **POST** `/v1/training/story-scripts/{session_id}/ensure`
  - 幂等触发 ensure：返回 `status=running|ready|failed`。

前端消费：字段存在则按状态渲染；不存在则继续按旧 payload 逻辑（不冲突）。

#### Phase B（收敛旧语义）
- **GET 只读**：绝不触发 LLM/写库，仅返回当前记录与状态。
- ensure 只能通过 POST/后台任务推进。

### 2.3 错误码（建议最小集合）
- `TRAINING_STORY_SCRIPT_STORAGE_UNAVAILABLE`（缺表/DB 不可用）
- `TRAINING_STORY_SCRIPT_ALREADY_RUNNING`（并发 ensure 命中 running）
- `TRAINING_STORY_SCRIPT_LLM_EMPTY_OUTPUT`
- `TRAINING_STORY_SCRIPT_LLM_INVALID_JSON`
- `TRAINING_STORY_SCRIPT_VALIDATION_FAILED`
- `TRAINING_STORY_SCRIPT_MAPPING_INVALID_OPTIONS`

---

## 3. 幂等与并发保护（同 session 只允许一个 ensure 在飞）

### 推荐实现（DB 级，占位 running）
- 利用 `training_story_scripts.session_id` **唯一约束**：
  1. ensure 开始时尝试创建/更新记录为 `status=running`（若已 running 直接返回 running）
  2. 任务执行完成后写回 `ready/failed`

### 不建议仅用进程锁
- reload/多进程/多实例下无效，容易出现重复生成与外部依赖放大。

---

## 4. 复用策略（池化克隆）保持不变，但补“标准化兜底”

不改变“池够大就复用”的决策，但必须新增三项保证可恢复与隔离：

### 4.1 分桶过滤（不改策略，只缩小候选集）
- 给脚本增加维度（表字段或 payload.meta）：
  - `script_version`
  - `training_mode`
  - `scenario_bank_version`
- 抽样只在同桶内进行，避免契约漂移。

### 4.2 脱敏/去画像
- 克隆前对 payload 做最小清洗：
  - 移除或覆盖玩家可识别字段（name/identity 等），避免跨 session 画像污染。

### 4.3 溯源
- `source_script_id` 必须写入；建议在 payload.meta 里同时写入 `source_session_id`（内部排障用）。

---

## 5. Mapper 强契约（防止坏脚本进入训练主路径）

### 必须硬化的规则
- **options 必须 3 个**：不足则 `failed + error_code=...`（不建议静默补齐）
- **映射键**：不要用 title 作为唯一 key；优先使用 `scene_id` 或输入摘要 id。
- **顺序/数量校验**：major/micro 数量必须符合配置。

### 失败处理（不吞错）
- 失败必须结构化输出 `status/error_code`，禁止 `{payload:{}}` 假成功。

---

## 6. 热路径治理：确保训练主链路不被脚本阻塞

### 目标
- 训练恢复/刷新/并发访问时，脚本能力不会放大外部依赖（LLM）压力。

### 最小落地
- Phase A：POST ensure 触发后台任务；GET 只读。
- 无后台队列时：也至少把 LLM 调用从 GET 移出到 POST，并加超时/并发保护。

---

## 7. 可观测性（Telemetry/Logs/Trace）

### 后端日志（结构化字段）
- `session_id`, `script_id`, `status`, `error_code`, `fallback_used`, `provider`, `model`, `source_script_id`

### 前端（若消费该能力）
- 只按 `status/error_code` 决策 UI；不要解析 message 文本。

---

## 8. 测试清单（必须补齐）

### 后端单测/集成
- **并发幂等**：同 `session_id` 并发 ensure → 只生成/写入一次，其余返回 running。
- **缺表/存储不可用**：返回 503 + `TRAINING_STORY_SCRIPT_STORAGE_UNAVAILABLE`（禁止 200 + 空 payload）。
- **LLM 非法输出**：invalid JSON/空输出 → `failed + error_code`，可 fallback 时 `ready + fallback_used=true`。
- **mapper 强契约**：options 不足 3 个 → `failed + error_code`。

### 前端（如接入）
- `ready/pending/failed` 的 UI 空态与重试按钮逻辑（按 error_code，而非 message）。

---

## 9. 推荐迁移步骤（最小改动，最大收益）

1. **Phase A**
   - 在 story script 响应中新增 `status/error_code`（optional）。
   - 新增 `POST ensure`，并加入 DB 级并发保护（running 占位）。
2. **Phase B**
   - 打开开关：GET 彻底只读，不再触发 ensure/LLM/写库。
3. **复用兜底**
   - 分桶过滤 + 去画像 + 溯源（不改“池化复用”逻辑，只加安全带）。
4. **mapper 强契约**
   - 失败显性化（status/error_code），阻止坏脚本进入训练主流程。

---

## 10. 交付物清单（建议）
- `api/routers/training.py`：新增 `POST /story-scripts/{session_id}/ensure`（或新 router 也可）
- `api/services/training_story_script_service.py`：读写分离 + 状态机推进 + 幂等控制
- `training/story_script_agent.py`：保持核心生成/复用逻辑；补 meta（version/bucket/trace）
- `training/training_store.py` + repo：支持 status/error_code 更新与查询
- 测试：并发、缺表、LLM 非法输出、mapper 强契约

