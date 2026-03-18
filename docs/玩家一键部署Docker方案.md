# No End Story 玩家一键部署（Docker 方案）

本方案用于“玩家无需手动安装 PostgreSQL”场景。
玩家只需要安装并启动 Docker Desktop，然后执行一键脚本即可。

## 1. 你需要先准备（发行方）

1. 构建并推送后端镜像（基于 `backend/Dockerfile`）。
2. 将镜像地址写入 `deploy/player.env.example` 的 `BACKEND_IMAGE`。
3. 打包桌面端时，将 `deploy/` 与 `scripts/` 一起放入安装包资源目录。

示例（发行方本机）：

```powershell
docker build -t ghcr.io/no-end-story/no-end-story-backend:latest ./backend
docker push ghcr.io/no-end-story/no-end-story-backend:latest
```

## 2. 玩家如何一键启动

首次运行（Windows）：

```powershell
scripts\start_stack.ps1
```

或直接双击：

```text
scripts\start_stack.bat
```

脚本会自动完成：

1. 检查 Docker 环境
2. 首次生成 `deploy/player.env`
3. 自动生成 PostgreSQL 密码（若为空）
4. 拉取并启动 `postgres + backend` 容器
5. 轮询 `http://127.0.0.1:8000/health`，直到服务可用

## 3. 停止与重置

停止服务：

```powershell
scripts\stop_stack.ps1
```

重置数据（删除数据库和向量库卷）：

```powershell
scripts\reset_stack.ps1
```

## 4. 配置文件说明

玩家首次启动后会得到 `deploy/player.env`，可按需编辑：

1. `BACKEND_IMAGE`：后端镜像地址（必须可拉取）
2. `BACKEND_PORT`：后端端口（默认 8000）
3. `POSTGRES_PASSWORD`：数据库密码（首次自动生成）
4. `VOLCENGINE_*`、`DASHSCOPE_*`、`OPENAI_API_KEY`：模型服务密钥
5. `EMBEDDING_MODEL`：建议玩家版设为 `default`（构建更轻、更稳）

## 5. 故障排查

1. 启动失败且提示 `docker` 不存在：
   先安装 Docker Desktop 并确保已启动。
2. 拉镜像失败：
   检查 `BACKEND_IMAGE` 是否正确、仓库是否需要登录。
3. 8000 端口被占用：
   修改 `BACKEND_PORT` 为其他端口，并同步前端请求地址。
4. 数据库异常：
   执行 `scripts/reset_stack.ps1` 后重新启动。
