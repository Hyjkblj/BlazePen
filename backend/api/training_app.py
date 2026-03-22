"""训练引擎专用 FastAPI 应用入口。

说明：
1. 这个入口只挂载训练路由，用于本地或独立部署时只运行训练引擎服务。
2. 它不会注册角色、旧剧情流、TTS、向量库管理等其它业务路由。
3. 启动时只做数据库连通性检查，不自动补表。
"""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.app_runtime import install_trace_context_middleware
from api.cors_config import build_cors_middleware_options
from api.middleware.error_handler import install_common_exception_handlers
from api.routers import training
from database.db_manager import DatabaseManager
from utils.logger import setup_logger

logger = setup_logger(__name__)


app = FastAPI(
    title="烽火笔锋训练引擎 API",
    description="仅包含训练引擎相关接口的独立后端服务",
    version="1.0.0",
)

# 训练专用应用也复用统一异常处理，保证独立部署后返回形态不漂移。
install_common_exception_handlers(app)
install_trace_context_middleware(app)


@app.on_event("startup")
async def startup_event():
    """应用启动时检查数据库连接。

    这里故意只做连通性检查，不在启动阶段自动做 schema 变更。
    """
    try:
        logger.info("正在检查训练引擎数据库连接...")
        db_manager = DatabaseManager()
        db_manager.check_connection()
        logger.info("训练引擎数据库连接检查通过")
    except Exception as exc:
        # 独立训练服务也保留“记录错误但不阻断启动”的策略，方便本地先看接口和日志。
        logger.error("训练引擎数据库连接检查失败: %s", str(exc), exc_info=True)


app.add_middleware(
    CORSMiddleware,
    **build_cors_middleware_options(service_scope="training"),
)

# 这里只注册训练路由，确保服务边界清晰。
app.include_router(training.router, prefix="/api")


@app.get("/health")
async def check_server_health():
    """训练引擎健康检查。"""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "message": "训练引擎服务正常运行"},
    )


@app.get("/")
async def root():
    """训练引擎根路由。"""
    return {
        "message": "烽火笔锋训练引擎 API",
        "version": "1.0.0",
        "docs": "/docs",
        "service_scope": "training_only",
    }


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
