"""训练引擎专用 FastAPI 应用入口。

说明：
1. 这个入口只挂载训练路由，用于本地或独立部署时只运行训练引擎服务。
2. 它不会注册角色、旧剧情流、TTS、向量库管理等其它业务路由。
3. 启动时只做数据库连通性检查，不自动补表。
"""

from __future__ import annotations

import os

import uvicorn

from api.app_factory import create_api_app
from api.routers import training
from utils.logger import setup_logger

logger = setup_logger(__name__)


app = create_api_app(
    title="烽火笔锋训练引擎 API",
    description="仅包含训练引擎相关接口的独立后端服务",
    version="1.0.0",
    service_scope="training",
    logger=logger,
    database_label="训练引擎数据库",
    health_message="训练引擎服务正常运行",
    root_message="烽火笔锋训练引擎 API",
    root_extra={"entrypoint_kind": "training_only"},
)

# 这里只注册训练路由，确保服务边界清晰。
app.include_router(training.router, prefix="/api")


if __name__ == "__main__":
    # 直接运行文件时，把工作目录切到 backend 根目录，保证相对路径一致。
    api_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(api_dir)
    os.chdir(backend_dir)
    logger.info("训练引擎服务工作目录: %s", os.getcwd())

    uvicorn.run(
        "api.training_app:app",
        host=os.getenv("TRAINING_API_HOST", "0.0.0.0"),
        port=int(os.getenv("TRAINING_API_PORT", "8010")),
        reload=os.getenv("TRAINING_API_RELOAD", "true").lower() == "true",
    )
