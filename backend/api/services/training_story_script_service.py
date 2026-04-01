"""Training story script service.

Contract:
- GET paths must be read-only and stable.
- Explicit ensure is allowed via init flow / CLI / POST endpoint.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from training.exceptions import (
    TrainingSessionNotFoundError,
    TrainingStorageUnavailableError,
    TrainingStoryScriptNotFoundError,
)
from utils.logger import get_logger


logger = get_logger(__name__)


class TrainingStoryScriptService:
    def __init__(self, *, training_store: Any, training_service: Any, story_script_executor: Any = None):
        self.training_store = training_store
        self.training_service = training_service
        self.story_script_executor = story_script_executor

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
        if existing is not None and isinstance(getattr(existing, "payload", None), dict) and existing.payload:
            return self._to_response(existing)
        if existing is not None and str(getattr(existing, "status", "") or "").strip().lower() in {
            "pending",
            "running",
        }:
            # Only schedule on state boundary: pending can be scheduled; running should not be resubmitted.
            raw_status = str(getattr(existing, "status", "") or "").strip().lower()
            if self.story_script_executor is not None and raw_status == "pending":
                self.story_script_executor.submit_session(session_id)
            return self._to_response(existing)

        # Phase: mark pending (observable state), then schedule background generation.
        # Store layer provides idempotency by unique(session_id).
        pending_row = self.training_store.create_story_script(
            session_id=session_id,
            payload={},
            provider="auto",
            model="auto",
            major_scene_count=6,
            micro_scenes_per_gap=2,
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
            "major_scene_count": int(getattr(row, "major_scene_count", 6) or 6),
            "micro_scenes_per_gap": int(getattr(row, "micro_scenes_per_gap", 2) or 2),
            "status": normalized_status,
            "error_code": getattr(row, "error_code", None),
            "error_message": getattr(row, "error_message", None),
            "fallback_used": bool(getattr(row, "fallback_used", False)),
            "payload": dict(getattr(row, "payload", None) or {}),
            "created_at": created_at.isoformat() if created_at is not None else None,
            "updated_at": updated_at.isoformat() if updated_at is not None else None,
        }

