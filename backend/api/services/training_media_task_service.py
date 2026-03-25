"""Training media task application service."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any

from training.exceptions import (
    TrainingMediaTaskConflictError,
    TrainingMediaTaskInvalidError,
    TrainingMediaTaskNotFoundError,
    TrainingSessionNotFoundError,
)
from training.media_task_executor import TrainingMediaTaskExecutor
from training.media_task_policy import TrainingMediaTaskPolicy
from training.training_store import DatabaseTrainingStore, TrainingMediaTaskRecord, TrainingStoreProtocol
from utils.logger import get_logger


logger = get_logger(__name__)


class TrainingMediaTaskService:
    """Owns training-media task contract orchestration and idempotent writes."""

    def __init__(
        self,
        *,
        training_store: TrainingStoreProtocol | None = None,
        media_task_policy: TrainingMediaTaskPolicy | None = None,
        media_task_executor: TrainingMediaTaskExecutor | None = None,
    ):
        self.training_store = training_store or DatabaseTrainingStore()
        self.media_task_policy = media_task_policy or TrainingMediaTaskPolicy()
        self.media_task_executor = media_task_executor

    def create_task(
        self,
        *,
        session_id: str,
        round_no: int | None,
        task_type: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        max_retries: int = 0,
    ) -> dict[str, Any]:
        self._require_session_exists(session_id)

        normalized = self.media_task_policy.normalize_create_request(
            session_id=session_id,
            round_no=round_no,
            task_type=task_type,
            payload=payload,
            idempotency_key=idempotency_key,
            max_retries=max_retries,
        )

        existing = self.training_store.get_media_task_by_idempotency_key(normalized.idempotency_key)
        if existing is not None:
            self._assert_idempotent_task_scope(existing=existing, normalized_request=normalized)
            self._dispatch_task(existing.task_id)
            return self._to_task_response(existing)

        created = self.training_store.create_media_task(
            session_id=normalized.session_id,
            round_no=normalized.round_no,
            task_type=normalized.task_type,
            idempotency_key=normalized.idempotency_key,
            request_payload=normalized.payload,
            max_retries=normalized.max_retries,
        )
        self._assert_idempotent_task_scope(existing=created, normalized_request=normalized)
        self._dispatch_task(created.task_id)
        return self._to_task_response(created)

    def get_task(self, task_id: str) -> dict[str, Any]:
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            raise TrainingMediaTaskInvalidError(
                "training media task_id is required",
                details={"field": "task_id"},
            )

        row = self.training_store.get_media_task(normalized_task_id)
        if row is None:
            raise TrainingMediaTaskNotFoundError(task_id=normalized_task_id)
        return self._to_task_response(row)

    def list_tasks(self, *, session_id: str, round_no: int | None = None) -> dict[str, Any]:
        normalized_session_id = str(session_id or "").strip()
        if not normalized_session_id:
            raise TrainingMediaTaskInvalidError(
                "training media session_id is required",
                details={"field": "session_id"},
            )

        self._require_session_exists(normalized_session_id)
        normalized_round_no = self._normalize_optional_round_no(round_no)
        rows = self.training_store.list_media_tasks(
            session_id=normalized_session_id,
            round_no=normalized_round_no,
        )
        return {
            "session_id": normalized_session_id,
            "items": [self._to_task_response(item) for item in rows],
        }

    def _require_session_exists(self, session_id: str) -> None:
        if self.training_store.get_training_session(session_id) is None:
            raise TrainingSessionNotFoundError(session_id=session_id)

    def _normalize_optional_round_no(self, round_no: int | None) -> int | None:
        if round_no is None:
            return None

        try:
            normalized = int(round_no)
        except (TypeError, ValueError) as exc:
            raise TrainingMediaTaskInvalidError(
                "training media round_no must be an integer",
                details={"field": "round_no", "value": round_no},
            ) from exc

        if normalized < 0:
            raise TrainingMediaTaskInvalidError(
                "training media round_no must be >= 0",
                details={"field": "round_no", "value": normalized},
            )
        return normalized

    def _assert_idempotent_task_scope(
        self,
        *,
        existing: TrainingMediaTaskRecord,
        normalized_request: Any,
    ) -> None:
        if str(existing.session_id) != str(normalized_request.session_id):
            raise TrainingMediaTaskConflictError(
                "idempotency key conflicts with another training session",
                details={
                    "field": "idempotency_key",
                    "session_id": normalized_request.session_id,
                    "existing_session_id": existing.session_id,
                    "task_id": existing.task_id,
                },
            )

        existing_canonical_payload = self._canonicalize_payload(existing.request_payload or {})
        if (
            existing.round_no == normalized_request.round_no
            and str(existing.task_type) == str(normalized_request.task_type)
            and existing_canonical_payload == normalized_request.canonical_payload
        ):
            return

        raise TrainingMediaTaskConflictError(
            "idempotency key conflicts with a different media task request",
            details={
                "field": "idempotency_key",
                "session_id": normalized_request.session_id,
                "task_id": existing.task_id,
                "existing_scope": {
                    "round_no": existing.round_no,
                    "task_type": existing.task_type,
                    "canonical_payload": existing_canonical_payload,
                },
                "request_scope": {
                    "round_no": normalized_request.round_no,
                    "task_type": normalized_request.task_type,
                    "canonical_payload": normalized_request.canonical_payload,
                },
            },
        )

    @staticmethod
    def _canonicalize_payload(payload: dict[str, Any]) -> str:
        return json.dumps(dict(payload or {}), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def _to_task_response(self, row: TrainingMediaTaskRecord) -> dict[str, Any]:
        return {
            "task_id": row.task_id,
            "session_id": row.session_id,
            "round_no": row.round_no,
            "task_type": row.task_type,
            "status": row.status,
            "result": dict(row.result_payload or {}) if row.result_payload is not None else None,
            "error": dict(row.error_payload or {}) if row.error_payload is not None else None,
            "created_at": self._serialize_optional_datetime(row.created_at),
            "updated_at": self._serialize_optional_datetime(row.updated_at),
            "started_at": self._serialize_optional_datetime(row.started_at),
            "finished_at": self._serialize_optional_datetime(row.finished_at),
        }

    def _dispatch_task(self, task_id: str) -> None:
        if self.media_task_executor is None:
            return

        try:
            self.media_task_executor.submit_task(task_id)
        except Exception as exc:
            logger.warning("failed to dispatch training media task: task_id=%s error=%s", task_id, str(exc))

    @staticmethod
    def _serialize_optional_datetime(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None
