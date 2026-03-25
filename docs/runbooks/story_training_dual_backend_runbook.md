# Story / Training 双后端联调与排障 Runbook

更新时间：`2026-03-24`

## 1. 目标与边界
- Story backend 只负责 story 域，默认端口 `8000`。
- Training backend 只负责 training 域，默认端口 `8010`。
- `threadId` 仅属于 story 会话。
- `sessionId` 仅属于 training 会话。
- 双后端共享基础中间件能力，但不共享会话状态机事实源。

## 2. 本地启动

### 2.1 启动 story backend
```powershell
cd backend
python run_story_api.py
```

### 2.2 启动 training backend
```powershell
cd backend
python run_training_api.py
```

### 2.3 训练一键体验（含 smoke）
```powershell
cd backend
python run_training_cli.py experience
```

### 2.4 Story smoke（统一 CLI 入口）
```powershell
cd backend
python run_story_cli.py smoke
```

### 2.5 可选：PowerShell 脚本入口
```powershell
cd backend
.\start_story_backend.ps1
.\start_story_smoke.ps1
.\start_training_backend.ps1
.\start_training_experience.ps1
```

### 2.6 启动 story frontend
```powershell
cd frontend
npm run dev:story
```

### 2.7 启动 training frontend
```powershell
cd frontend
npm run dev:training
```

### 2.8 双前端并行启动（可选）
```powershell
cd frontend
npm run dev:all
```

### 2.9 Training frontend HMR 快速排障（`ERR_CONNECTION_REFUSED`）
```powershell
# 1) 检查 3001 端口占用（应只保留一个 vite 进程）
Get-NetTCPConnection -LocalPort 3001 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess

# 2) 结束占用 3001 的残留 node 进程（按上一步 PID 替换）
Stop-Process -Id <PID> -Force

# 3) 重新启动训练前端（默认 localhost:3001）
cd frontend
npm run dev:training
```

说明：
- 当浏览器访问 `localhost:3001`，但 dev server 绑定在 `127.0.0.1`（或反过来）且存在残留进程时，HMR WebSocket 可能失败。
- 当前默认配置已统一为 `localhost`；如需覆盖可设置 `VITE_DEV_HOST` / `VITE_HMR_HOST`。

## 3. CORS 单一事实源
统一由 `backend/api/cors_config.py` 管理：
- 公共 allowlist：`ALLOWED_ORIGINS`
- story allowlist：`STORY_ALLOWED_ORIGINS`
- training allowlist：`TRAINING_ALLOWED_ORIGINS`

生产环境必须满足以下之一：
1. 配置 `ALLOWED_ORIGINS`
2. 同时配置 `STORY_ALLOWED_ORIGINS` + `TRAINING_ALLOWED_ORIGINS`

`backend/config_manager.py` 和 `backend/utils/config_validator.py` 已与该规则对齐。

## 4. 健康检查与边界检查

### 4.1 健康检查
```bash
curl http://localhost:8000/health
curl http://localhost:8010/health
```

### 4.2 路由边界检查
```bash
# story backend 不应暴露 training 路由
curl -X POST "http://localhost:8000/api/v1/training/init" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"u1\",\"training_mode\":\"guided\"}"

# training backend 不应暴露 story 路由
curl "http://localhost:8010/api/v1/game/sessions?user_id=u1"
```

预期均为 `404`。

### 4.3 CORS 预检检查
```bash
# story preflight（预期 200 且返回 access-control-allow-origin）
curl -i -X OPTIONS "http://localhost:8000/health" \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: X-Trace-Id,Content-Type"

# training preflight（预期 200 且返回 access-control-allow-origin）
curl -i -X OPTIONS "http://localhost:8010/health" \
  -H "Origin: http://localhost:3001" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: X-Trace-Id,Content-Type"
```

## 5. 最小回归命令（上线前建议）
### 5.1 backend 最小回归
```powershell
python -m pytest backend/test_domain_import_boundaries.py `
  backend/test_story_training_import_boundaries.py `
  backend/test_api_domain_boundaries.py `
  backend/test_runner_import_boundaries.py `
  backend/test_story_router_facade_boundaries.py `
  backend/test_game_service_facade_surface.py `
  backend/test_api_app_factory_metadata.py `
  backend/test_api_dependencies.py `
  backend/test_story_service_bundle.py `
  backend/test_api_cors_scope_prod.py `
  backend/test_story_api_entry.py `
  backend/test_training_api_entry.py `
  backend/test_training_runner_bootstrap.py `
  backend/test_story_cli_entry.py `
  backend/test_story_standalone_app.py `
  backend/test_training_standalone_app.py `
  backend/test_api_entrypoint_boundaries.py `
  backend/test_api_entry_common_middleware.py `
  backend/test_api_cors_config.py `
  backend/test_config_manager_cors_alignment.py `
  backend/test_config_validator_cors.py `
  backend/test_story_route_smoke.py `
  backend/test_training_query_service.py `
  backend/test_training_route_smoke.py -q
```

### 5.2 frontend 最小回归
```powershell
cd frontend
npm run test:smoke:training:all
```

若需要把 story + training 一并回归，可直接运行：
```powershell
cd frontend
npm run test:smoke:all
```

### 5.3 CI 准入门槛
- backend 边界与 smoke：`.github/workflows/backend-boundary-smoke.yml`
- frontend smoke：`.github/workflows/frontend-smoke.yml`

建议保持“本地先过 5.1/5.2，再发 PR”。

### 5.4 legacy 字段清退守卫
训练前端已不再消费 legacy `briefing` 字段，新增静态边界测试：
```powershell
cd frontend
npm exec vitest run src/test/trainingLegacyBriefingBoundary.test.ts
```
训练后端已收口为 canonical `brief` 输出：legacy `briefing` 输入不会再回填到 DTO，也不会出现在冻结场景快照与对外响应中。

### 5.5 报告查询性能护栏（常量级 I/O）
```powershell
python -m pytest backend/test_training_query_service.py `
  -k "constant_store_read_calls_without_write_side_effects" -q
```
该用例用于守卫 `training report` 查询路径的 store 调用次数保持常量级，避免回归到逐回合额外查询或写路径泄漏。

## 6. 常见故障定位
- 跨域失败：优先检查 `ENV` 与三组 CORS 环境变量是否符合第 3 节规则。
- 打错端口：确认 story 前端走 `8000`，training 前端走 `8010`。
- 会话恢复错域：确认 story 只传 `threadId`，training 只传 `sessionId`。
- trace 丢失：检查响应头是否返回 `X-Trace-Id`，便于端到端排障。

## 7. PR-TRN-07 CI Baseline (2026-03-24)
- Frontend workflow `.github/workflows/frontend-smoke.yml` runs:
  - `npm run test:smoke:all`
  - `npm run test:training:route-integration`
- `npm run test:smoke:training:all` now includes:
  - `npm run test:boundary:training:legacy-briefing`
