"""Training media task async executor and provider dispatcher."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import os
import re
from threading import Lock
from time import sleep
from typing import Any, Protocol

from training.exceptions import (
    TrainingMediaProviderUnavailableError,
    TrainingMediaTaskExecutionFailedError,
    TrainingMediaTaskTimeoutError,
)
from training.training_store import DatabaseTrainingStore, TrainingMediaTaskRecord, TrainingStoreProtocol
from utils.logger import get_logger


logger = get_logger(__name__)


class ImageProviderProtocol(Protocol):
    def generate_character_image(
        self,
        *,
        prompt: str,
        character_id: int | None = None,
        user_id: str | None = None,
        image_type: str = "portrait",
        generate_group: bool = True,
        group_count: int = 3,
    ) -> list[str]:
        ...

    def generate_scene_image(self, *, scene_data: dict[str, Any], scene_id: str | None = None, user_id: str | None = None) -> str:
        ...


class TtsProviderProtocol(Protocol):
    def generate_speech(
        self,
        *,
        text: str,
        character_id: int = 1,
        emotion_params: dict[str, Any] | None = None,
        use_cache: bool = True,
        override_voice_id: str | None = None,
    ) -> dict[str, Any]:
        ...


class TextProviderProtocol(Protocol):
    def generate_text(
        self,
        *,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.7,
        system_message: str | None = None,
        use_retry: bool = True,
    ) -> str:
        ...


@dataclass(slots=True)
class TrainingMediaTaskExecutorConfig:
    """Runtime config for media task async execution."""

    max_workers: int = 2
    retry_backoff_seconds: float = 0.2
    task_timeout_seconds: float = 30.0
    scene_task_timeout_seconds: float = 120.0
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
            scene_task_timeout_seconds=max(
                1.0,
                float(os.getenv("TRAINING_MEDIA_SCENE_TASK_TIMEOUT_SECONDS", "120")),
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
        image_service: ImageProviderProtocol | None = None,
        tts_service: TtsProviderProtocol | None = None,
        text_model_service: TextProviderProtocol | None = None,
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

        if self._should_generate_scene_series(payload):
            return self._execute_scene_series_task(payload)

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

    def _should_generate_scene_series(self, payload: dict[str, Any]) -> bool:
        # Gate heavy "scene-series" generation behind a server-side switch.
        # Default: disabled (client payload cannot force it).
        series_enabled = str(os.getenv("TRAINING_ENABLE_SCENE_SERIES", "")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not series_enabled:
            return False
        image_type = str(payload.get("image_type") or "").strip().lower()
        should_generate_series = bool(payload.get("generate_storyline_series"))
        if not should_generate_series:
            return False

        return image_type in {"scene", "smallscene", "small_scene", "storyline_scene"}

    def _execute_scene_series_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.image_service is None:
            raise TrainingMediaProviderUnavailableError(task_type="image", provider="ImageService")

        session_id = self._optional_str(payload.get("session_id")) or self._optional_str(
            payload.get("training_session_id")
        )
        if not session_id:
            raise TrainingMediaTaskExecutionFailedError(
                task_type="image",
                reason="missing_session_id",
            )
        round_no = max(self._optional_int(payload.get("round_no")) or 0, 0)
        scenario_id = self._optional_str(payload.get("scenario_id")) or ""
        major_scene_title = (
            self._optional_str(payload.get("major_scene_title"))
            or self._optional_str(payload.get("scenario_title"))
            or "主场景"
        )
        base_prompt = (
            self._optional_str(payload.get("major_scene_prompt"))
            or self._optional_str(payload.get("prompt"))
            or self._optional_str(payload.get("scenario_prompt"))
            or self._build_default_scene_prompt(payload, major_scene_title=major_scene_title)
        )
        if not base_prompt:
            raise TrainingMediaTaskExecutionFailedError(
                task_type="image",
                reason="scene-series prompt is required",
            )

        micro_scene_count = self._resolve_micro_scene_count(
            payload=payload,
            session_id=session_id,
            round_no=round_no,
            scenario_id=scenario_id,
            major_scene_title=major_scene_title,
        )
        micro_prompts = self._resolve_micro_scene_prompts(
            payload=payload,
            base_prompt=base_prompt,
            major_scene_title=major_scene_title,
            micro_scene_count=micro_scene_count,
        )
        call_sequence_start = max(self._optional_int(payload.get("call_sequence_start")) or 1, 1)

        generated_urls: list[str] = []
        small_scene_urls: list[str] = []
        prompt_bundle: list[dict[str, Any]] = []

        major_call_sequence = call_sequence_start
        major_scene_key = self._build_scene_call_key(
            session_id=session_id,
            round_no=round_no,
            call_sequence=major_call_sequence,
        )
        major_scene_url = self._generate_single_scene_image(
            session_id=session_id,
            round_no=round_no,
            scene_id=major_scene_key,
            scene_name=f"{major_scene_title}_major",
            scene_prompt=base_prompt,
            scene_level="major",
            payload=payload,
        )
        generated_urls.append(major_scene_url)
        prompt_bundle.append(
            {
                "scene_level": "major",
                "call_sequence": major_call_sequence,
                "scene_id": major_scene_key,
                "scene_prompt": base_prompt,
            }
        )

        for index, micro_prompt in enumerate(micro_prompts, start=1):
            call_sequence = call_sequence_start + index
            micro_scene_key = self._build_scene_call_key(
                session_id=session_id,
                round_no=round_no,
                call_sequence=call_sequence,
            )
            micro_scene_url = self._generate_single_scene_image(
                session_id=session_id,
                round_no=round_no,
                scene_id=micro_scene_key,
                scene_name=f"{major_scene_title}_micro_{index}",
                scene_prompt=micro_prompt,
                scene_level="micro",
                payload=payload,
            )
            generated_urls.append(micro_scene_url)
            small_scene_urls.append(micro_scene_url)
            prompt_bundle.append(
                {
                    "scene_level": "micro",
                    "call_sequence": call_sequence,
                    "scene_id": micro_scene_key,
                    "scene_prompt": micro_prompt,
                }
            )

        return {
            "preview_url": major_scene_url,
            "major_scene_url": major_scene_url,
            "small_scene_urls": small_scene_urls,
            "image_urls": generated_urls,
            "series_size": len(generated_urls),
            "series_profile": {
                "session_id": session_id,
                "round_no": round_no,
                "major_scene_count": 1,
                "micro_scene_count": micro_scene_count,
                "naming_rule": "sessionId_r{roundNo}_call_{sequence}",
            },
            "prompt_bundle": prompt_bundle,
        }

    def _generate_single_scene_image(
        self,
        *,
        session_id: str,
        round_no: int,
        scene_id: str,
        scene_name: str,
        scene_prompt: str,
        scene_level: str,
        payload: dict[str, Any],
    ) -> str:
        scene_data = {
            "scene_id": scene_id,
            "scene_name": scene_name,
            "scene_description": scene_prompt,
            # Explicit prompt has the highest priority in image_generation_service.
            "prompt": scene_prompt,
            "atmosphere": self._optional_str(payload.get("atmosphere")),
            "time_of_day": self._optional_str(payload.get("time_of_day")),
            "weather": self._optional_str(payload.get("weather")),
            "session_id": session_id,
            "round_no": round_no,
            "scene_level": scene_level,
        }
        scene_image_url = self.image_service.generate_scene_image(
            scene_data=scene_data,
            scene_id=scene_id,
            user_id=session_id,
        )
        if not scene_image_url:
            raise TrainingMediaTaskExecutionFailedError(
                task_type="image",
                reason=f"scene-series image generation failed: scene_id={scene_id}",
            )
        return str(scene_image_url)

    def _resolve_micro_scene_count(
        self,
        *,
        payload: dict[str, Any],
        session_id: str,
        round_no: int,
        scenario_id: str,
        major_scene_title: str,
    ) -> int:
        requested_count = self._optional_int(payload.get("micro_scene_count"))
        if requested_count is not None:
            return min(max(requested_count, 2), 3)

        seed_source = f"{session_id}|{round_no}|{scenario_id}|{major_scene_title}"
        digest = sha256(seed_source.encode("utf-8")).hexdigest()
        return 2 + (int(digest[:2], 16) % 2)

    def _resolve_micro_scene_prompts(
        self,
        *,
        payload: dict[str, Any],
        base_prompt: str,
        major_scene_title: str,
        micro_scene_count: int,
    ) -> list[str]:
        provided_prompts = payload.get("micro_scene_prompts")
        normalized_provided_prompts: list[str] = []
        if isinstance(provided_prompts, list):
            for item in provided_prompts:
                prompt = self._optional_str(item)
                if prompt:
                    normalized_provided_prompts.append(prompt)

        if len(normalized_provided_prompts) >= micro_scene_count:
            return normalized_provided_prompts[:micro_scene_count]

        decision_focus = self._optional_str(payload.get("decision_focus")) or "信息核验与发布权衡"
        mission = self._optional_str(payload.get("mission")) or "保持连续叙事与风险可控"
        fallback_prompts = list(normalized_provided_prompts)
        for index in range(len(fallback_prompts) + 1, micro_scene_count + 1):
            fallback_prompts.append(
                (
                    f"{base_prompt}\n"
                    f"镜头切换到“{major_scene_title}”对应的小场景{index}，"
                    f"突出{decision_focus}，并保持“{mission}”的连续氛围。"
                )
            )
        return fallback_prompts

    def _build_default_scene_prompt(self, payload: dict[str, Any], *, major_scene_title: str) -> str:
        scenario_brief = self._optional_str(payload.get("brief")) or "场景处于高压信息流中"
        mission = self._optional_str(payload.get("mission")) or "在速度与准确之间达成平衡"
        decision_focus = self._optional_str(payload.get("decision_focus")) or "完成关键决策"
        return (
            f"{major_scene_title}。{scenario_brief}。"
            f"任务：{mission}。决策焦点：{decision_focus}。"
            "视觉风格：纪实新闻叙事，环境细节真实，无人物特写。"
        )

    def _build_scene_call_key(self, *, session_id: str, round_no: int, call_sequence: int) -> str:
        safe_session_id = re.sub(r"[^0-9A-Za-z_-]+", "_", str(session_id or "training_session")).strip("_")
        if not safe_session_id:
            safe_session_id = "training_session"
        return f"{safe_session_id}_r{max(round_no, 0):02d}_call_{max(call_sequence, 1):02d}"

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
            logger.info("training media submit rejected: reason=empty_task_id")
            return False

        with self._scheduled_lock:
            if normalized_task_id in self._scheduled_task_ids:
                logger.info("training media submit rejected: reason=already_scheduled task_id=%s", normalized_task_id)
                return False
            self._scheduled_task_ids.add(normalized_task_id)

        logger.info("training media submit accepted: task_id=%s", normalized_task_id)
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
                            "message": "recovery timeout exceeded",
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
                if isinstance(exc, TrainingMediaTaskExecutionFailedError):
                    error_payload["reason"] = exc.reason

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
        timeout_seconds = self._resolve_task_timeout_seconds(task)
        future = self._provider_pool.submit(
            self.provider_dispatcher.execute_task,
            task_type=task.task_type,
            payload=dict(task.request_payload or {}),
        )
        try:
            result = future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            future.cancel()
            raise TrainingMediaTaskTimeoutError(
                task_type=task.task_type,
                timeout_seconds=timeout_seconds,
            ) from exc

        if not isinstance(result, dict):
            raise TrainingMediaTaskExecutionFailedError(
                task_type=task.task_type,
                reason="provider result must be a json object",
            )
        return result

    def _resolve_task_timeout_seconds(self, task: TrainingMediaTaskRecord) -> float:
        if str(task.task_type or "").strip().lower() != "image":
            return float(self.config.task_timeout_seconds)

        payload = dict(task.request_payload or {})
        image_type = str(payload.get("image_type") or "").strip().lower()
        generate_series = bool(payload.get("generate_storyline_series"))
        is_scene_series = generate_series and image_type in {"scene", "smallscene", "small_scene", "storyline_scene"}
        if is_scene_series:
            return float(self.config.scene_task_timeout_seconds)

        return float(self.config.task_timeout_seconds)
