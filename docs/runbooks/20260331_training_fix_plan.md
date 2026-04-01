# Training 修复与优化方案（前后端不冲突版）

更新日期：2026-03-31  
适用范围：BlazePen training 域（训练入口、训练会话/恢复、场景图与媒体任务、storyline、story script）

---

## 目标与约束

### 目标
- **关闭“后端生成场景图但前端拿不到”**的故障面，并将其从“环境偶发”变为“契约可控、可观测、可回归测试”。
- **保证训练会话可恢复且一致**：同一个 `sessionId` 在刷新/重启/恢复下，storyline 与关键序列不漂移。
- **把重任务从同步热路径移出**：LLM 生成与脚本 ensure 不得阻塞训练读接口。

### 约束（前后端不冲突）
- **先扩展契约、后收敛旧行为**：后端先“加字段/加接口”兼容旧前端；前端按“字段存在才启用增强逻辑”消费。
- **新语义必须结构化**（`status/error_code/idempotency_key/...`），禁止前端依赖 message 文本判断业务语义。
- **破坏性语义变更必须有开关/灰度**（env/flag），避免一次性断链。

---

## 一、静态资源可达性（/static）——关闭“场景图拿不到”

### 问题现象
- 后端日志显示场景图已生成并保存到 `images/smallscenes/`。
- 前端 `sceneImageUrl` 为相对路径（如 `/static/images/smallscenes/...jpg`），但浏览器请求落到错误 origin，导致 404。

### 契约设计（不冲突）
- **后端保持返回形态不变**：仍返回相对 `/static/...` 或绝对 `https://...`。
- **前端增强 `getStaticAssetUrl()`**：当设置 `VITE_STATIC_ASSET_ORIGIN` 且路径以 `/static/` 开头时，拼接为 `${origin}/static/...`；否则保持同源行为（向后兼容）。

### 推荐落地方案
#### 方案 A（推荐，最少侵入）
- **统一要求 training 入口在“非同源形态”配置 `VITE_STATIC_ASSET_ORIGIN`**。
- 在 training 入口增加一次性校验/提示（仅告警不阻断）：
  - 若检测到训练资产为 `/static/...` 且 `VITE_STATIC_ASSET_ORIGIN` 为空、且当前运行入口无法保证 `/static` 代理，则 UI 提示“静态资源 origin 未配置，场景图可能不可用”，并打 telemetry。

#### 方案 B（工程化更强）
- 确保所有 training 入口运行形态（dev/preview/electron）都具备 `/static -> training backend` 代理。

### 回归测试（必须）
- `frontend/src/services/assetUrl.test.ts`
  - `VITE_STATIC_ASSET_ORIGIN` 为空：`/static/...` 不拼接
  - 有值：`/static/...` 拼接为 `${origin}/static/...`
  - 非 `/static` 的绝对路径不拼接
- training smoke/集成：至少断言 `sceneImageUrl` 经过 `getStaticAssetUrl()` 后可形成可请求 URL（不要求真的拉图，但要验证拼接行为）。

---

## 二、409 冲突恢复避免串图（training media task）

### 现状
- 前端在 `TRAINING_MEDIA_TASK_CONFLICT (409)` 时从 `error.details` 读取既存 `taskId` 并继续 poll。
- 风险：若 conflict 的 task 不属于当前 `sessionId/scenarioId/attempt`，可能导致 **串图/错图**。

### 契约扩展（后端先做，不破旧）
后端在 409 `details` 中新增（**optional**）字段：
- `task_id`（已有或保持）
- `idempotency_key`（新增，强推荐）
- `session_id`（新增，推荐）
- `round_no`（新增，可选）

### 前端兼容消费（字段存在才启用增强）
前端逻辑：
- 若仅有 `task_id`：沿用旧行为（不破旧后端）。
- 若同时有 `idempotency_key/session_id/round_no`：校验不一致则 **进入新 attempt**（`attemptNo+1`），避免串图。

### 测试缺口
- 前端：补一个用例覆盖“冲突返回 taskId 但身份不匹配时不会写回旧图”。
- 后端：补一条契约测试确保 conflict details 包含新增字段（在开启增强模式时）。

