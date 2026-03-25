"""Training media task policy.

This policy owns task create-contract normalization so service/router layers can
stay thin and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any

from training.exceptions import TrainingMediaTaskInvalidError, TrainingMediaTaskUnsupportedError


SUPPORTED_MEDIA_TASK_TYPES = ("image", "tts", "text")


@dataclass(slots=True)
class NormalizedTrainingMediaTaskCreate:
    """Canonical media task creation payload passed into storage/services."""

    session_id: str
    round_no: int | None
    task_type: str
    payload: dict[str, Any]
    canonical_payload: str
    idempotency_key: str
    max_retries: int


class TrainingMediaTaskPolicy:
    """Validate and normalize training media task requests."""

    def __init__(self, supported_task_types: tuple[str, ...] = SUPPORTED_MEDIA_TASK_TYPES):
        normalized_supported = tuple(
            str(item).strip().lower()
            for item in supported_task_types
            if str(item).strip()
        )
        if not normalized_supported:
            raise ValueError("supported_task_types cannot be empty")
        self.supported_task_types = normalized_supported

    def normalize_create_request(
        self,
        *,
        session_id: str,
        round_no: int | None,
        task_type: str,
        payload: dict[str, Any],
        idempotency_key: str | None,
        max_retries: int = 0,
    ) -> NormalizedTrainingMediaTaskCreate:
        normalized_session_id = self._normalize_session_id(session_id)
        normalized_round_no = self._normalize_round_no(round_no)
        normalized_task_type = self._normalize_task_type(task_type)
        normalized_payload = self._normalize_payload(payload)
        canonical_payload = self._canonicalize_payload(normalized_payload)
        normalized_max_retries = self._normalize_max_retries(max_retries)

        normalized_idempotency_key = self._normalize_idempotency_key(idempotency_key)
        if normalized_idempotency_key is None:
            normalized_idempotency_key = self._generate_idempotency_key(
                session_id=normalized_session_id,
                round_no=normalized_round_no,
                task_type=normalized_task_type,
                canonical_payload=canonical_payload,
            )

        return NormalizedTrainingMediaTaskCreate(
            session_id=normalized_session_id,
            round_no=normalized_round_no,
            task_type=normalized_task_type,
            payload=normalized_payload,
            canonical_payload=canonical_payload,
            idempotency_key=normalized_idempotency_key,
            max_retries=normalized_max_retries,
        )

    def _normalize_session_id(self, session_id: str) -> str:
        normalized = str(session_id or "").strip()
        if not normalized:
            raise TrainingMediaTaskInvalidError(
                "training media session_id is required",
                details={"field": "session_id"},
            )
        return normalized

    def _normalize_round_no(self, round_no: int | None) -> int | None:
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

    def _normalize_task_type(self, task_type: str) -> str:
        normalized = str(task_type or "").strip().lower()
        if not normalized:
            raise TrainingMediaTaskInvalidError(
                "training media task_type is required",
                details={"field": "task_type"},
            )
        if normalized not in self.supported_task_types:
            raise TrainingMediaTaskUnsupportedError(
                task_type=normalized,
                supported_task_types=self.supported_task_types,
            )
        return normalized

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise TrainingMediaTaskInvalidError(
                "training media payload must be an object",
                details={"field": "payload"},
            )

        return self._normalize_json_value(payload, path="payload")

    def _normalize_max_retries(self, max_retries: int) -> int:
        try:
            normalized = int(max_retries)
        except (TypeError, ValueError) as exc:
            raise TrainingMediaTaskInvalidError(
                "training media max_retries must be an integer",
                details={"field": "max_retries", "value": max_retries},
            ) from exc

        if normalized < 0:
            raise TrainingMediaTaskInvalidError(
                "training media max_retries must be >= 0",
                details={"field": "max_retries", "value": normalized},
            )
        return normalized

    def _normalize_idempotency_key(self, idempotency_key: str | None) -> str | None:
        if idempotency_key is None:
            return None
        normalized = str(idempotency_key).strip()
        if not normalized:
            return None
        if len(normalized) > 128:
            raise TrainingMediaTaskInvalidError(
                "training media idempotency_key exceeds max length 128",
                details={"field": "idempotency_key"},
            )
        return normalized

    def _canonicalize_payload(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def _generate_idempotency_key(
        self,
        *,
        session_id: str,
        round_no: int | None,
        task_type: str,
        canonical_payload: str,
    ) -> str:
        source = f"{session_id}|{round_no}|{task_type}|{canonical_payload}"
        return sha256(source.encode("utf-8")).hexdigest()

    def _normalize_json_value(self, value: Any, *, path: str) -> Any:
        if isinstance(value, dict):
            normalized: dict[str, Any] = {}
            for key, child in value.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}"
                normalized[key_text] = self._normalize_json_value(child, path=child_path)
            return normalized

        if isinstance(value, list):
            return [
                self._normalize_json_value(item, path=f"{path}[{index}]")
                for index, item in enumerate(value)
            ]

        if isinstance(value, tuple):
            return [
                self._normalize_json_value(item, path=f"{path}[{index}]")
                for index, item in enumerate(value)
            ]

        if isinstance(value, bool) or value is None:
            return value

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            if not math.isfinite(value):
                raise TrainingMediaTaskInvalidError(
                    "training media payload contains non-finite float",
                    details={"field": path, "value": value},
                )
            return value

        if isinstance(value, str):
            return value

        raise TrainingMediaTaskInvalidError(
            "training media payload contains unsupported value type",
            details={
                "field": path,
                "type": type(value).__name__,
            },
        )
