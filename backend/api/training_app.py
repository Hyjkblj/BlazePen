"""Training-engine-only FastAPI entrypoint.

This app intentionally mounts only training-domain routers.
"""

from __future__ import annotations

import os

import uvicorn

from api.app_factory import create_api_app
from api.dependencies import warmup_training_media_task_executor
from api.routers import training, training_media
from utils.logger import setup_logger

logger = setup_logger(__name__)


app = create_api_app(
    title="BlazePen Training Engine API",
    description="Standalone backend service exposing training-engine endpoints only.",
    version="1.0.0",
    service_scope="training",
    logger=logger,
    database_label="training engine database",
    health_message="training engine service is running",
    root_message="BlazePen Training Engine API",
    root_extra={"entrypoint_kind": "training_only"},
)

app.include_router(training.router, prefix="/api")
app.include_router(training_media.router, prefix="/api")


async def warmup_training_media_runtime() -> None:
    """Warm up training media executor outside request hot paths."""

    try:
        result = warmup_training_media_task_executor()
        logger.info(
            "training media executor warmup completed: recovered=%s timed_out=%s",
            result.get("recovered", 0),
            result.get("timed_out", 0),
        )
    except Exception as exc:
        logger.error("training media executor warmup failed: %s", str(exc), exc_info=True)


app.add_event_handler("startup", warmup_training_media_runtime)


if __name__ == "__main__":
    api_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(api_dir)
    os.chdir(backend_dir)
    logger.info("training engine service working directory: %s", os.getcwd())

    uvicorn.run(
        "api.training_app:app",
        host=os.getenv("TRAINING_API_HOST", "0.0.0.0"),
        port=int(os.getenv("TRAINING_API_PORT", "8010")),
        reload=os.getenv("TRAINING_API_RELOAD", "true").lower() == "true",
    )
