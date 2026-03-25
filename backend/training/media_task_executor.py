"""Training media task async executor and provider dispatcher."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from threading import Lock
from time import sleep
from typing import Any

from api.services.image_service import ImageService
from api.services.tts_service import TTSService
from models.text_model_service import TextModelService
from training.exceptions import (
    TrainingMediaProviderUnavailableError,
    TrainingMediaTaskExecutionFailedError,
    TrainingMediaTaskTimeoutError,
)
from training.training_store import DatabaseTrainingStore, TrainingMediaTaskRecord, TrainingStoreProtocol
from utils.logger import get_logger


logger = get_logger(__name__)


@dataclass(slots=True)
class TrainingMediaTaskExecutorConfig:
    """Runtime config for media task async execution."""

    max_workers: int = 2
    retry_backoff_seconds: float = 0.2
    task_timeout_seconds: float = 30.0
    recovery_timeout_seconds: float = 300.0

    @classmethod
    def from_environment(cls) -> "TrainingMediaTaskExecutorConfig":
        return cls(
            max_workers=max(1, int(os.getenv("TRAINING_MEDIA_EXECUTOR_MAX_WORKERS", "2"))),
            retry_backoff_seconds=max(
                0.0,
                float(os.getenv("TRAINING_MEDIA_RETRY_BACKOFF_SECONDS", "0.2")),
            ),
            task_timeout_seconds=max(
                1.0,
                float(os.getenv("TRAINING_MEDIA_TASK_TIMEOUT_SECONDS", "30")),
            ),
            recovery_timeout_seconds=max(
                1.0,
                float(os.getenv("TRAINING_MEDIA_RECOVERY_TIMEOUT_SECONDS", "300")),
            ),
        )


class TrainingMediaTaskProviderDispatcher:
    """Provider adapter layer dispatching task_type to concrete media services."""

    def __init__(
        self,
        *,
        image_service: ImageService | None = None,
        tts_service: TTSService | None = None,
        text_model_service: TextModelService | None = None,
    ):
        self.image_service = image_service
        self.tts_service = tts_service
        self.text_model_service = text_model_service

    def execute_task(self, *, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized_task_type = str(task_type or "").strip().lower()
        normalized_payload = dict(payload or {})

        if normalized_task_type == "image":
            return self._execute_image_task(normalized_payload)
        if normalized_task_type == "tts":
            return self._execute_tts_task(normalized_payload)
        if normalized_task_type == "text":
            return self._execute_text_task(normalized_payload)

        raise TrainingMediaTaskExecutionFailedError(
            task_type=normalized_task_type,
            reason="unsupported task type in provider dispatcher",
        )

    def _execute_image_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.image_service is None:
            raise TrainingMediaProviderUnavailableError(task_type="image", provider="ImageService")

        prompt = str(payload.get("prompt") or "").strip()
        if not prompt:
            raise TrainingMediaTaskExecutionFailedError(
                task_type="image",
                reason="payload.prompt is required",
            )

        character_id = self._optional_int(payload.get("character_id"))
        user_id = self._optional_str(payload.get("user_id"))
        image_type = self._optional_str(payload.get("image_type")) or "portrait"
        generate_group = bool(payload.get("generate_group", True))
        group_count = max(1, int(payload.get("group_count", 3) or 3))

        image_urls = self.image_service.generate_character_image(
            prompt=prompt,
            character_id=character_id,
            user_id=user_id,
            image_type=image_type,
            generate_group=generate_group,
            group_count=group_count,
        )
        if not image_urls:
            raise TrainingMediaTaskExecutionFailedError(
                task_type="image",
                reason="image provider returned empty result",
            )
        return {"image_urls": list(image_urls)}

    def _execute_tts_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.tts_service is None:
            raise TrainingMediaProviderUnavailableError(task_type="tts", provider="TTSService")

        text = str(payload.get("text") or "").strip()
        if not text:
            raise TrainingMediaTaskExecutionFailedError(
                task_type="tts",
                reason="payload.text is required",
            )

        character_id = self._optional_int(payload.get("character_id")) or 1
        emotion_params = payload.get("emotion_params")
        if emotion_params is not None and not isinstance(emotion_params, dict):
            raise TrainingMediaTaskExecutionFailedError(
                task_type="tts",
                reason="payload.emotion_params must be an object",
            )

        result = self.tts_service.generate_speech(
            text=text,
            character_id=character_id,
            emotion_params=emotion_params,
            use_cache=bool(payload.get("use_cache", True)),
            override_voice_id=self._optional_str(payload.get("voice_id")),
        )
        if not isinstance(result, dict):
            raise TrainingMediaTaskExecutionFailedError(
                task_type="tts",
                reason="tts provider returned invalid result",
            )
        return dict(result)

    def _execute_text_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.text_model_service is None:
            raise TrainingMediaProviderUnavailableError(task_type="text", provider="TextModelService")

        prompt = str(payload.get("prompt") or "").strip()
        if not prompt:
            raise TrainingMediaTaskExecutionFailedError(
                task_type="text",
                reason="payload.prompt is required",
            )

        generated_text = self.text_model_service.generate_text(
            prompt=prompt,
            max_tokens=max(1, int(payload.get("max_tokens", 200) or 200)),
            temperature=float(payload.get("temperature", 0.7) or 0.7),
            system_message=self._optional_str(payload.get("system_message")),
            use_retry=bool(payload.get("use_retry", True)),
        )
        if not generated_text:
            raise TrainingMediaTaskExecutionFailedError(
                task_type="text",
                reason="text model returned empty content",
            )
        return {"text": str(generated_text)}

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None


class TrainingMediaTaskExecutor:
    """Background executor for training media task lifecycle management."""

    _TERMINAL_STATUSES = frozenset({"succeeded", "failed", "timeout"})

    def __init__(
        self,
        *,
        training_store: TrainingStoreProtocol | None = None,
        provider_dispatcher: TrainingMediaTaskProviderDispatcher | None = None,
        config: TrainingMediaTaskExecutorConfig | None = None,
    ):
        self.training_store = training_store or DatabaseTrainingStore()
        self.provider_dispatcher = provider_dispatcher or TrainingMediaTaskProviderDispatcher()
        self.config = config or TrainingMediaTaskExecutorConfig.from_environment()

        self._pool = ThreadPoolExecutor(
            max_workers=self.config.max_workers,
            thread_name_prefix="training_media",
        )
        self._provider_pool = ThreadPoolExecutor(
            max_workers=self.config.max_workers,
            thread_name_prefix="training_media_provider",
        )
        self._scheduled_task_ids: set[str] = set()
        self._scheduled_lock = Lock()

    def submit_task(self, task_id: str) -> bool:
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            return False

        with self._scheduled_lock:
            if normalized_task_id in self._scheduled_task_ids:
                return False
            self._scheduled_task_ids.add(normalized_task_id)

        self._pool.submit(self._run_task, normalized_task_id)
        return True

    def recover_pending_tasks(self) -> dict[str, int]:
        """Recover pending/running tasks when service starts."""
        now = datetime.utcnow()
        recovered_count = 0
        timeout_count = 0

        tasks = self.training_store.list_media_tasks_by_status(["pending", "running"])
        for task in tasks:
            if str(task.status) == "running":
                started_at = task.started_at or task.updated_at or task.created_at
                if started_at is None:
                    started_at = now
                if started_at <= now - timedelta(seconds=self.config.recovery_timeout_seconds):
                    self.training_store.complete_media_task(
                        task.task_id,
                        status="timeout",
                        result_payload=None,
                        error_payload={
                            "type": "timeout",
                            "reason": "recovery timeout exceeded",
                            "timeout_seconds": self.config.recovery_timeout_seconds,
                        },
                        retry_count=task.retry_count,
                    )
                    timeout_count += 1
                    continue

                self.training_store.update_media_task(
                    task.task_id,
                    {
                        "status": "pending",
                        "started_at": None,
                    },
                )

            if self.submit_task(task.task_id):
                recovered_count += 1

        if recovered_count or timeout_count:
            logger.info(
                "training media recovery completed: recovered=%s timeout=%s",
                recovered_count,
                timeout_count,
            )
        return {"recovered": recovered_count, "timed_out": timeout_count}

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False)
        self._provider_pool.shutdown(wait=False, cancel_futures=True)

    def _run_task(self, task_id: str) -> None:
        try:
            self._execute_task_with_retries(task_id)
        finally:
            with self._scheduled_lock:
                self._scheduled_task_ids.discard(task_id)

    def _execute_task_with_retries(self, task_id: str) -> None:
        task = self.training_store.claim_media_task(task_id)
        if task is None:
            return

        retries_used = int(task.retry_count or 0)
        max_retries = int(task.max_retries or 0)

        while True:
            try:
                result = self._execute_task_once(task)
                self.training_store.complete_media_task(
                    task.task_id,
                    status="succeeded",
                    result_payload=result,
                    error_payload=None,
                    retry_count=retries_used,
                )
                return
            except TrainingMediaTaskTimeoutError as exc:
                self.training_store.complete_media_task(
                    task.task_id,
                    status="timeout",
                    result_payload=None,
                    error_payload={
                        "type": "timeout",
                        "message": str(exc),
                        "timeout_seconds": exc.timeout_seconds,
                    },
                    retry_count=retries_used,
                )
                return
            except (TrainingMediaProviderUnavailableError, TrainingMediaTaskExecutionFailedError, Exception) as exc:
                error_payload = {
                    "type": "execution_failed",
                    "message": str(exc),
                    "error_class": type(exc).__name__,
                }

                if retries_used < max_retries:
                    retries_used += 1
                    self.training_store.update_media_task(
                        task.task_id,
                        {
                            "retry_count": retries_used,
                            "error_payload": error_payload,
                        },
                    )
                    if self.config.retry_backoff_seconds > 0:
                        sleep(self.config.retry_backoff_seconds * retries_used)
                    continue

                self.training_store.complete_media_task(
                    task.task_id,
                    status="failed",
                    result_payload=None,
                    error_payload=error_payload,
                    retry_count=retries_used,
                )
                return

    def _execute_task_once(self, task: TrainingMediaTaskRecord) -> dict[str, Any]:
        future = self._provider_pool.submit(
            self.provider_dispatcher.execute_task,
            task_type=task.task_type,
            payload=dict(task.request_payload or {}),
        )
        try:
            result = future.result(timeout=self.config.task_timeout_seconds)
        except FuturesTimeoutError as exc:
            future.cancel()
            raise TrainingMediaTaskTimeoutError(
                task_type=task.task_type,
                timeout_seconds=self.config.task_timeout_seconds,
            ) from exc

        if not isinstance(result, dict):
            raise TrainingMediaTaskExecutionFailedError(
                task_type=task.task_type,
                reason="provider result must be a json object",
            )
        return result
