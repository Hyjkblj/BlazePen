"""Training-engine-only FastAPI entrypoint.

This app intentionally mounts only training-domain routers.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os

import uvicorn
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from uuid import uuid4

from api.app_factory import create_api_app
from api.dependencies import (
    warmup_training_character_preview_job_service,
    warmup_training_media_task_executor,
    get_training_media_task_executor,
    get_training_story_script_executor,
    get_story_image_executor,
)
from api.routers import training, training_characters, training_media, tts
import config
from training.exceptions import TrainingStorageUnavailableError
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
    root_message="烽火笔锋训练引擎 API",
    root_extra={"entrypoint_kind": "training_only"},
)

# Configure static assets for media/model outputs (same contract as story app).
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    if os.path.isabs(config.IMAGE_SAVE_DIR):
        character_images_dir = config.IMAGE_SAVE_DIR
    else:
        character_images_dir = os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
    os.makedirs(character_images_dir, exist_ok=True)
    app.mount(
        "/static/images/characters",
        StaticFiles(directory=character_images_dir),
        name="training_character_images",
    )
except Exception as exc:
    logger.warning("training app character static mount failed: %s", str(exc))

try:
    if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
        scene_images_dir = config.SCENE_IMAGE_SAVE_DIR
    else:
        scene_images_dir = os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
    os.makedirs(scene_images_dir, exist_ok=True)
    app.mount(
        "/static/images/scenes",
        StaticFiles(directory=scene_images_dir),
        name="training_scene_images",
    )
except Exception as exc:
    logger.warning("training app scene static mount failed: %s", str(exc))

try:
    if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
        small_scene_images_dir = config.SMALL_SCENE_IMAGE_SAVE_DIR
    else:
        small_scene_images_dir = os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR)
    os.makedirs(small_scene_images_dir, exist_ok=True)
    app.mount(
        "/static/images/smallscenes",
        StaticFiles(directory=small_scene_images_dir),
        name="training_small_scene_images",
    )
except Exception as exc:
    logger.warning("training app small-scene static mount failed: %s", str(exc))

try:
    if os.path.isabs(config.COMPOSITE_IMAGE_SAVE_DIR):
        composite_images_dir = config.COMPOSITE_IMAGE_SAVE_DIR
    else:
        composite_images_dir = os.path.join(backend_dir, config.COMPOSITE_IMAGE_SAVE_DIR)
    os.makedirs(composite_images_dir, exist_ok=True)
    app.mount(
        "/static/images/composite",
        StaticFiles(directory=composite_images_dir),
        name="training_composite_images",
    )
except Exception as exc:
    logger.warning("training app composite static mount failed: %s", str(exc))

try:
    audio_cache_dir = os.path.join(backend_dir, "audio", "cache")
    os.makedirs(audio_cache_dir, exist_ok=True)
    app.mount(
        "/static/audio/cache",
        StaticFiles(directory=audio_cache_dir),
        name="training_audio_cache",
    )
except Exception as exc:
    logger.warning("training app audio cache static mount failed: %s", str(exc))

app.include_router(training.router, prefix="/api")
app.include_router(training_media.router, prefix="/api")
app.include_router(training_characters.router, prefix="/api")
app.include_router(tts.router, prefix="/api")

_TRAINING_MEDIA_RUNTIME_STATE_KEY = "training_media_runtime_state"


def _new_training_media_runtime_state() -> dict:
    return {
        "ready": False,
        "degraded": False,
        "updated_at": None,
        "components": {
            "preview_warmup": {
                "status": "pending",
                "recovered": 0,
                "timed_out": 0,
                "error": None,
            },
            "media_warmup": {
                "status": "pending",
                "recovered": 0,
                "timed_out": 0,
                "error": None,
            },
        },
    }


app.state.training_media_runtime_state = _new_training_media_runtime_state()


@app.on_event("shutdown")
async def _shutdown_executors() -> None:
    try:
        executor = get_training_media_task_executor()
        if executor is not None and hasattr(executor, "shutdown"):
            executor.shutdown()
    except Exception as exc:
        logger.warning("failed to shutdown training media executor: %s", str(exc))

    try:
        story_script_executor = get_training_story_script_executor()
        if story_script_executor is not None and hasattr(story_script_executor, "shutdown"):
            story_script_executor.shutdown()
    except Exception as exc:
        logger.warning("failed to shutdown training story-script executor: %s", str(exc))

    try:
        story_image_executor = get_story_image_executor()
        if story_image_executor is not None and hasattr(story_image_executor, "shutdown"):
            story_image_executor.shutdown(wait=False, cancel_futures=True)  # type: ignore[arg-type]
    except Exception as exc:
        logger.warning("failed to shutdown story image executor: %s", str(exc))

def _single_line(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def _build_runtime_error(exc: Exception, *, component: str) -> dict:
    debug_enabled = str(os.getenv("TRAINING_READINESS_DEBUG", "")).strip().lower() in {"1", "true", "yes", "on"}
    error_type = type(exc).__name__
    message = _single_line(str(exc) or error_type or "unknown error")

    error_code = "TRAINING_WARMUP_FAILED"
    if component == "media_warmup":
        error_code = "TRAINING_MEDIA_WARMUP_FAILED"
    if component == "preview_warmup":
        error_code = "TRAINING_PREVIEW_WARMUP_FAILED"

    payload = {
        "error_code": error_code,
        "error_type": error_type,
        "message": message,
        "retryable": False,
    }
    if debug_enabled:
        payload["debug_id"] = uuid4().hex
    return payload


async def warmup_training_media_runtime() -> None:
    """Warm up training media executor outside request hot paths."""
    runtime_state = _new_training_media_runtime_state()

    try:
        preview_result = warmup_training_character_preview_job_service()
        runtime_state["components"]["preview_warmup"] = {
            "status": "ready",
            "recovered": int(preview_result.get("recovered", 0) or 0),
            "timed_out": int(preview_result.get("timed_out", 0) or 0),
            "error": None,
        }
        logger.info(
            "training preview executor warmup completed: recovered=%s timed_out=%s",
            preview_result.get("recovered", 0),
            preview_result.get("timed_out", 0),
        )
    except TrainingStorageUnavailableError as exc:
        runtime_state["degraded"] = True
        runtime_state["components"]["preview_warmup"] = {
            "status": "degraded",
            "recovered": 0,
            "timed_out": 0,
            "error": _build_runtime_error(exc, component="preview_warmup"),
        }
        logger.warning(
            "training preview executor warmup degraded: %s",
            str(exc),
            exc_info=True,
        )
    except Exception as exc:
        runtime_state["degraded"] = True
        runtime_state["components"]["preview_warmup"] = {
            "status": "degraded",
            "recovered": 0,
            "timed_out": 0,
            "error": _build_runtime_error(exc, component="preview_warmup"),
        }
        logger.warning(
            "training preview executor warmup degraded: %s",
            str(exc),
            exc_info=True,
        )

    try:
        result = warmup_training_media_task_executor()
        runtime_state["components"]["media_warmup"] = {
            "status": "ready",
            "recovered": int(result.get("recovered", 0) or 0),
            "timed_out": int(result.get("timed_out", 0) or 0),
            "error": None,
        }
        logger.info(
            "training media executor warmup completed: recovered=%s timed_out=%s",
            result.get("recovered", 0),
            result.get("timed_out", 0),
        )
    except TrainingStorageUnavailableError as exc:
        runtime_state["degraded"] = True
        runtime_state["components"]["media_warmup"] = {
            "status": "degraded",
            "recovered": 0,
            "timed_out": 0,
            "error": _build_runtime_error(exc, component="media_warmup"),
        }
        logger.warning(
            "training media executor warmup degraded: %s",
            str(exc),
            exc_info=True,
        )
    except Exception as exc:
        runtime_state["degraded"] = True
        runtime_state["components"]["media_warmup"] = {
            "status": "degraded",
            "recovered": 0,
            "timed_out": 0,
            "error": _build_runtime_error(exc, component="media_warmup"),
        }
        logger.warning(
            "training media executor warmup degraded: %s",
            str(exc),
            exc_info=True,
        )

    runtime_state["ready"] = True
    runtime_state["updated_at"] = datetime.now(timezone.utc).isoformat()
    app.state.training_media_runtime_state = runtime_state

    if runtime_state["degraded"]:
        logger.warning("training app started in media-degraded mode")


@app.get("/readiness")
async def training_readiness():
    runtime_state = getattr(app.state, _TRAINING_MEDIA_RUNTIME_STATE_KEY, None)
    if not isinstance(runtime_state, dict):
        runtime_state = _new_training_media_runtime_state()
    http_status = status.HTTP_200_OK if runtime_state.get("ready") else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ready" if runtime_state.get("ready") else "starting",
            "media_runtime": runtime_state,
        },
    )


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
