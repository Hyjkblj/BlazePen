"""Training standalone app tests."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.dependencies import (
    get_character_service,
    get_training_character_preview_job_service,
    get_training_media_task_service,
    get_training_service,
)
from api.training_app import app, warmup_training_media_runtime
from training.exceptions import TrainingStorageUnavailableError


class _FakeTrainingService:
    """Minimal training service stub for standalone routing checks."""

    def init_training(self, user_id, character_id=None, training_mode="guided", player_profile=None):
        return {
            "session_id": "standalone-s1",
            "status": "in_progress",
            "round_no": 0,
            "k_state": {"K1": 0.45},
            "s_state": {"credibility": 0.6},
            "player_profile": player_profile,
            "next_scenario": {"id": "S1", "title": "Training Scenario"},
            "scenario_candidates": [{"id": "S1", "title": "Training Scenario"}],
        }


class _FakeTrainingMediaTaskService:
    """Minimal media task service stub for standalone media-route checks."""

    def create_task(self, *, session_id, round_no, task_type, payload, idempotency_key=None, max_retries=0):
        return {
            "task_id": "task-standalone-1",
            "session_id": session_id,
            "round_no": round_no,
            "task_type": task_type,
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": "2026-03-25T12:00:00",
            "updated_at": "2026-03-25T12:00:00",
            "started_at": None,
            "finished_at": None,
        }

    def get_task(self, task_id):
        return {
            "task_id": task_id,
            "session_id": "standalone-s1",
            "round_no": 1,
            "task_type": "image",
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": "2026-03-25T12:00:00",
            "updated_at": "2026-03-25T12:00:00",
            "started_at": None,
            "finished_at": None,
        }

    def list_tasks(self, *, session_id, round_no=None):
        return {
            "session_id": session_id,
            "items": [
                {
                    "task_id": "task-standalone-1",
                    "session_id": session_id,
                    "round_no": round_no,
                    "task_type": "image",
                    "status": "pending",
                    "result": None,
                    "error": None,
                    "created_at": "2026-03-25T12:00:00",
                    "updated_at": "2026-03-25T12:00:00",
                    "started_at": None,
                    "finished_at": None,
                }
            ],
        }


class _FakeCharacterService:
    """Minimal character service stub for training portrait routes."""

    def generate_character_image_prompt(self, request_data, generate_group=True, group_count=3):
        return "stub prompt"

    def create_character(self, request_data):
        return 101

    def generate_character_image(
        self,
        request_data,
        character_id=None,
        user_id=None,
        image_type="portrait",
        generate_group=True,
        group_count=3,
    ):
        return ["/static/images/characters/training_stub_1.png"]

    def get_character(self, character_id):
        return {
            "character_id": str(character_id),
            "name": "Training Stub",
            "appearance": {"keywords": ["stub"]},
            "personality": {"keywords": ["calm"]},
            "background": {"style": "stub style"},
        }

    def get_character_images(self, character_id):
        return ["/static/images/characters/training_stub_1.png"]


class _FakePreviewJobRecord:
    def __init__(self, payload):
        self.payload = dict(payload)

    def to_dict(self):
        return dict(self.payload)


class _FakeTrainingCharacterPreviewJobService:
    def create_preview_job(
        self,
        *,
        character_id,
        idempotency_key,
        user_id=None,
        image_type="portrait",
        group_count=3,
        generate_scene_groups=False,
        scene_group_count=6,
        micro_scene_min=2,
        micro_scene_max=3,
    ):
        return _FakePreviewJobRecord(
            {
                "job_id": "preview-job-1",
                "character_id": int(character_id),
                "idempotency_key": idempotency_key,
                "status": "succeeded",
                "image_urls": ["/static/images/characters/training_stub_1.png"],
                "scene_storyline_script": {},
                "scene_groups": [],
                "scene_generation_status": "pending",
                "scene_generation_error": None,
                "scene_generated_at": None,
                "error_message": None,
                "created_at": "2026-03-26T10:00:00",
                "updated_at": "2026-03-26T10:00:00",
            }
        )

    def get_preview_job(self, job_id):
        return _FakePreviewJobRecord(
            {
                "job_id": job_id,
                "character_id": 101,
                "idempotency_key": "preview-key-1",
                "status": "succeeded",
                "image_urls": ["/static/images/characters/training_stub_1.png"],
                "scene_storyline_script": {},
                "scene_groups": [],
                "scene_generation_status": "pending",
                "scene_generation_error": None,
                "scene_generated_at": None,
                "error_message": None,
                "created_at": "2026-03-26T10:00:00",
                "updated_at": "2026-03-26T10:00:00",
            }
        )


class TrainingStandaloneAppTestCase(unittest.TestCase):
    """Ensure training-only app works without story-domain routes."""

    def setUp(self):
        self.database_manager_patcher = patch("api.app_factory.DatabaseManager")
        self.database_manager_patcher.start()
        app.state.training_media_runtime_state = {
            "ready": False,
            "degraded": False,
            "updated_at": None,
            "components": {
                "preview_warmup": {"status": "pending", "recovered": 0, "timed_out": 0, "error": None},
                "media_warmup": {"status": "pending", "recovered": 0, "timed_out": 0, "error": None},
            },
        }
        app.dependency_overrides[get_training_service] = lambda: _FakeTrainingService()
        app.dependency_overrides[get_training_media_task_service] = lambda: _FakeTrainingMediaTaskService()
        app.dependency_overrides[get_character_service] = lambda: _FakeCharacterService()
        app.dependency_overrides[get_training_character_preview_job_service] = (
            lambda: _FakeTrainingCharacterPreviewJobService()
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.database_manager_patcher.stop()

    def test_health_endpoint_should_return_training_service_scope(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "healthy")
        self.assertTrue(response.headers["X-Trace-Id"])

    def test_health_endpoint_should_echo_trace_id_header(self):
        response = self.client.get(
            "/health",
            headers={"X-Trace-Id": "training-trace-001"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Trace-Id"], "training-trace-001")

    def test_init_endpoint_should_work_on_training_only_app(self):
        response = self.client.post(
            "/api/v1/training/init",
            json={
                "user_id": "standalone-user",
                "training_mode": "guided",
                "player_profile": {
                    "name": "Li Min",
                    "gender": "female",
                    "identity": "field-reporter",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["session_id"], "standalone-s1")
        self.assertEqual(payload["data"]["player_profile"]["name"], "Li Min")
        self.assertEqual(payload["data"]["next_scenario"]["id"], "S1")

    def test_media_task_endpoint_should_work_on_training_only_app(self):
        response = self.client.post(
            "/api/v1/training/media/tasks",
            json={
                "session_id": "standalone-s1",
                "round_no": 1,
                "task_type": "image",
                "payload": {"prompt": "draw skyline"},
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["task_id"], "task-standalone-1")
        self.assertEqual(payload["data"]["status"], "pending")

    def test_training_character_create_endpoint_should_work_on_training_only_app(self):
        response = self.client.post(
            "/api/v1/training/characters/create",
            json={
                "identity_code": "correspondent-female",
                "identity": "field-reporter",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["character_id"], "101")
        self.assertEqual(payload["data"]["identity_code"], "correspondent-female")
        self.assertIn("image_urls", payload["data"])

    def test_training_identity_presets_endpoint_should_work_on_training_only_app(self):
        response = self.client.get("/api/v1/training/characters/identity-presets")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 200)
        self.assertGreater(len(payload.get("data", {}).get("presets", [])), 0)

    def test_training_character_preview_job_endpoints_should_work_on_training_only_app(self):
        create_response = self.client.post(
            "/api/v1/training/characters/preview-jobs",
            json={
                "character_id": 101,
                "idempotency_key": "preview-key-1",
                "group_count": 3,
            },
        )

        self.assertEqual(create_response.status_code, 200)
        create_payload = create_response.json()["data"]
        self.assertEqual(create_payload["job_id"], "preview-job-1")
        self.assertEqual(create_payload["status"], "succeeded")
        self.assertEqual(
            create_payload["image_urls"],
            ["/static/images/characters/training_stub_1.png"],
        )

        get_response = self.client.get("/api/v1/training/characters/preview-jobs/preview-job-1")
        self.assertEqual(get_response.status_code, 200)
        get_payload = get_response.json()["data"]
        self.assertEqual(get_payload["job_id"], "preview-job-1")
        self.assertEqual(get_payload["status"], "succeeded")

    def test_training_only_app_should_not_expose_story_routes(self):
        response = self.client.get(
            "/api/v1/game/sessions",
            params={"user_id": "story-user"},
        )

        self.assertEqual(response.status_code, 404)

    def test_warmup_should_allow_degraded_startup_when_preview_storage_unavailable(self):
        with patch(
            "api.training_app.warmup_training_character_preview_job_service",
            side_effect=TrainingStorageUnavailableError(
                message="training preview storage unavailable: operation=recover_pending_jobs",
                details={"operation": "recover_pending_jobs"},
            ),
        ):
            asyncio.run(warmup_training_media_runtime())

        runtime_state = app.state.training_media_runtime_state
        self.assertTrue(runtime_state.get("ready"))
        self.assertTrue(runtime_state.get("degraded"))
        self.assertEqual(
            runtime_state.get("components", {}).get("preview_warmup", {}).get("status"),
            "degraded",
        )

    def test_warmup_should_allow_degraded_startup_when_preview_warmup_raises_generic_exception(self):
        with patch(
            "api.training_app.warmup_training_character_preview_job_service",
            side_effect=RuntimeError("preview warmup crashed"),
        ):
            asyncio.run(warmup_training_media_runtime())

        runtime_state = app.state.training_media_runtime_state
        self.assertTrue(runtime_state.get("ready"))
        self.assertTrue(runtime_state.get("degraded"))
        self.assertEqual(
            runtime_state.get("components", {}).get("preview_warmup", {}).get("status"),
            "degraded",
        )

    def test_warmup_should_allow_degraded_startup_when_media_warmup_raises_generic_exception(self):
        with patch(
            "api.training_app.warmup_training_character_preview_job_service",
            return_value={"recovered": 0, "timed_out": 0},
        ), patch(
            "api.training_app.warmup_training_media_task_executor",
            side_effect=RuntimeError("media warmup crashed"),
        ):
            asyncio.run(warmup_training_media_runtime())

        runtime_state = app.state.training_media_runtime_state
        self.assertTrue(runtime_state.get("ready"))
        self.assertTrue(runtime_state.get("degraded"))
        self.assertEqual(
            runtime_state.get("components", {}).get("media_warmup", {}).get("status"),
            "degraded",
        )

    def test_readiness_endpoint_should_expose_media_runtime_state(self):
        app.state.training_media_runtime_state = {
            "ready": True,
            "degraded": True,
            "updated_at": "2026-03-29T00:00:00+00:00",
            "components": {
                "preview_warmup": {"status": "ready", "recovered": 1, "timed_out": 0, "error": None},
                "media_warmup": {"status": "degraded", "recovered": 0, "timed_out": 0, "error": "provider down"},
            },
        }

        response = self.client.get("/readiness")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("status"), "ready")
        self.assertTrue(payload.get("media_runtime", {}).get("degraded"))


if __name__ == "__main__":
    unittest.main()
