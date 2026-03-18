"""启动训练引擎专用 FastAPI 服务。"""

from __future__ import annotations

import os

import uvicorn


if __name__ == "__main__":
    # 保证训练专用启动脚本总是在 backend 根目录下运行。
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"训练引擎服务工作目录: {os.getcwd()}")

    uvicorn.run(
        "api.training_app:app",
        host=os.getenv("TRAINING_API_HOST", "0.0.0.0"),
        port=int(os.getenv("TRAINING_API_PORT", "8010")),
        reload=os.getenv("TRAINING_API_RELOAD", "true").lower() == "true",
    )