---

## 三、storyline seed：单一事实源 + 可恢复一致（阻塞级）

### 问题
- seed 默认引入随机源（如 `uuid4()`），若未持久化为会话事实源，会导致同 `sessionId` 恢复后 storyline 漂移。

### 最佳修复（后端自洽，前端不强依赖）
1. **seed 作为服务端单一事实源**（推荐专用字段；次选放 `training_sessions.session_meta.storyline_seed`）。
2. **首次 init**：
   - 若请求显式提供 `script_seed/storyline_seed`：直接持久化。
   - 否则生成 seed 并持久化（推荐基于 `session_id` 的确定性 derivation，或生成后立即写入）。
3. **恢复/扩展**：只读 seed，不得再引入随机源。

### 回归测试（必须）
- 同一 `sessionId` 多次恢复/扩展：`storyline_id` 与序列完全一致。
- seed 缺失时：init 会回填 seed，后续恢复仍一致。

---

## 四、story script：从 GET 热路径迁出（阻塞级）

### 问题
- `GET /v1/training/story-scripts/{session_id}` 内部可能触发 ensure（LLM + 校验 + 写库），并在失败时吞错返回空 payload。
- 这是 **读写边界破坏 + 同步热路径重任务 + 假成功** 的组合风险。

### 不冲突的分阶段落地（强推荐）

#### Phase A：先扩展契约（兼容旧前端）
后端：
- 保留现有 GET 行为（暂不破旧）。
- 在返回 DTO 中新增（optional）：
  - `status`: `ready | pending | failed`（或 `missing`）
  - `error_code`: string | null
- 新增 `POST /v1/training/story-scripts/{session_id}/ensure`（幂等触发生成）。

前端：
- 若 `status` 不存在：按旧逻辑消费 `payload`。
- 若 `status` 存在：按 `ready/pending/failed` 渲染与重试策略（必要时调用 POST ensure）。

#### Phase B：收敛旧语义（开启开关灰度）
后端：
- 打开开关：GET **不再触发 ensure/LLM/写库**，只读状态与结果。
- 生成必须走 POST/后台任务。

### 失败策略（必须结构化）
- 缺表/存储不可用：返回 503 + 稳定错误码（不要空 payload）。
- LLM 解析失败：返回 `status=failed` + `error_code`，可选 `debug_id`，禁止用 message 承载分支语义。

### 回归测试（必须）
- 并发 ensure：同 `sessionId` 并发触发只生成/写入一次（幂等/锁）。
- 缺表：返回 503 + 错误码（禁止“200 + 空 payload”）。
- status 模型：GET 在 pending/failed/ready 下返回稳定结构。

---

## 五、禁止从真实 session 抽样克隆脚本（改模板库）

### 问题
- 从其他 session 抽样并克隆到当前 session 属于跨会话数据复用，破坏会话隔离与事实源边界。

### 最佳替代
- 建立独立模板库（脱敏 + 版本化 + 分桶）：
  - `script_version`
  - `training_mode`
  - `scenario_bank_version`
- 训练 session 只引用模板 id 或拷贝模板（可溯源），禁止从真实用户 session 抽样。

---

## 落地顺序（按风险/收益比）
1. **后端：storyline seed 持久化/确定性派生**（一致性阻塞）
2. **后端：story script Phase A（status 字段 + ensure POST）**（热路径阻塞）
3. **后端：story script Phase B（GET 只读）**（开关灰度）
4. **前端：静态资源契约固化（入口校验 + 单测）**
5. **前后端：409 冲突恢复字段扩展 + 前端校验避免串图**
6. **后端：移除 session pool 克隆，替换模板库**

---

## 上线前检查清单
- 后端：
  - migration 已执行（story scripts 表存在）
  - GET story-scripts 在开关关闭/开启两种模式下均返回稳定结构
  - seed 已持久化并在恢复中只读
- 前端：
  - `assetUrl` 单测通过
  - training 入口对 origin/proxy 缺失有可观测告警
  - 关键训练页面无资源 404（至少 smoke）

