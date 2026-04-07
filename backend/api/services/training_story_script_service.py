"""Training story script service.

Contract:
- GET paths must be read-only and stable.
- Explicit ensure is allowed via init flow / CLI / POST endpoint.
"""

from __future__ import annotations

from typing import Any, Dict

from training.exceptions import (
    TrainingSessionNotFoundError,
    TrainingStorageUnavailableError,
    TrainingStoryScriptNotFoundError,
)
from utils.logger import get_logger


logger = get_logger(__name__)

DEFAULT_MAJOR_SCENE_COUNT = 6
DEFAULT_MICRO_SCENES_PER_GAP = 3


class TrainingStoryScriptService:
    def __init__(self, *, training_store: Any, training_service: Any, story_script_executor: Any = None):
        self.training_store = training_store
        self.training_service = training_service
        self.story_script_executor = story_script_executor

    def _resolve_story_script_scene_shape(self) -> tuple[int, int]:
        """Resolve script metadata defaults from runtime policies with safe fallbacks."""
        major_scene_count = DEFAULT_MAJOR_SCENE_COUNT
        micro_scenes_per_gap = DEFAULT_MICRO_SCENES_PER_GAP

        try:
            runtime_config = getattr(self.training_service, "runtime_config", None)
            scenario_config = getattr(runtime_config, "scenario", None)
            default_sequence = getattr(scenario_config, "default_sequence", None)
            if default_sequence is not None:
                major_scene_count = max(1, int(len(default_sequence)))
        except Exception:
            major_scene_count = DEFAULT_MAJOR_SCENE_COUNT

        try:
            storyline_policy = getattr(self.training_service, "session_storyline_policy", None)
            resolved_micro = int(
                getattr(storyline_policy, "micro_scene_max", DEFAULT_MICRO_SCENES_PER_GAP)
                or DEFAULT_MICRO_SCENES_PER_GAP
            )
            if resolved_micro > 0:
                micro_scenes_per_gap = resolved_micro
        except Exception:
            micro_scenes_per_gap = DEFAULT_MICRO_SCENES_PER_GAP

        return major_scene_count, micro_scenes_per_gap

    def get_story_script(self, session_id: str) -> Dict[str, Any]:
        session = self.training_store.get_training_session(session_id)
        if session is None:
            raise TrainingSessionNotFoundError(session_id=session_id)

        existing = self.training_store.get_story_script_by_session_id(session_id)
        if existing is None:
            # GET must be read-only. Missing script should be reported explicitly by contract.
            raise TrainingStoryScriptNotFoundError(session_id=session_id)
        return self._to_response(existing)

    def ensure_story_script(self, session_id: str) -> Dict[str, Any]:
        """Explicit ensure path (async trigger; returns pending/ready/failed)."""
        session = self.training_store.get_training_session(session_id)
        if session is None:
            raise TrainingSessionNotFoundError(session_id=session_id)

        existing = self.training_store.get_story_script_by_session_id(session_id)
        if existing is not None:
            payload = getattr(existing, "payload", None)
            has_payload = isinstance(payload, dict) and bool(payload)
            normalized_status = str(getattr(existing, "status", "") or "").strip().lower()

            if normalized_status in {"pending", "running"}:
                # Only schedule on state boundary: pending can be scheduled; running should not be resubmitted.
                if self.story_script_executor is not None and normalized_status == "pending":
                    self.story_script_executor.submit_session(session_id)
                return self._to_response(existing)

            if has_payload and normalized_status not in {"failed", "error"}:
                return self._to_response(existing)

            pending_row = self.training_store.update_story_script_by_session_id(
                session_id,
                {
                    "status": "pending",
                    "error_code": None,
                    "error_message": None,
                },
            )
            if pending_row is None:
                raise TrainingStorageUnavailableError(
                    message="training story script storage unavailable",
                    details={"operation": "ensure_story_script", "session_id": session_id},
                )

            # Only schedule on state boundary: pending can be scheduled; running should not be resubmitted.
            if self.story_script_executor is not None:
                self.story_script_executor.submit_session(session_id)
            return self._to_response(pending_row)

        # Phase: mark pending (observable state), then schedule background generation.
        # Store layer provides idempotency by unique(session_id).
        major_scene_count, micro_scenes_per_gap = self._resolve_story_script_scene_shape()
        pending_row = self.training_store.create_story_script(
            session_id=session_id,
            payload={},
            provider="auto",
            model="auto",
            major_scene_count=major_scene_count,
            micro_scenes_per_gap=micro_scenes_per_gap,
            source_script_id=None,
            status="pending",
            error_code=None,
            error_message=None,
            fallback_used=False,
        )
        if pending_row is None:
            raise TrainingStorageUnavailableError(
                message="training story script storage unavailable",
                details={"operation": "ensure_story_script", "session_id": session_id},
            )

        if self.story_script_executor is not None:
            self.story_script_executor.submit_session(session_id)
        return self._to_response(pending_row)

    @staticmethod
    def _to_response(row: Any) -> Dict[str, Any]:
        created_at = getattr(row, "created_at", None)
        updated_at = getattr(row, "updated_at", None)
        raw_status = str(getattr(row, "status", "") or "").strip().lower()
        # Backward compatibility: older rows used succeeded/running.
        if raw_status in {"succeeded", "success"}:
            normalized_status = "ready"
        elif raw_status in {"running", "pending"}:
            normalized_status = raw_status
        elif raw_status in {"failed", "error"}:
            normalized_status = "failed"
        else:
            normalized_status = raw_status or "ready"
        return {
            "session_id": str(getattr(row, "session_id", "") or ""),
            "script_id": str(getattr(row, "script_id", "") or ""),
            "source_script_id": getattr(row, "source_script_id", None),
            "provider": str(getattr(row, "provider", "") or "auto"),
            "model": str(getattr(row, "model", "") or "auto"),
            "major_scene_count": int(
                getattr(row, "major_scene_count", DEFAULT_MAJOR_SCENE_COUNT) or DEFAULT_MAJOR_SCENE_COUNT
            ),
            "micro_scenes_per_gap": int(
                getattr(row, "micro_scenes_per_gap", DEFAULT_MICRO_SCENES_PER_GAP) or DEFAULT_MICRO_SCENES_PER_GAP
            ),
            "status": normalized_status,
            "error_code": getattr(row, "error_code", None),
            "error_message": getattr(row, "error_message", None),
            "fallback_used": bool(getattr(row, "fallback_used", False)),
            "payload": dict(getattr(row, "payload", None) or {}),
            "created_at": created_at.isoformat() if created_at is not None else None,
            "updated_at": updated_at.isoformat() if updated_at is not None else None,
        }
