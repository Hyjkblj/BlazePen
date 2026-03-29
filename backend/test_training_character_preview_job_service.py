"""Tests for persistent training character preview job service."""

from __future__ import annotations

import threading
import time
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.training  # noqa: F401 - register ORM models
from api.services.training_character_preview_job_service import (
    TrainingCharacterPreviewJobConflictError,
    TrainingCharacterPreviewJobService,
)
from models.character import Base
from training.training_character_preview_job_repository import (
    SqlAlchemyTrainingCharacterPreviewJobRepository,
)


class _FakeCharacterService:
    def __init__(self):
        self.generated_calls = 0
        self.image_service = _FakeImageService()

    def get_character(self, character_id: int):
        return {
            "character_id": str(character_id),
            "name": "preview-stub",
            "gender": "female",
            "identity": "field-reporter",
            "appearance": {"keywords": ["stub"]},
            "personality": {"keywords": ["calm"]},
            "background": {"style": "stub-style"},
        }

    def generate_character_image(
        self,
        request_data,
        character_id=None,
        user_id=None,
        image_type="portrait",
        generate_group=True,
        group_count=3,
    ):
        self.generated_calls += 1
        return [f"/static/images/characters/preview_{character_id}_{self.generated_calls}.png"]


class _FakeImageService:
    def __init__(self):
        self.scene_generated_calls = 0

    def generate_scene_image(self, scene_data, scene_id=None, user_id=None):
        self.scene_generated_calls += 1
        normalized_scene_id = str(scene_id or scene_data.get("scene_id") or "scene")
        return f"/static/images/training/{normalized_scene_id}_{self.scene_generated_calls}.png"


class TrainingCharacterPreviewJobServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        self.repository = SqlAlchemyTrainingCharacterPreviewJobRepository(
            engine=self.engine,
            session_factory=self.SessionLocal,
        )
        self.character_service = _FakeCharacterService()
        self.service = TrainingCharacterPreviewJobService(
            character_service=self.character_service,
            preview_job_repository=self.repository,
            max_workers=1,
            generation_timeout_seconds=30,
            recovery_timeout_seconds=30,
        )

    def tearDown(self):
        self.service.shutdown()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _wait_terminal_status(self, job_id: str, timeout_seconds: float = 5.0) -> str:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            status = self.service.get_preview_job(job_id).status
            if status in {"succeeded", "failed"}:
                return status
            time.sleep(0.05)
        self.fail(f"preview job did not reach terminal status in {timeout_seconds}s: job_id={job_id}")

    def test_should_persist_preview_job_and_reuse_same_idempotency_scope(self):
        first = self.service.create_preview_job(
            character_id=101,
            idempotency_key="preview-key-101",
            group_count=3,
        )
        second = self.service.create_preview_job(
            character_id=101,
            idempotency_key="preview-key-101",
            group_count=3,
        )

        self.assertEqual(first.job_id, second.job_id)
        status = self._wait_terminal_status(first.job_id)
        self.assertEqual(status, "succeeded")

        restarted_service = TrainingCharacterPreviewJobService(
            character_service=self.character_service,
            preview_job_repository=self.repository,
            max_workers=1,
            generation_timeout_seconds=30,
            recovery_timeout_seconds=30,
        )
        try:
            persisted = restarted_service.get_preview_job(first.job_id)
            self.assertEqual(persisted.job_id, first.job_id)
            self.assertEqual(persisted.status, "succeeded")
            self.assertTrue(persisted.image_urls)
        finally:
            restarted_service.shutdown()

    def test_should_raise_conflict_when_idempotency_scope_changes(self):
        self.service.create_preview_job(
            character_id=101,
            idempotency_key="preview-conflict-key",
            group_count=3,
        )

        with self.assertRaises(TrainingCharacterPreviewJobConflictError):
            self.service.create_preview_job(
                character_id=202,
                idempotency_key="preview-conflict-key",
                group_count=3,
            )

    def test_should_retry_failed_job_with_same_idempotency_key(self):
        call_count = 0

        def flaky_generate(
            request_data,
            character_id=None,
            user_id=None,
            image_type="portrait",
            generate_group=True,
            group_count=3,
        ):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("preview generation failed for first attempt")
            return [f"/static/images/characters/retry_{character_id}_{call_count}.png"]

        self.character_service.generate_character_image = flaky_generate

        first_attempt = self.service.create_preview_job(
            character_id=101,
            idempotency_key="preview-retry-key",
            group_count=3,
        )
        self.assertEqual(self._wait_terminal_status(first_attempt.job_id), "failed")
        failed_record = self.service.get_preview_job(first_attempt.job_id)
        self.assertEqual(failed_record.attempt_count, 1)
        self.assertIsNotNone(failed_record.last_failed_at)
        self.assertIn("first attempt", failed_record.last_error_message or "")

        second_attempt = self.service.create_preview_job(
            character_id=101,
            idempotency_key="preview-retry-key",
            group_count=3,
        )
        self.assertEqual(first_attempt.job_id, second_attempt.job_id)
        self.assertEqual(self._wait_terminal_status(second_attempt.job_id), "succeeded")
        self.assertGreaterEqual(call_count, 2)
        recovered_record = self.service.get_preview_job(second_attempt.job_id)
        self.assertEqual(recovered_record.attempt_count, 1)
        self.assertIsNotNone(recovered_record.last_failed_at)
        self.assertIn("first attempt", recovered_record.last_error_message or "")

    def test_should_recover_pending_jobs_after_service_restart(self):
        payload = {
            "character_id": 301,
            "name": "preview-stub",
            "gender": "female",
            "identity": "field-reporter",
            "appearance": {"keywords": ["stub"]},
            "personality": {"keywords": ["calm"]},
            "background": {"style": "stub-style"},
            "user_id": None,
            "image_type": "portrait",
            "group_count": 3,
        }
        canonical = self.service._canonicalize_payload(payload)  # noqa: SLF001 - test helper
        pending_row = self.repository.create_preview_job(
            character_id=301,
            idempotency_key="preview-recovery-key",
            request_payload=payload,
            request_payload_canonical=canonical,
        )

        restarted_service = TrainingCharacterPreviewJobService(
            character_service=self.character_service,
            preview_job_repository=self.repository,
            max_workers=1,
            generation_timeout_seconds=30,
            recovery_timeout_seconds=30,
        )
        try:
            result = restarted_service.recover_pending_jobs()
            self.assertEqual(result.get("recovered"), 1)

            deadline = time.time() + 5
            while time.time() < deadline:
                row = restarted_service.get_preview_job(pending_row.job_id)
                if row.status in {"succeeded", "failed"}:
                    self.assertEqual(row.status, "succeeded")
                    self.assertTrue(row.image_urls)
                    return
                time.sleep(0.05)
            self.fail("recovered preview job did not complete in expected timeout")
        finally:
            restarted_service.shutdown()

    def test_claim_preview_job_should_be_atomic_under_concurrency(self):
        payload = {
            "character_id": 401,
            "name": "preview-stub",
            "gender": "female",
            "identity": "field-reporter",
            "appearance": {"keywords": ["stub"]},
            "personality": {"keywords": ["calm"]},
            "background": {"style": "stub-style"},
            "user_id": None,
            "image_type": "portrait",
            "group_count": 3,
        }
        canonical = self.service._canonicalize_payload(payload)  # noqa: SLF001 - test helper
        pending_row = self.repository.create_preview_job(
            character_id=401,
            idempotency_key="preview-claim-race-key",
            request_payload=payload,
            request_payload_canonical=canonical,
        )

        barrier = threading.Barrier(2)
        claims: list[bool] = []
        claim_lock = threading.Lock()

        def _claim_worker():
            barrier.wait(timeout=1.0)
            claimed = self.repository.claim_preview_job(pending_row.job_id)
            with claim_lock:
                claims.append(claimed is not None)

        first = threading.Thread(target=_claim_worker, name="preview-claim-worker-1")
        second = threading.Thread(target=_claim_worker, name="preview-claim-worker-2")
        first.start()
        second.start()
        first.join(timeout=2.0)
        second.join(timeout=2.0)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(len(claims), 2)
        self.assertEqual(sum(1 for item in claims if item), 1)

        persisted = self.repository.get_preview_job(pending_row.job_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(str(getattr(persisted, "status", "")), "running")
        self.assertIsNotNone(getattr(persisted, "started_at", None))

    def test_shutdown_wait_should_drain_inflight_preview_job_to_terminal_status(self):
        generation_started = threading.Event()
        allow_generation_finish = threading.Event()
        shutdown_completed = threading.Event()

        def blocked_generate(
            request_data,
            character_id=None,
            user_id=None,
            image_type="portrait",
            generate_group=True,
            group_count=3,
        ):
            generation_started.set()
            allow_generation_finish.wait(timeout=2.0)
            return [f"/static/images/characters/shutdown_{character_id}.png"]

        self.character_service.generate_character_image = blocked_generate

        created = self.service.create_preview_job(
            character_id=120,
            idempotency_key="preview-shutdown-drain-key",
            group_count=1,
        )

        self.assertTrue(
            generation_started.wait(timeout=1.0),
            "expected preview generation to start before shutdown",
        )

        def _shutdown_worker():
            self.service.shutdown(wait=True)
            shutdown_completed.set()

        shutdown_thread = threading.Thread(
            target=_shutdown_worker,
            name="training-preview-shutdown-test",
        )
        shutdown_thread.start()

        time.sleep(0.05)
        self.assertFalse(
            shutdown_completed.is_set(),
            "shutdown(wait=True) should block until in-flight preview generation completes",
        )

        allow_generation_finish.set()
        shutdown_thread.join(timeout=2.0)
        self.assertFalse(
            shutdown_thread.is_alive(),
            "shutdown(wait=True) should finish after in-flight generation drains",
        )
        self.assertTrue(shutdown_completed.is_set())

        persisted = self.repository.get_preview_job(created.job_id)
        self.assertIsNotNone(persisted)
        self.assertIn(str(getattr(persisted, "status", "")), {"succeeded", "failed"})

    def test_should_generate_scene_groups_asynchronously_when_enabled(self):
        scene_service = TrainingCharacterPreviewJobService(
            character_service=self.character_service,
            preview_job_repository=self.repository,
            max_workers=1,
            generation_timeout_seconds=30,
            recovery_timeout_seconds=30,
            enable_scene_group_generation=True,
            default_scene_group_count=2,
            scene_generation_timeout_seconds=30,
            micro_scene_min=2,
            micro_scene_max=2,
        )
        try:
            created = scene_service.create_preview_job(
                character_id=102,
                idempotency_key="preview-scene-key-102",
                group_count=3,
                generate_scene_groups=True,
                scene_group_count=2,
                micro_scene_min=2,
                micro_scene_max=2,
            )
            deadline = time.time() + 5.0
            while time.time() < deadline:
                status = scene_service.get_preview_job(created.job_id).status
                if status in {"succeeded", "failed"}:
                    self.assertEqual(status, "succeeded")
                    break
                time.sleep(0.05)
            else:
                self.fail("preview job did not reach terminal status in expected timeout")

            deadline = time.time() + 5.0
            while time.time() < deadline:
                row = scene_service.get_preview_job(created.job_id)
                if row.scene_generation_status in {"succeeded", "failed"}:
                    self.assertEqual(row.scene_generation_status, "succeeded")
                    self.assertEqual(len(row.scene_groups), 2)
                    self.assertTrue(all(group.get("major_scene_url") for group in row.scene_groups))
                    return
                time.sleep(0.05)
            self.fail("scene generation did not reach terminal status in expected timeout")
        finally:
            scene_service.shutdown()


if __name__ == "__main__":
    unittest.main()
