"""Training media router smoke tests backed by SQLite."""

from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.training  # noqa: F401 - register training models
from api.dependencies import (
    get_training_media_task_service,
    get_training_query_service,
    get_training_service,
)
from api.middleware.error_handler import install_common_exception_handlers
from api.routers import training, training_media
from api.services.training_media_task_service import TrainingMediaTaskService
from api.services.training_service import TrainingService
from backend.test_training_service import _FakeEvaluator
from models.character import Base
from training.training_repository import SqlAlchemyTrainingRepository
from training.training_store import DatabaseTrainingStore


class TrainingMediaRouteSqliteSmokeTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.repository = SqlAlchemyTrainingRepository(
            engine=self.engine,
            session_factory=self.SessionLocal,
        )
        self.store = DatabaseTrainingStore(self.repository)

        self.training_service = TrainingService(
            training_store=self.store,
            evaluator=_FakeEvaluator(),
            scenario_sequence=[
                {"id": "S1", "title": "Intro"},
                {"id": "S2", "title": "Follow Up"},
            ],
        )
        self.media_service = TrainingMediaTaskService(training_store=self.store)

        self.app = FastAPI()
        install_common_exception_handlers(self.app)
        self.app.include_router(training.router, prefix="/api")
        self.app.include_router(training_media.router, prefix="/api")
        self.app.dependency_overrides[get_training_service] = lambda: self.training_service
        self.app.dependency_overrides[get_training_query_service] = lambda: self.training_service.query_service
        self.app.dependency_overrides[get_training_media_task_service] = lambda: self.media_service
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _init_session(self) -> str:
        response = self.client.post(
            "/api/v1/training/init",
            json={"user_id": "media-smoke-user", "training_mode": "self-paced"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]["session_id"]

    def test_media_task_routes_should_support_create_get_list_and_idempotency(self):
        session_id = self._init_session()

        create_response = self.client.post(
            "/api/v1/training/media/tasks",
            json={
                "session_id": session_id,
                "round_no": 1,
                "task_type": "image",
                "payload": {
                    "prompt": "draw city skyline",
                    "seed": 7,
                },
            },
        )
        self.assertEqual(create_response.status_code, 200)
        first_task = create_response.json()["data"]
        self.assertEqual(first_task["status"], "pending")
        self.assertEqual(first_task["session_id"], session_id)

        duplicate_response = self.client.post(
            "/api/v1/training/media/tasks",
            json={
                "session_id": session_id,
                "round_no": 1,
                "task_type": "image",
                "payload": {
                    "seed": 7,
                    "prompt": "draw city skyline",
                },
            },
        )
        self.assertEqual(duplicate_response.status_code, 200)
        duplicate_task = duplicate_response.json()["data"]
        self.assertEqual(duplicate_task["task_id"], first_task["task_id"])

        get_response = self.client.get(f"/api/v1/training/media/tasks/{first_task['task_id']}")
        self.assertEqual(get_response.status_code, 200)
        fetched_task = get_response.json()["data"]
        self.assertEqual(fetched_task["task_id"], first_task["task_id"])

        list_response = self.client.get(f"/api/v1/training/media/sessions/{session_id}/tasks")
        self.assertEqual(list_response.status_code, 200)
        listed_payload = list_response.json()["data"]
        self.assertEqual(listed_payload["session_id"], session_id)
        self.assertEqual(len(listed_payload["items"]), 1)
        self.assertEqual(listed_payload["items"][0]["task_id"], first_task["task_id"])

    def test_media_task_routes_should_return_session_not_found_for_unknown_session(self):
        response = self.client.post(
            "/api/v1/training/media/tasks",
            json={
                "session_id": "missing-session",
                "round_no": 1,
                "task_type": "text",
                "payload": {"prompt": "hello"},
            },
        )

        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_NOT_FOUND")
        self.assertEqual(payload["error"]["details"]["route"], "training.media.create_task")

    def test_media_task_routes_should_return_conflict_when_idempotency_scope_changes(self):
        session_id = self._init_session()
        idempotency_key = "manual-idempotency-key-1"

        first_response = self.client.post(
            "/api/v1/training/media/tasks",
            json={
                "session_id": session_id,
                "round_no": 1,
                "task_type": "image",
                "idempotency_key": idempotency_key,
                "payload": {
                    "prompt": "draw city skyline",
                    "seed": 7,
                },
            },
        )
        self.assertEqual(first_response.status_code, 200)

        conflict_response = self.client.post(
            "/api/v1/training/media/tasks",
            json={
                "session_id": session_id,
                "round_no": 2,
                "task_type": "image",
                "idempotency_key": idempotency_key,
                "payload": {
                    "prompt": "draw city skyline",
                    "seed": 7,
                },
            },
        )
        self.assertEqual(conflict_response.status_code, 409)
        conflict_payload = conflict_response.json()
        self.assertEqual(conflict_payload["error"]["code"], "TRAINING_MEDIA_TASK_CONFLICT")
        self.assertEqual(conflict_payload["error"]["details"]["route"], "training.media.create_task")

    def test_media_task_create_should_keep_single_image_contract_without_explicit_scene_series_flag(self):
        session_id = self._init_session()

        create_response = self.client.post(
            "/api/v1/training/media/tasks",
            json={
                "session_id": session_id,
                "round_no": 1,
                "task_type": "image",
                "payload": {
                    "prompt": "draw city skyline",
                    "image_type": "scene",
                    "scenario_id": "S1",
                },
            },
        )
        self.assertEqual(create_response.status_code, 200)
        task = create_response.json()["data"]
        self.assertEqual(task["status"], "pending")

        get_response = self.client.get(f"/api/v1/training/media/tasks/{task['task_id']}")
        self.assertEqual(get_response.status_code, 200)
        fetched = get_response.json()["data"]
        persisted = self.store.get_media_task(fetched["task_id"])
        request_payload = dict(getattr(persisted, "request_payload", {}) or {})
        self.assertEqual(request_payload.get("scenario_id"), "S1")
        self.assertNotIn("generate_storyline_series", request_payload)

    def test_media_task_list_should_return_storage_unavailable_when_media_table_is_missing(self):
        session_id = self._init_session()

        with self.engine.begin() as connection:
            connection.execute(text("DROP TABLE training_media_tasks"))

        response = self.client.get(f"/api/v1/training/media/sessions/{session_id}/tasks")
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "TRAINING_STORAGE_UNAVAILABLE")
        self.assertEqual(payload["error"]["details"]["route"], "training.media.list_tasks")
        self.assertEqual(payload["error"]["details"]["session_id"], session_id)

    def test_media_task_create_should_return_storage_unavailable_when_media_table_is_missing(self):
        session_id = self._init_session()

        with self.engine.begin() as connection:
            connection.execute(text("DROP TABLE training_media_tasks"))

        response = self.client.post(
            "/api/v1/training/media/tasks",
            json={
                "session_id": session_id,
                "round_no": 1,
                "task_type": "image",
                "payload": {"prompt": "draw skyline"},
            },
        )
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "TRAINING_STORAGE_UNAVAILABLE")
        self.assertEqual(payload["error"]["details"]["route"], "training.media.create_task")
        self.assertEqual(payload["error"]["details"]["session_id"], session_id)


if __name__ == "__main__":
    unittest.main()
