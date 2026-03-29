"""Persistent async preview-job service for training character portrait generation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
from threading import Event, Lock
from typing import Any, Callable, Dict, List

from api.services.character_service import CharacterNotFoundError, CharacterService
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError
from training.constants import TRAINING_DEFAULT_SCENARIO_SEQUENCE
from training.exceptions import TrainingStorageUnavailableError
from training.media_task_executor import TrainingMediaTaskProviderDispatcher
from training.training_character_preview_job_repository import (
    SqlAlchemyTrainingCharacterPreviewJobRepository,
)
from utils.logger import get_logger


logger = get_logger(__name__)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_optional_text(value: Any) -> str | None:
    normalized = _normalize_text(value)
    return normalized or None


def _normalize_payload_map(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _normalize_image_urls(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in (_normalize_text(url) for url in value) if item]


def _normalize_prompt_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    prompts: List[str] = []
    for item in value:
        normalized = _normalize_optional_text(item)
        if normalized:
            prompts.append(normalized)
    return prompts


def _normalize_payload_list(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: List[Dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            items.append(dict(item))
    return items


def _normalize_positive_int(
    value: Any,
    default: int,
    *,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = int(default)

    normalized = max(normalized, int(minimum))
    if maximum is not None:
        normalized = min(normalized, int(maximum))
    return normalized


def _normalize_non_negative_int(value: Any, default: int = 0) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = int(default)
    return max(normalized, 0)


def _normalize_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = _normalize_text(value).lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _parse_iso_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    normalized = _normalize_text(value)
    if not normalized:
        return None
    candidate = normalized
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


_STORAGE_UNAVAILABLE_TOKENS = (
    "no such table",
    "does not exist",
    "unknown table",
    "unable to open database file",
)

_SCENE_GENERATION_STATUS_VALUES = frozenset(
    {
        "pending",
        "running",
        "succeeded",
        "failed",
        "skipped",
    }
)


def _normalize_scene_generation_status(value: Any, *, default: str = "pending") -> str:
    normalized = _normalize_text(value).lower()
    if normalized in _SCENE_GENERATION_STATUS_VALUES:
        return normalized
    fallback = _normalize_text(default).lower()
    if fallback in _SCENE_GENERATION_STATUS_VALUES:
        return fallback
    return "pending"


def _is_storage_unavailable_error(exc: Exception) -> bool:
    if isinstance(exc, (OperationalError, ProgrammingError)):
        return True
    if not isinstance(exc, SQLAlchemyError):
        return False
    normalized_error = _normalize_text(exc).lower()
    return any(token in normalized_error for token in _STORAGE_UNAVAILABLE_TOKENS)


@dataclass(slots=True)
class TrainingCharacterPreviewJobRecord:
    """Stable preview job read model."""

    job_id: str
    character_id: int
    idempotency_key: str
    status: str
    request_payload_canonical: str
    image_urls: List[str]
    scene_storyline_script: Dict[str, Any]
    scene_groups: List[Dict[str, Any]]
    scene_generation_status: str
    scene_generation_error: str | None
    scene_generated_at: datetime | None
    attempt_count: int
    last_failed_at: datetime | None
    last_error_message: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "character_id": self.character_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status,
            "image_urls": list(self.image_urls),
            "scene_storyline_script": dict(self.scene_storyline_script),
            "scene_groups": [dict(item) for item in self.scene_groups],
            "scene_generation_status": self.scene_generation_status,
            "scene_generation_error": self.scene_generation_error,
            "scene_generated_at": (
                self.scene_generated_at.isoformat() if isinstance(self.scene_generated_at, datetime) else None
            ),
            "attempt_count": self.attempt_count,
            "last_failed_at": (
                self.last_failed_at.isoformat() if isinstance(self.last_failed_at, datetime) else None
            ),
            "last_error_message": self.last_error_message,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TrainingCharacterPreviewJobNotFoundError(ValueError):
    """Raised when preview job does not exist."""

    def __init__(self, job_id: str):
        normalized_job_id = _normalize_text(job_id)
        self.job_id = normalized_job_id
        super().__init__(f"training character preview job not found: {normalized_job_id}")


class TrainingCharacterPreviewJobConflictError(ValueError):
    """Raised when idempotency key is reused for a different request scope."""

    def __init__(self, *, idempotency_key: str, existing_job_id: str):
        normalized_key = _normalize_text(idempotency_key)
        normalized_job_id = _normalize_text(existing_job_id)
        self.idempotency_key = normalized_key
        self.existing_job_id = normalized_job_id
        super().__init__(
            "training character preview idempotency key conflicts with another request: "
            f"idempotency_key={normalized_key}, existing_job_id={normalized_job_id}"
        )


class TrainingCharacterPreviewJobInvalidError(ValueError):
    """Raised when preview job request is invalid."""

    def __init__(self, message: str):
        normalized_message = _normalize_text(message) or "training character preview request is invalid"
        super().__init__(normalized_message)


class TrainingCharacterPreviewCharacterNotFoundError(ValueError):
    """Raised when target training character is missing."""

    def __init__(self, character_id: int):
        self.character_id = int(character_id)
        super().__init__(f"training character not found: {self.character_id}")


class TrainingCharacterPreviewJobService:
    """Creates persistent async preview jobs and exposes pollable status."""

    _TERMINAL_STATUSES = frozenset({"succeeded", "failed"})
    _SCENE_TERMINAL_STATUSES = frozenset({"succeeded", "failed", "skipped"})
    _FIXED_CAST: tuple[dict[str, str], ...] = (
        {"name": "赵川", "role": "前线通讯员"},
        {"name": "老何", "role": "印刷与发布"},
        {"name": "陈编辑", "role": "总编把关"},
        {"name": "林岚", "role": "摄影记者"},
    )

    def __init__(
        self,
        *,
        character_service: CharacterService | None = None,
        preview_job_repository: SqlAlchemyTrainingCharacterPreviewJobRepository | None = None,
        max_workers: int = 2,
        generation_timeout_seconds: float = 180.0,
        recovery_timeout_seconds: float = 300.0,
        enable_scene_group_generation: bool = False,
        default_scene_group_count: int = 6,
        scene_generation_timeout_seconds: float = 900.0,
        micro_scene_min: int = 2,
        micro_scene_max: int = 3,
    ):
        self.character_service = character_service or CharacterService()
        self.preview_job_repository = (
            preview_job_repository or SqlAlchemyTrainingCharacterPreviewJobRepository()
        )
        self.generation_timeout_seconds = max(float(generation_timeout_seconds or 0.0), 1.0)
        self.recovery_timeout_seconds = max(float(recovery_timeout_seconds or 0.0), 1.0)
        self.enable_scene_group_generation = bool(enable_scene_group_generation)
        self.default_scene_group_count = _normalize_positive_int(
            default_scene_group_count,
            6,
            minimum=1,
            maximum=6,
        )
        self.scene_generation_timeout_seconds = max(
            float(scene_generation_timeout_seconds or 0.0),
            30.0,
        )
        self.micro_scene_min = _normalize_positive_int(micro_scene_min, 2, minimum=1, maximum=3)
        self.micro_scene_max = _normalize_positive_int(
            micro_scene_max,
            3,
            minimum=self.micro_scene_min,
            maximum=3,
        )

        workers = max(int(max_workers or 1), 1)
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="training_preview")
        self._provider_pool = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="training_preview_provider",
        )
        self._scene_pool = ThreadPoolExecutor(
            max_workers=max(1, min(workers, 2)),
            thread_name_prefix="training_preview_scene",
        )
        self._scheduled_job_ids: set[str] = set()
        self._scheduled_scene_job_ids: set[str] = set()
        self._scheduled_lock = Lock()
        self._scheduled_scene_lock = Lock()
        self._shutdown_lock = Lock()
        self._is_shutting_down = Event()
        self._scene_dispatcher = self._build_scene_dispatcher()

    def _build_scene_dispatcher(self) -> TrainingMediaTaskProviderDispatcher | None:
        if not self.enable_scene_group_generation:
            return None
        image_service = getattr(self.character_service, "image_service", None)
        if image_service is None:
            logger.warning(
                "training preview scene generation disabled: character_service.image_service unavailable"
            )
            return None
        return TrainingMediaTaskProviderDispatcher(image_service=image_service)

    def _guard_repository_call(
        self,
        *,
        operation: str,
        call: Callable[[], Any],
        details: Dict[str, Any] | None = None,
    ) -> Any:
        try:
            return call()
        except Exception as exc:
            if not _is_storage_unavailable_error(exc):
                raise
            normalized_details: Dict[str, Any] = {"operation": operation}
            if isinstance(details, dict):
                normalized_details.update(dict(details))
            logger.error(
                "training preview storage unavailable: operation=%s error=%s details=%s",
                operation,
                str(exc),
                normalized_details,
            )
            raise TrainingStorageUnavailableError(
                message=f"training preview storage unavailable: operation={operation}",
                details=normalized_details,
            ) from exc

    def create_preview_job(
        self,
        *,
        character_id: int,
        idempotency_key: str,
        user_id: str | None = None,
        image_type: str | None = "portrait",
        group_count: int = 3,
        generate_scene_groups: bool | None = None,
        scene_group_count: int | None = None,
        micro_scene_min: int | None = None,
        micro_scene_max: int | None = None,
    ) -> TrainingCharacterPreviewJobRecord:
        try:
            normalized_character_id = int(character_id)
        except (TypeError, ValueError) as exc:
            raise TrainingCharacterPreviewJobInvalidError(
                "training preview character_id must be a positive integer"
            ) from exc
        if normalized_character_id <= 0:
            raise TrainingCharacterPreviewJobInvalidError(
                "training preview character_id must be a positive integer"
            )

        normalized_key = _normalize_text(idempotency_key)
        if not normalized_key:
            raise TrainingCharacterPreviewJobInvalidError("training preview idempotency_key is required")

        request_payload = self._build_generation_payload(
            character_id=normalized_character_id,
            user_id=user_id,
            image_type=image_type,
            group_count=group_count,
            idempotency_key=normalized_key,
            generate_scene_groups=generate_scene_groups,
            scene_group_count=scene_group_count,
            micro_scene_min=micro_scene_min,
            micro_scene_max=micro_scene_max,
        )
        canonical_payload = self._canonicalize_payload(request_payload)

        existing_row = self._guard_repository_call(
            operation="get_preview_job_by_idempotency_key",
            call=lambda: self.preview_job_repository.get_preview_job_by_idempotency_key(normalized_key),
            details={"idempotency_key": normalized_key},
        )
        if existing_row is not None:
            if (
                int(getattr(existing_row, "character_id", 0) or 0) == normalized_character_id
                and str(getattr(existing_row, "request_payload_canonical", "") or "")
                == canonical_payload
            ):
                existing_record = self._to_record(existing_row)
                existing_payload = _normalize_payload_map(getattr(existing_row, "request_payload", {}))
                if existing_record.status not in self._TERMINAL_STATUSES:
                    self.submit_preview_job(existing_record.job_id)
                    return self.get_preview_job(existing_record.job_id)
                if existing_record.status == "failed":
                    retry_payload = self._build_retry_payload(
                        base_request_payload=request_payload,
                        existing_request_payload=existing_payload,
                        existing_error_message=existing_record.error_message,
                        existing_finished_at=getattr(existing_row, "finished_at", None),
                    )
                    self._guard_repository_call(
                        operation="update_preview_job",
                        call=lambda: self.preview_job_repository.update_preview_job(
                            existing_record.job_id,
                            {
                                "status": "pending",
                                "image_urls": [],
                                "error_message": None,
                                "started_at": None,
                                "finished_at": None,
                                "request_payload": retry_payload,
                                "request_payload_canonical": canonical_payload,
                            },
                        ),
                        details={"job_id": existing_record.job_id, "reason": "retry_failed_job"},
                    )
                    self.submit_preview_job(existing_record.job_id)
                    return self.get_preview_job(existing_record.job_id)
                if existing_record.status == "succeeded":
                    self._maybe_schedule_scene_generation(
                        job_id=existing_record.job_id,
                        request_payload=existing_payload,
                    )
                return existing_record
            raise TrainingCharacterPreviewJobConflictError(
                idempotency_key=normalized_key,
                existing_job_id=str(getattr(existing_row, "job_id", "") or ""),
            )

        created_row = self._guard_repository_call(
            operation="create_preview_job",
            call=lambda: self.preview_job_repository.create_preview_job(
                character_id=normalized_character_id,
                idempotency_key=normalized_key,
                request_payload=request_payload,
                request_payload_canonical=canonical_payload,
            ),
            details={
                "character_id": normalized_character_id,
                "idempotency_key": normalized_key,
            },
        )
        created_record = self._to_record(created_row)
        self.submit_preview_job(created_record.job_id)
        return self.get_preview_job(created_record.job_id)

    def get_preview_job(self, job_id: str) -> TrainingCharacterPreviewJobRecord:
        normalized_job_id = _normalize_text(job_id)
        if not normalized_job_id:
            raise TrainingCharacterPreviewJobNotFoundError(job_id=job_id)

        row = self._guard_repository_call(
            operation="get_preview_job",
            call=lambda: self.preview_job_repository.get_preview_job(normalized_job_id),
            details={"job_id": normalized_job_id},
        )
        if row is None:
            raise TrainingCharacterPreviewJobNotFoundError(job_id=normalized_job_id)
        return self._to_record(row)

    def submit_preview_job(self, job_id: str) -> bool:
        normalized_job_id = _normalize_text(job_id)
        if not normalized_job_id:
            return False
        if self._is_shutting_down.is_set():
            return False

        with self._scheduled_lock:
            if normalized_job_id in self._scheduled_job_ids:
                return False
            self._scheduled_job_ids.add(normalized_job_id)

        try:
            self._pool.submit(self._run_preview_job, normalized_job_id)
        except RuntimeError:
            with self._scheduled_lock:
                self._scheduled_job_ids.discard(normalized_job_id)
            return False
        return True

    def submit_scene_generation_job(self, *, job_id: str, request_payload: Dict[str, Any]) -> bool:
        normalized_job_id = _normalize_text(job_id)
        if not normalized_job_id:
            return False
        if self._is_shutting_down.is_set():
            return False

        with self._scheduled_scene_lock:
            if normalized_job_id in self._scheduled_scene_job_ids:
                return False
            self._scheduled_scene_job_ids.add(normalized_job_id)

        try:
            self._scene_pool.submit(
                self._run_scene_generation_job,
                normalized_job_id,
                dict(request_payload or {}),
            )
        except RuntimeError:
            with self._scheduled_scene_lock:
                self._scheduled_scene_job_ids.discard(normalized_job_id)
            return False
        return True

    def recover_pending_jobs(self) -> dict[str, int]:
        """Recover pending/running jobs after service restart."""

        now = datetime.utcnow()
        recovered_count = 0
        timed_out_count = 0
        rows = self._guard_repository_call(
            operation="list_preview_jobs_by_status",
            call=lambda: self.preview_job_repository.list_preview_jobs_by_status(["pending", "running"]),
            details={"statuses": ["pending", "running"]},
        )
        for row in rows:
            status = str(getattr(row, "status", "") or "").strip().lower()
            job_id = str(getattr(row, "job_id", "") or "").strip()
            if not job_id:
                continue

            if status == "running":
                started_at = (
                    getattr(row, "started_at", None)
                    or getattr(row, "updated_at", None)
                    or getattr(row, "created_at", None)
                    or now
                )
                if started_at <= now - timedelta(seconds=self.recovery_timeout_seconds):
                    self._guard_repository_call(
                        operation="complete_preview_job",
                        call=lambda: self.preview_job_repository.complete_preview_job(
                            job_id,
                            status="failed",
                            image_urls=[],
                            error_message=(
                                "training preview recovery timeout exceeded: "
                                f"{self.recovery_timeout_seconds:.1f}s"
                            ),
                        ),
                        details={"job_id": job_id},
                    )
                    timed_out_count += 1
                    continue

                self._guard_repository_call(
                    operation="update_preview_job",
                    call=lambda: self.preview_job_repository.update_preview_job(
                        job_id,
                        {
                            "status": "pending",
                            "started_at": None,
                        },
                    ),
                    details={"job_id": job_id},
                )

            if self.submit_preview_job(job_id):
                recovered_count += 1

        scene_recover_result = self._recover_scene_generation_jobs()
        if recovered_count or timed_out_count or scene_recover_result["recovered"] or scene_recover_result["timed_out"]:
            logger.info(
                "training preview recovery completed: recovered=%s timed_out=%s scene_recovered=%s scene_timed_out=%s",
                recovered_count,
                timed_out_count,
                scene_recover_result["recovered"],
                scene_recover_result["timed_out"],
            )
        return {
            "recovered": recovered_count,
            "timed_out": timed_out_count,
            "scene_recovered": scene_recover_result["recovered"],
            "scene_timed_out": scene_recover_result["timed_out"],
        }

    def _recover_scene_generation_jobs(self) -> dict[str, int]:
        if not self.enable_scene_group_generation:
            return {"recovered": 0, "timed_out": 0}

        now = datetime.utcnow()
        recovered = 0
        timed_out = 0
        rows = self._guard_repository_call(
            operation="list_preview_jobs_by_status",
            call=lambda: self.preview_job_repository.list_preview_jobs_by_status(["succeeded"]),
            details={"statuses": ["succeeded"]},
        )
        for row in rows:
            job_id = _normalize_text(getattr(row, "job_id", ""))
            if not job_id:
                continue

            request_payload = _normalize_payload_map(getattr(row, "request_payload", {}))
            if not self._should_generate_scene_groups(request_payload):
                continue

            scene_status = _normalize_scene_generation_status(
                request_payload.get("scene_generation_status"),
                default="pending",
            )
            if scene_status in self._SCENE_TERMINAL_STATUSES:
                continue

            if scene_status == "running":
                scene_started_at = (
                    _parse_iso_datetime(request_payload.get("scene_generation_started_at"))
                    or getattr(row, "updated_at", None)
                    or getattr(row, "created_at", None)
                    or now
                )
                if scene_started_at <= now - timedelta(seconds=self.recovery_timeout_seconds):
                    self._update_scene_generation_metadata(
                        job_id=job_id,
                        status="failed",
                        error_message=(
                            "training preview scene generation recovery timeout exceeded: "
                            f"{self.recovery_timeout_seconds:.1f}s"
                        ),
                    )
                    timed_out += 1
                    continue

            if self.submit_scene_generation_job(job_id=job_id, request_payload=request_payload):
                recovered += 1

        return {"recovered": recovered, "timed_out": timed_out}

    def shutdown(self, *, wait: bool = True) -> None:
        with self._shutdown_lock:
            if self._is_shutting_down.is_set():
                return
            self._is_shutting_down.set()

        # Stop receiving new tasks first, then drain running workers.
        self._pool.shutdown(wait=wait, cancel_futures=not wait)
        self._scene_pool.shutdown(wait=wait, cancel_futures=not wait)
        self._provider_pool.shutdown(wait=wait, cancel_futures=not wait)

    def _build_retry_payload(
        self,
        *,
        base_request_payload: Dict[str, Any],
        existing_request_payload: Dict[str, Any],
        existing_error_message: str | None,
        existing_finished_at: Any,
    ) -> Dict[str, Any]:
        merged_payload = dict(base_request_payload or {})
        previous_attempt_count = _normalize_non_negative_int(
            existing_request_payload.get("attempt_count"),
            0,
        )
        merged_payload["attempt_count"] = max(
            _normalize_non_negative_int(merged_payload.get("attempt_count"), 0),
            previous_attempt_count,
        )
        last_failed_at = (
            _parse_iso_datetime(existing_request_payload.get("last_failed_at"))
            or _parse_iso_datetime(existing_finished_at)
        )
        merged_payload["last_failed_at"] = (
            last_failed_at.isoformat() if isinstance(last_failed_at, datetime) else None
        )
        merged_payload["last_error_message"] = (
            _normalize_optional_text(existing_request_payload.get("last_error_message"))
            or _normalize_optional_text(existing_error_message)
        )
        merged_payload["last_retry_at"] = datetime.utcnow().isoformat()
        return merged_payload

    def _record_failed_attempt_metadata(self, *, job_id: str, error_message: str) -> None:
        normalized_job_id = _normalize_text(job_id)
        if not normalized_job_id:
            return

        row = self._guard_repository_call(
            operation="get_preview_job",
            call=lambda: self.preview_job_repository.get_preview_job(normalized_job_id),
            details={"job_id": normalized_job_id, "reason": "record_failed_attempt"},
        )
        if row is None:
            return

        request_payload = _normalize_payload_map(getattr(row, "request_payload", {}))
        request_payload["attempt_count"] = _normalize_non_negative_int(
            request_payload.get("attempt_count"),
            0,
        ) + 1
        request_payload["last_failed_at"] = datetime.utcnow().isoformat()
        request_payload["last_error_message"] = _normalize_optional_text(error_message)

        self._guard_repository_call(
            operation="update_preview_job",
            call=lambda: self.preview_job_repository.update_preview_job(
                normalized_job_id,
                {"request_payload": request_payload},
            ),
            details={"job_id": normalized_job_id, "reason": "record_failed_attempt"},
        )

    def _run_preview_job(self, job_id: str) -> None:
        try:
            self._execute_preview_job(job_id)
        except Exception as exc:
            logger.error(
                "training preview job runner failed: job_id=%s error=%s",
                job_id,
                str(exc),
                exc_info=True,
            )
        finally:
            with self._scheduled_lock:
                self._scheduled_job_ids.discard(job_id)

    def _run_scene_generation_job(self, job_id: str, request_payload: Dict[str, Any]) -> None:
        try:
            self._execute_scene_generation_job(job_id=job_id, request_payload=request_payload)
        except Exception as exc:
            logger.error(
                "training preview scene generation runner failed: job_id=%s error=%s",
                job_id,
                str(exc),
                exc_info=True,
            )
            self._update_scene_generation_metadata(
                job_id=job_id,
                status="failed",
                error_message=str(exc),
            )
        finally:
            with self._scheduled_scene_lock:
                self._scheduled_scene_job_ids.discard(job_id)

    def _execute_preview_job(self, job_id: str) -> None:
        claimed_row = self.preview_job_repository.claim_preview_job(job_id)
        if claimed_row is None:
            return

        request_payload = _normalize_payload_map(getattr(claimed_row, "request_payload", {}))
        try:
            image_urls = self._execute_generation_with_timeout(request_payload)
            normalized_urls = _normalize_image_urls(image_urls)
            if not normalized_urls:
                raise RuntimeError("preview generation returned empty image urls")

            self.preview_job_repository.complete_preview_job(
                job_id,
                status="succeeded",
                image_urls=normalized_urls,
                error_message=None,
            )
            self._maybe_schedule_scene_generation(
                job_id=job_id,
                request_payload=request_payload,
            )
        except Exception as exc:
            logger.error(
                "training preview job failed: job_id=%s error=%s",
                job_id,
                str(exc),
                exc_info=True,
            )
            self._record_failed_attempt_metadata(
                job_id=job_id,
                error_message=str(exc),
            )
            self.preview_job_repository.complete_preview_job(
                job_id,
                status="failed",
                image_urls=[],
                error_message=str(exc),
            )
            self._update_scene_generation_metadata(
                job_id=job_id,
                status="skipped",
                error_message="preview generation failed before scene generation",
            )

    def _maybe_schedule_scene_generation(self, *, job_id: str, request_payload: Dict[str, Any]) -> bool:
        if not self._should_generate_scene_groups(request_payload):
            self._update_scene_generation_metadata(
                job_id=job_id,
                status="skipped",
                error_message=None,
            )
            return False

        current_status = _normalize_scene_generation_status(
            request_payload.get("scene_generation_status"),
            default="pending",
        )
        if current_status in {"running", "succeeded"}:
            return False

        return self.submit_scene_generation_job(job_id=job_id, request_payload=request_payload)

    def _should_generate_scene_groups(self, request_payload: Dict[str, Any]) -> bool:
        if not self.enable_scene_group_generation:
            return False
        if self._scene_dispatcher is None:
            return False
        return _normalize_bool(request_payload.get("generate_scene_groups"), default=False)

    def _execute_scene_generation_job(self, *, job_id: str, request_payload: Dict[str, Any]) -> None:
        if not self._should_generate_scene_groups(request_payload):
            self._update_scene_generation_metadata(
                job_id=job_id,
                status="skipped",
                error_message=None,
            )
            return

        self._update_scene_generation_metadata(
            job_id=job_id,
            status="running",
            error_message=None,
            scene_generated_at=None,
            scene_generation_started_at=datetime.utcnow().isoformat(),
        )

        scene_storyline_script: Dict[str, Any] | None = None
        try:
            scene_storyline_script = self._build_scene_storyline_script(
                request_payload=request_payload,
                job_id=job_id,
            )
            scene_groups = self._execute_scene_group_generation_with_timeout(
                job_id=job_id,
                request_payload=request_payload,
                scene_storyline_script=scene_storyline_script,
            )
            self._update_scene_generation_metadata(
                job_id=job_id,
                status="succeeded",
                error_message=None,
                scene_storyline_script=scene_storyline_script,
                scene_groups=scene_groups,
                scene_generated_at=datetime.utcnow().isoformat(),
                scene_generation_started_at=None,
            )
        except Exception as exc:
            logger.error(
                "training preview scene generation failed: job_id=%s error=%s",
                job_id,
                str(exc),
                exc_info=True,
            )
            self._update_scene_generation_metadata(
                job_id=job_id,
                status="failed",
                error_message=str(exc),
                scene_storyline_script=scene_storyline_script,
                scene_generation_started_at=None,
            )

    def _execute_scene_group_generation_with_timeout(
        self,
        *,
        job_id: str,
        request_payload: Dict[str, Any],
        scene_storyline_script: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        future = self._provider_pool.submit(
            self._execute_scene_group_generation,
            job_id,
            request_payload,
            scene_storyline_script,
        )
        try:
            result = future.result(timeout=self.scene_generation_timeout_seconds)
        except FuturesTimeoutError as exc:
            future.cancel()
            raise RuntimeError(
                "training preview scene generation timed out after "
                f"{self.scene_generation_timeout_seconds:.1f} seconds"
            ) from exc
        return _normalize_payload_list(result)

    def _execute_scene_group_generation(
        self,
        job_id: str,
        request_payload: Dict[str, Any],
        scene_storyline_script: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        dispatcher = self._scene_dispatcher
        if dispatcher is None:
            raise RuntimeError("training preview scene dispatcher is unavailable")

        groups = _normalize_payload_list(scene_storyline_script.get("groups"))
        if not groups:
            return []

        scene_session_id = _normalize_optional_text(scene_storyline_script.get("scene_session_id")) or (
            f"preview_{_normalize_text(job_id).replace('-', '_')}"
        )
        generated_groups: List[Dict[str, Any]] = []
        for group in groups:
            group_index = _normalize_positive_int(
                group.get("group_index"),
                len(generated_groups) + 1,
                minimum=1,
                maximum=999,
            )
            major_scene_title = _normalize_optional_text(group.get("major_scene_title")) or f"主线场景{group_index}"
            micro_scene_prompts = _normalize_prompt_list(group.get("micro_scene_prompts"))
            major_scene_prompt = _normalize_optional_text(group.get("major_scene_prompt"))
            if not major_scene_prompt:
                major_scene_prompt = f"{major_scene_title}，纪实新闻叙事，突出关键决策压力。"

            generation_payload: Dict[str, Any] = {
                "session_id": scene_session_id,
                "round_no": group_index,
                "scenario_id": _normalize_optional_text(group.get("major_scene_id")) or "",
                "major_scene_title": major_scene_title,
                "major_scene_prompt": major_scene_prompt,
                "decision_focus": _normalize_optional_text(group.get("decision_focus")) or "",
                "mission": _normalize_optional_text(group.get("mission")) or "",
                "micro_scene_prompts": micro_scene_prompts,
                "micro_scene_count": len(micro_scene_prompts),
                "call_sequence_start": 1,
                "image_type": "scene",
                "generate_storyline_series": True,
            }

            task_result = dispatcher.execute_task(task_type="image", payload=generation_payload)
            generated_groups.append(
                {
                    "group_index": group_index,
                    "major_scene_id": _normalize_optional_text(group.get("major_scene_id")),
                    "major_scene_title": major_scene_title,
                    "major_scene_url": _normalize_optional_text(task_result.get("major_scene_url")),
                    "small_scene_urls": _normalize_image_urls(task_result.get("small_scene_urls")),
                    "image_urls": _normalize_image_urls(task_result.get("image_urls")),
                    "prompt_bundle": _normalize_payload_list(task_result.get("prompt_bundle")),
                    "series_profile": _normalize_payload_map(task_result.get("series_profile")),
                }
            )
        return generated_groups

    def _build_scene_storyline_script(
        self,
        *,
        request_payload: Dict[str, Any],
        job_id: str,
    ) -> Dict[str, Any]:
        major_scenes = self._resolve_major_scene_templates()
        scene_group_count = _normalize_positive_int(
            request_payload.get("scene_group_count"),
            self.default_scene_group_count,
            minimum=1,
            maximum=min(6, len(major_scenes)),
        )
        selected_major_scenes = major_scenes[:scene_group_count]

        player_name = _normalize_optional_text(request_payload.get("name")) or "训练记者"
        player_identity = _normalize_optional_text(request_payload.get("identity")) or "前线记者"
        identity_code = _normalize_optional_text(request_payload.get("identity_code")) or "default"
        user_id = _normalize_optional_text(request_payload.get("user_id")) or "training_user"
        character_id = _normalize_text(request_payload.get("character_id"))
        idempotency_key = _normalize_optional_text(request_payload.get("idempotency_key")) or job_id
        storyline_seed = (
            f"{character_id}|{user_id}|{player_name}|{player_identity}|{identity_code}|{idempotency_key}"
        )
        storyline_digest = sha256(storyline_seed.encode("utf-8")).hexdigest()
        storyline_id = f"storyline_{storyline_digest[:12]}"
        scene_session_id = f"{storyline_id}_{_normalize_text(job_id).replace('-', '')[:8]}"

        effective_micro_scene_min = _normalize_positive_int(
            request_payload.get("micro_scene_min"),
            self.micro_scene_min,
            minimum=1,
            maximum=3,
        )
        effective_micro_scene_max = _normalize_positive_int(
            request_payload.get("micro_scene_max"),
            self.micro_scene_max,
            minimum=effective_micro_scene_min,
            maximum=3,
        )

        groups: List[Dict[str, Any]] = []
        for group_index, major_scene in enumerate(selected_major_scenes, start=1):
            major_scene_id = _normalize_optional_text(major_scene.get("id")) or f"S{group_index}"
            major_scene_title = _normalize_optional_text(major_scene.get("title")) or f"主线场景{group_index}"
            group_seed = f"{storyline_seed}|{major_scene_id}|{group_index}"
            group_digest = sha256(group_seed.encode("utf-8")).hexdigest()
            micro_scene_count = effective_micro_scene_min + (
                int(group_digest[:2], 16) % (effective_micro_scene_max - effective_micro_scene_min + 1)
            )

            cast_primary = self._FIXED_CAST[(group_index - 1) % len(self._FIXED_CAST)]
            cast_secondary = self._FIXED_CAST[group_index % len(self._FIXED_CAST)]
            decision_focus = "在时效、核验与风险控制之间做出可复盘决策"
            mission = (
                f"{cast_primary['name']}与{cast_secondary['name']}协同推进，"
                f"你需要以“{player_identity}”身份完成本幕关键发布决策。"
            )
            major_scene_prompt = (
                f"{major_scene_title}。{player_name}（{player_identity}）进入该幕，"
                f"与固定角色{cast_primary['name']}({cast_primary['role']})、"
                f"{cast_secondary['name']}({cast_secondary['role']})共同行动，"
                "保持纪实新闻叙事、环境细节真实、镜头层次清晰。"
            )
            micro_scene_prompts: List[str] = []
            for micro_index in range(1, micro_scene_count + 1):
                micro_digest = sha256(f"{group_digest}|micro|{micro_index}".encode("utf-8")).hexdigest()[:6]
                micro_scene_prompts.append(
                    (
                        f"{major_scene_prompt}\n"
                        f"切换小场景{micro_index}，聚焦{decision_focus}，"
                        f"保留固定角色互动线索，变量代号{micro_digest}。"
                    )
                )

            groups.append(
                {
                    "group_index": group_index,
                    "major_scene_id": major_scene_id,
                    "major_scene_title": major_scene_title,
                    "major_scene_prompt": major_scene_prompt,
                    "decision_focus": decision_focus,
                    "mission": mission,
                    "cast": [cast_primary, cast_secondary],
                    "micro_scene_prompts": micro_scene_prompts,
                }
            )

        return {
            "storyline_id": storyline_id,
            "scene_session_id": scene_session_id,
            "seed": storyline_digest,
            "fixed_cast": [dict(item) for item in self._FIXED_CAST],
            "naming_rule": "sessionId_r{roundNo}_call_{sequence}",
            "scene_group_count": len(groups),
            "groups": groups,
        }

    def _resolve_major_scene_templates(self) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for index, item in enumerate(TRAINING_DEFAULT_SCENARIO_SEQUENCE or [], start=1):
            if not isinstance(item, dict):
                continue
            scenario_id = _normalize_optional_text(item.get("id")) or f"S{index}"
            title = _normalize_optional_text(item.get("title")) or f"主线场景{index}"
            normalized.append({"id": scenario_id, "title": title})

        if normalized:
            return normalized
        return [{"id": f"S{index}", "title": f"主线场景{index}"} for index in range(1, 7)]

    def _update_scene_generation_metadata(
        self,
        *,
        job_id: str,
        status: str,
        error_message: str | None,
        scene_storyline_script: Dict[str, Any] | None = None,
        scene_groups: List[Dict[str, Any]] | None = None,
        scene_generated_at: str | None = None,
        scene_generation_started_at: str | None = None,
    ) -> None:
        normalized_job_id = _normalize_text(job_id)
        if not normalized_job_id:
            return

        row = self._guard_repository_call(
            operation="get_preview_job",
            call=lambda: self.preview_job_repository.get_preview_job(normalized_job_id),
            details={"job_id": normalized_job_id},
        )
        if row is None:
            return

        request_payload = _normalize_payload_map(getattr(row, "request_payload", {}))
        request_payload["scene_generation_status"] = _normalize_scene_generation_status(
            status,
            default="pending",
        )
        request_payload["scene_generation_error"] = _normalize_optional_text(error_message)
        if scene_storyline_script is not None:
            request_payload["scene_storyline_script"] = dict(scene_storyline_script)
        if scene_groups is not None:
            request_payload["scene_groups"] = _normalize_payload_list(scene_groups)
        if scene_generated_at is not None:
            request_payload["scene_generated_at"] = _normalize_optional_text(scene_generated_at)
        if scene_generation_started_at is not None:
            request_payload["scene_generation_started_at"] = _normalize_optional_text(
                scene_generation_started_at
            )

        self._guard_repository_call(
            operation="update_preview_job",
            call=lambda: self.preview_job_repository.update_preview_job(
                normalized_job_id,
                {"request_payload": request_payload},
            ),
            details={
                "job_id": normalized_job_id,
                "scene_generation_status": request_payload["scene_generation_status"],
            },
        )

    def _execute_generation_with_timeout(self, request_payload: Dict[str, Any]) -> List[str]:
        future = self._provider_pool.submit(
            self.character_service.generate_character_image,
            request_payload,
            int(request_payload.get("character_id")),
            _normalize_optional_text(request_payload.get("user_id")),
            _normalize_optional_text(request_payload.get("image_type")) or "portrait",
            True,
            max(int(request_payload.get("group_count", 3) or 3), 1),
        )
        try:
            result = future.result(timeout=self.generation_timeout_seconds)
        except FuturesTimeoutError as exc:
            future.cancel()
            raise RuntimeError(
                "training preview generation timed out after "
                f"{self.generation_timeout_seconds:.1f} seconds"
            ) from exc
        return list(result or [])

    def _build_generation_payload(
        self,
        *,
        character_id: int,
        user_id: str | None,
        image_type: str | None,
        group_count: int,
        idempotency_key: str,
        generate_scene_groups: bool | None,
        scene_group_count: int | None,
        micro_scene_min: int | None,
        micro_scene_max: int | None,
    ) -> Dict[str, Any]:
        try:
            character = self.character_service.get_character(character_id)
        except CharacterNotFoundError as exc:
            raise TrainingCharacterPreviewCharacterNotFoundError(character_id=character_id) from exc

        if not isinstance(character, dict):
            raise TrainingCharacterPreviewCharacterNotFoundError(character_id=character_id)

        should_generate_scene_groups = (
            self.enable_scene_group_generation
            and self._scene_dispatcher is not None
            and _normalize_bool(generate_scene_groups, default=False)
        )
        effective_scene_group_count = _normalize_positive_int(
            scene_group_count,
            self.default_scene_group_count,
            minimum=1,
            maximum=6,
        )
        effective_micro_scene_min = _normalize_positive_int(
            micro_scene_min,
            self.micro_scene_min,
            minimum=1,
            maximum=3,
        )
        effective_micro_scene_max = _normalize_positive_int(
            micro_scene_max,
            self.micro_scene_max,
            minimum=effective_micro_scene_min,
            maximum=3,
        )

        request_payload: Dict[str, Any] = {
            "character_id": character_id,
            "name": _normalize_optional_text(character.get("name")),
            "gender": _normalize_optional_text(character.get("gender")),
            "age": character.get("age"),
            "identity": _normalize_optional_text(character.get("identity")),
            "identity_code": _normalize_optional_text(character.get("identity_code")),
            "appearance": _normalize_payload_map(character.get("appearance")),
            "personality": _normalize_payload_map(character.get("personality")),
            "background": _normalize_payload_map(character.get("background")),
            "user_id": _normalize_optional_text(user_id),
            "image_type": _normalize_optional_text(image_type) or "portrait",
            "group_count": max(int(group_count or 3), 1),
            "idempotency_key": _normalize_optional_text(idempotency_key),
            "generate_scene_groups": should_generate_scene_groups,
            "scene_group_count": effective_scene_group_count,
            "micro_scene_min": effective_micro_scene_min,
            "micro_scene_max": effective_micro_scene_max,
            "scene_generation_status": "pending" if should_generate_scene_groups else "skipped",
            "scene_generation_error": None,
            "scene_generation_started_at": None,
            "scene_generated_at": None,
            "scene_storyline_script": {},
            "scene_groups": [],
            "attempt_count": 0,
            "last_failed_at": None,
            "last_error_message": None,
            "last_retry_at": None,
        }
        return request_payload

    @staticmethod
    def _canonicalize_payload(payload: Dict[str, Any]) -> str:
        return json.dumps(dict(payload or {}), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _to_record(row: Any) -> TrainingCharacterPreviewJobRecord:
        created_at = getattr(row, "created_at", None) or datetime.utcnow()
        updated_at = getattr(row, "updated_at", None) or created_at
        request_payload = _normalize_payload_map(getattr(row, "request_payload", {}))
        scene_generation_requested = _normalize_bool(
            request_payload.get("generate_scene_groups"),
            default=False,
        )
        scene_status_default = "pending" if scene_generation_requested else "skipped"
        return TrainingCharacterPreviewJobRecord(
            job_id=str(getattr(row, "job_id", "") or ""),
            character_id=int(getattr(row, "character_id", 0) or 0),
            idempotency_key=str(getattr(row, "idempotency_key", "") or ""),
            status=str(getattr(row, "status", "pending") or "pending"),
            request_payload_canonical=str(getattr(row, "request_payload_canonical", "") or ""),
            image_urls=_normalize_image_urls(getattr(row, "image_urls", [])),
            scene_storyline_script=_normalize_payload_map(request_payload.get("scene_storyline_script")),
            scene_groups=_normalize_payload_list(request_payload.get("scene_groups")),
            scene_generation_status=_normalize_scene_generation_status(
                request_payload.get("scene_generation_status"),
                default=scene_status_default,
            ),
            scene_generation_error=_normalize_optional_text(request_payload.get("scene_generation_error")),
            scene_generated_at=_parse_iso_datetime(request_payload.get("scene_generated_at")),
            attempt_count=_normalize_non_negative_int(request_payload.get("attempt_count"), 0),
            last_failed_at=_parse_iso_datetime(request_payload.get("last_failed_at")),
            last_error_message=_normalize_optional_text(request_payload.get("last_error_message")),
            error_message=_normalize_optional_text(getattr(row, "error_message", None)),
            created_at=created_at,
            updated_at=updated_at,
        )
