"""Contract tests for training story script ensure/recovery behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import unittest

from api.services.training_story_script_service import TrainingStoryScriptService


@dataclass
class _FakeStoryScriptRow:
    session_id: str
    script_id: str
    status: str
    payload: dict = field(default_factory=dict)
    provider: str = "auto"
    model: str = "auto"
    major_scene_count: int = 6
    micro_scenes_per_gap: int = 2
    source_script_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    fallback_used: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class _FakeSession:
    session_id: str


class _FakeTrainingStore:
    def __init__(self, *, existing_script: _FakeStoryScriptRow | None):
        self._existing_script = existing_script
        self.update_calls: list[dict] = []
        self.create_calls: int = 0

    def get_training_session(self, session_id: str):
        return _FakeSession(session_id=session_id)

    def get_story_script_by_session_id(self, session_id: str):
        return self._existing_script

    def update_story_script_by_session_id(self, session_id: str, updates: dict):
        self.update_calls.append({"session_id": session_id, "updates": dict(updates or {})})
        if self._existing_script is None:
            return None
        for key, value in (updates or {}).items():
            setattr(self._existing_script, key, value)
        self._existing_script.updated_at = datetime.utcnow()
        return self._existing_script

    def create_story_script(self, **kwargs):
        self.create_calls += 1
        self._existing_script = _FakeStoryScriptRow(
            session_id=str(kwargs.get("session_id") or ""),
            script_id="script-created",
            status=str(kwargs.get("status") or "pending"),
            payload=dict(kwargs.get("payload") or {}),
            error_code=kwargs.get("error_code"),
            error_message=kwargs.get("error_message"),
            fallback_used=bool(kwargs.get("fallback_used", False)),
        )
        return self._existing_script


class _FakeStoryScriptExecutor:
    def __init__(self):
        self.submitted_session_ids: list[str] = []

    def submit_session(self, session_id: str):
        self.submitted_session_ids.append(str(session_id))
        return True


class TrainingStoryScriptServiceContractTestCase(unittest.TestCase):
    def test_ensure_should_reset_failed_row_to_pending_and_submit_executor(self):
        existing = _FakeStoryScriptRow(
            session_id="training-session-1",
            script_id="script-1",
            status="failed",
            payload={},
            error_code="BACKGROUND_FAILED",
            error_message="provider timeout",
        )
        store = _FakeTrainingStore(existing_script=existing)
        executor = _FakeStoryScriptExecutor()
        service = TrainingStoryScriptService(
            training_store=store,
            training_service=object(),
            story_script_executor=executor,
        )

        result = service.ensure_story_script("training-session-1")

        self.assertEqual(result["status"], "pending")
        self.assertIsNone(result["error_code"])
        self.assertIsNone(result["error_message"])
        self.assertEqual(len(store.update_calls), 1)
        self.assertEqual(store.update_calls[0]["updates"]["status"], "pending")
        self.assertEqual(executor.submitted_session_ids, ["training-session-1"])

    def test_ensure_should_reset_ready_row_without_payload_to_pending(self):
        existing = _FakeStoryScriptRow(
            session_id="training-session-2",
            script_id="script-2",
            status="ready",
            payload={},
        )
        store = _FakeTrainingStore(existing_script=existing)
        executor = _FakeStoryScriptExecutor()
        service = TrainingStoryScriptService(
            training_store=store,
            training_service=object(),
            story_script_executor=executor,
        )

        result = service.ensure_story_script("training-session-2")

        self.assertEqual(result["status"], "pending")
        self.assertEqual(len(store.update_calls), 1)
        self.assertEqual(executor.submitted_session_ids, ["training-session-2"])

    def test_ensure_should_not_mutate_ready_row_when_payload_already_exists(self):
        existing = _FakeStoryScriptRow(
            session_id="training-session-3",
            script_id="script-3",
            status="ready",
            payload={"major_scenes": [{"id": "M1"}]},
        )
        store = _FakeTrainingStore(existing_script=existing)
        executor = _FakeStoryScriptExecutor()
        service = TrainingStoryScriptService(
            training_store=store,
            training_service=object(),
            story_script_executor=executor,
        )

        result = service.ensure_story_script("training-session-3")

        self.assertEqual(result["status"], "ready")
        self.assertEqual(len(store.update_calls), 0)
        self.assertEqual(store.create_calls, 0)
        self.assertEqual(executor.submitted_session_ids, [])


if __name__ == "__main__":
    unittest.main()
