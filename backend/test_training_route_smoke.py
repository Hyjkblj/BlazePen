"""Training route smoke tests backed by SQLite.

This suite is the repository/router baseline for PR-BE-08A:
1. training router/service/query/repository should work end-to-end on a real SQLAlchemy DB
2. corrupted recovery facts should surface the same typed errors across read/write routes

It does not replace the explicit PostgreSQL release-chain smoke.
"""

from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.training  # noqa: F401 - register training models on Base.metadata
from api.dependencies import get_training_query_service, get_training_service
from api.middleware.error_handler import install_common_exception_handlers
from api.routers import training
from api.services.training_service import TrainingService
from test_training_service import _FakeEvaluator
from models.character import Base
from training.training_repository import SqlAlchemyTrainingRepository
from training.training_store import DatabaseTrainingStore


class TrainingRouteSqliteSmokeTestCase(unittest.TestCase):
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

        self.app = FastAPI()
        install_common_exception_handlers(self.app)
        self.app.include_router(training.router, prefix="/api")
        self.app.dependency_overrides[get_training_service] = lambda: self.training_service
        self.app.dependency_overrides[get_training_query_service] = lambda: self.training_service.query_service
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _init_session(self, user_id: str) -> tuple[str, str]:
        init_response = self.client.post(
            "/api/v1/training/init",
            json={"user_id": user_id, "training_mode": "self-paced"},
        )
        self.assertEqual(init_response.status_code, 200)
        init_payload = init_response.json()["data"]
        return init_payload["session_id"], init_payload["next_scenario"]["id"]

    def _corrupt_session_snapshots(self, session_id: str) -> None:
        session_row = self.repository.get_training_session(session_id)
        corrupted_meta = dict(session_row.session_meta or {})
        corrupted_meta.pop("scenario_payload_sequence", None)
        corrupted_meta.pop("scenario_payload_catalog", None)
        self.repository.update_training_session(
            session_id,
            {"session_meta": corrupted_meta},
        )

    def _assert_recovery_conflict(
        self,
        *,
        method: str,
        path: str,
        route_name: str,
        json_payload: dict | None = None,
    ) -> None:
        request_fn = getattr(self.client, method)
        response = request_fn(path, json=json_payload) if json_payload is not None else request_fn(path)

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_RECOVERY_STATE_CORRUPTED")
        self.assertEqual(payload["error"]["details"]["route"], route_name)
        self.assertEqual(payload["error"]["details"]["recovery_reason"], "scenario_snapshots_missing")

    def test_training_routes_should_complete_real_db_smoke_flow(self):
        init_response = self.client.post(
            "/api/v1/training/init",
            json={
                "user_id": "smoke-user",
                "training_mode": "self-paced",
                "player_profile": {
                    "name": "Lin Min",
                    "gender": "female",
                    "identity": "field-reporter",
                },
            },
        )
        self.assertEqual(init_response.status_code, 200)
        init_payload = init_response.json()["data"]
        session_id = init_payload["session_id"]
        scenario_id = init_payload["next_scenario"]["id"]
        self.assertNotIn("briefing", init_payload["next_scenario"])
        self.assertNotIn("briefing", init_payload["scenario_candidates"][0])

        next_response = self.client.post(
            "/api/v1/training/scenario/next",
            json={"session_id": session_id},
        )
        self.assertEqual(next_response.status_code, 200)
        next_payload = next_response.json()["data"]
        self.assertEqual(next_payload["session_id"], session_id)
        self.assertEqual(next_payload["round_no"], 1)
        self.assertEqual(next_payload["scenario"]["id"], scenario_id)
        self.assertNotIn("briefing", next_payload["scenario"])
        self.assertNotIn("briefing", next_payload["scenario_candidates"][0])

        submit_response = self.client.post(
            "/api/v1/training/round/submit",
            json={
                "session_id": session_id,
                "scenario_id": scenario_id,
                "user_input": "Verify the source first, then submit the report.",
            },
        )
        self.assertEqual(submit_response.status_code, 200)
        submit_payload = submit_response.json()["data"]
        self.assertEqual(submit_payload["session_id"], session_id)
        self.assertEqual(submit_payload["round_no"], 1)
        self.assertEqual(submit_payload["decision_context"]["selected_scenario_id"], scenario_id)
        self.assertEqual(submit_payload["media_tasks"], [])
        self.assertFalse(submit_payload["is_completed"])

        progress_response = self.client.get(f"/api/v1/training/progress/{session_id}")
        self.assertEqual(progress_response.status_code, 200)
        progress_payload = progress_response.json()["data"]
        self.assertEqual(progress_payload["session_id"], session_id)
        self.assertEqual(progress_payload["round_no"], 1)
        self.assertEqual(progress_payload["total_rounds"], 2)
        self.assertEqual(progress_payload["decision_context"]["selected_scenario_id"], scenario_id)
        self.assertIsInstance(progress_payload["consequence_events"], list)

        summary_response = self.client.get(f"/api/v1/training/sessions/{session_id}")
        self.assertEqual(summary_response.status_code, 200)
        summary_payload = summary_response.json()["data"]
        self.assertEqual(summary_payload["progress_anchor"]["progress_percent"], 50.0)
        self.assertEqual(summary_payload["progress_anchor"]["next_round_no"], 2)
        self.assertNotIn("briefing", summary_payload["resumable_scenario"])
        self.assertNotIn("briefing", summary_payload["scenario_candidates"][0])

        history_response = self.client.get(f"/api/v1/training/sessions/{session_id}/history")
        self.assertEqual(history_response.status_code, 200)
        history_payload = history_response.json()["data"]
        self.assertEqual(history_payload["history"][0]["scenario_id"], scenario_id)
        self.assertEqual(history_payload["progress_anchor"]["progress_percent"], 50.0)

        report_response = self.client.get(f"/api/v1/training/report/{session_id}")
        self.assertEqual(report_response.status_code, 200)
        report_payload = report_response.json()["data"]
        self.assertEqual(report_payload["history"][0]["scenario_id"], scenario_id)
        self.assertEqual(report_payload["history"][0]["decision_context"]["selected_scenario_id"], scenario_id)

        diagnostics_response = self.client.get(f"/api/v1/training/diagnostics/{session_id}")
        self.assertEqual(diagnostics_response.status_code, 200)
        diagnostics_payload = diagnostics_response.json()["data"]
        self.assertEqual(diagnostics_payload["session_id"], session_id)
        self.assertGreaterEqual(len(diagnostics_payload["audit_events"]), 1)
        self.assertGreaterEqual(len(diagnostics_payload["recommendation_logs"]), 1)
        self.assertGreaterEqual(len(diagnostics_payload["kt_observations"]), 1)

    def test_submit_round_should_persist_media_tasks_within_round_transaction(self):
        session_id, scenario_id = self._init_session(user_id="media-task-smoke-user")

        submit_response = self.client.post(
            "/api/v1/training/round/submit",
            json={
                "session_id": session_id,
                "scenario_id": scenario_id,
                "user_input": "Prepare text and image assets for this round.",
                "media_tasks": [
                    {
                        "task_type": "image",
                        "payload": {"prompt": "war newsroom night scene"},
                        "max_retries": 1,
                    },
                    {
                        "task_type": "tts",
                        "payload": {"text": "urgent bulletin draft", "voice": "female"},
                        "max_retries": 0,
                    },
                ],
            },
        )
        self.assertEqual(submit_response.status_code, 200)
        submit_payload = submit_response.json()["data"]
        self.assertEqual(submit_payload["session_id"], session_id)
        self.assertEqual(submit_payload["round_no"], 1)
        self.assertEqual(len(submit_payload["media_tasks"]), 2)
        self.assertEqual(
            sorted(item["task_type"] for item in submit_payload["media_tasks"]),
            ["image", "tts"],
        )
        self.assertTrue(all(item["status"] == "pending" for item in submit_payload["media_tasks"]))

        persisted_media_tasks = self.store.list_media_tasks(session_id=session_id, round_no=1)
        self.assertEqual(len(persisted_media_tasks), 2)
        self.assertEqual(
            sorted(item.task_type for item in persisted_media_tasks),
            ["image", "tts"],
        )
        self.assertTrue(all(item.status == "pending" for item in persisted_media_tasks))

        progress_response = self.client.get(f"/api/v1/training/progress/{session_id}")
        self.assertEqual(progress_response.status_code, 200)
        progress_payload = progress_response.json()["data"]
        self.assertEqual(progress_payload["session_id"], session_id)
        self.assertEqual(progress_payload["round_no"], 1)
        self.assertEqual(progress_payload["total_rounds"], 2)
        self.assertEqual(progress_payload["decision_context"]["selected_scenario_id"], scenario_id)
        self.assertIsInstance(progress_payload["consequence_events"], list)

        summary_response = self.client.get(f"/api/v1/training/sessions/{session_id}")
        self.assertEqual(summary_response.status_code, 200)
        summary_payload = summary_response.json()["data"]
        self.assertEqual(summary_payload["progress_anchor"]["progress_percent"], 50.0)
        self.assertEqual(summary_payload["progress_anchor"]["next_round_no"], 2)
        self.assertNotIn("briefing", summary_payload["resumable_scenario"])
        self.assertNotIn("briefing", summary_payload["scenario_candidates"][0])

        history_response = self.client.get(f"/api/v1/training/sessions/{session_id}/history")
        self.assertEqual(history_response.status_code, 200)
        history_payload = history_response.json()["data"]
        self.assertEqual(history_payload["history"][0]["scenario_id"], scenario_id)
        self.assertEqual(history_payload["progress_anchor"]["progress_percent"], 50.0)

        report_response = self.client.get(f"/api/v1/training/report/{session_id}")
        self.assertEqual(report_response.status_code, 200)
        report_payload = report_response.json()["data"]
        self.assertEqual(report_payload["history"][0]["scenario_id"], scenario_id)
        self.assertEqual(report_payload["history"][0]["decision_context"]["selected_scenario_id"], scenario_id)

        diagnostics_response = self.client.get(f"/api/v1/training/diagnostics/{session_id}")
        self.assertEqual(diagnostics_response.status_code, 200)
        diagnostics_payload = diagnostics_response.json()["data"]
        self.assertEqual(diagnostics_payload["session_id"], session_id)
        self.assertGreaterEqual(len(diagnostics_payload["audit_events"]), 1)
        self.assertGreaterEqual(len(diagnostics_payload["recommendation_logs"]), 1)
        self.assertGreaterEqual(len(diagnostics_payload["kt_observations"]), 1)

    def test_training_read_routes_should_surface_recovery_error_when_snapshots_are_missing(self):
        session_id, _ = self._init_session(user_id="broken-read-user")
        self._corrupt_session_snapshots(session_id)

        self._assert_recovery_conflict(
            method="get",
            path=f"/api/v1/training/sessions/{session_id}",
            route_name="training.session_summary",
        )
        self._assert_recovery_conflict(
            method="get",
            path=f"/api/v1/training/progress/{session_id}",
            route_name="training.progress",
        )
        self._assert_recovery_conflict(
            method="get",
            path=f"/api/v1/training/sessions/{session_id}/history",
            route_name="training.history",
        )
        self._assert_recovery_conflict(
            method="get",
            path=f"/api/v1/training/report/{session_id}",
            route_name="training.report",
        )
        self._assert_recovery_conflict(
            method="get",
            path=f"/api/v1/training/diagnostics/{session_id}",
            route_name="training.diagnostics",
        )

    def test_training_write_routes_should_surface_recovery_error_when_snapshots_are_missing(self):
        session_id, _ = self._init_session(user_id="broken-write-user")
        self._corrupt_session_snapshots(session_id)

        self._assert_recovery_conflict(
            method="post",
            path="/api/v1/training/scenario/next",
            route_name="training.next",
            json_payload={"session_id": session_id},
        )


if __name__ == "__main__":
    unittest.main()
