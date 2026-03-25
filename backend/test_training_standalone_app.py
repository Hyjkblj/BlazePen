"""Training standalone app tests."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.dependencies import get_training_media_task_service, get_training_service
from api.training_app import app


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


class TrainingStandaloneAppTestCase(unittest.TestCase):
    """Ensure training-only app works without story-domain routes."""

    def setUp(self):
        self.database_manager_patcher = patch("api.app_factory.DatabaseManager")
        self.database_manager_patcher.start()
        app.dependency_overrides[get_training_service] = lambda: _FakeTrainingService()
        app.dependency_overrides[get_training_media_task_service] = lambda: _FakeTrainingMediaTaskService()
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

    def test_training_only_app_should_not_expose_story_routes(self):
        response = self.client.get(
            "/api/v1/game/sessions",
            params={"user_id": "story-user"},
        )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
