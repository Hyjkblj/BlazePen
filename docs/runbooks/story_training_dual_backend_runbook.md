# Story / Training 双后端联调与排障 Runbook

更新时间：`2026-03-22`

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

### 2.5 鍙€夛細PowerShell 脚本入口
```powershell
cd backend
.\start_story_backend.ps1
.\start_story_smoke.ps1
.\start_training_backend.ps1
.\start_training_experience.ps1
```

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
```powershell
python -m pytest backend/test_domain_import_boundaries.py `
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
  backend/test_training_route_smoke.py -q
```

## 6. 常见故障定位
- 跨域失败：优先检查 `ENV` 与三组 CORS 环境变量是否符合第 3 节规则。
- 打错端口：确认 story 前端走 `8000`，training 前端走 `8010`。
- 会话恢复错域：确认 story 只传 `threadId`，training 只传 `sessionId`。
- trace 丢失：检查响应头是否返回 `X-Trace-Id`，便于端到端排障。
