"""Opt-in PostgreSQL smoke for the training release chain.

This suite is intentionally gated behind ``BLAZEPEN_RUN_POSTGRES_SMOKE=1`` so
normal local/unit runs stay fast and do not mutate the developer's default DB.
When enabled, it validates the release-oriented chain:
1. ``scripts/init_db.py`` migrates a fresh PostgreSQL database
2. ``scripts/check_database_status.py`` sees the migrated training tables
3. training routes work end-to-end on the migrated PostgreSQL schema
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import models.training  # noqa: F401 - register training models for repository payloads
from api.dependencies import get_training_query_service, get_training_service
from api.middleware.error_handler import install_common_exception_handlers
from api.routers import training
from api.services.training_service import TrainingService
from backend.test_training_service import _FakeEvaluator
from training.training_repository import SqlAlchemyTrainingRepository
from training.training_store import DatabaseTrainingStore


RUN_POSTGRES_SMOKE = os.getenv("BLAZEPEN_RUN_POSTGRES_SMOKE") == "1"


def _quote_identifier(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


@unittest.skipUnless(
    RUN_POSTGRES_SMOKE,
    "requires BLAZEPEN_RUN_POSTGRES_SMOKE=1 and PostgreSQL test credentials",
)
class TrainingRoutePostgresqlSmokeTestCase(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.database_name = f"blazepen_training_smoke_{uuid.uuid4().hex[:8]}"
        self.environment = os.environ.copy()
        self.environment.setdefault("DB_HOST", "localhost")
        self.environment.setdefault("DB_PORT", "5432")
        self.environment.setdefault("DB_USER", "postgres")
        self.environment.setdefault("DB_PASSWORD", "")
        self.environment.update(
            {
                "ENV": "dev",
                "PYTHONIOENCODING": "utf-8",
                "DB_NAME": self.database_name,
            }
        )

        self.admin_url = self._build_database_url(database_name="postgres")
        self.database_url = self._build_database_url(database_name=self.database_name)
        self.addCleanup(self._cleanup_postgresql_database)

        self.init_db_output = self._run_script("scripts/init_db.py")
        self.status_after_init_output = self._run_script("scripts/check_database_status.py")

        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        self.addCleanup(self._dispose_engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
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
        self.addCleanup(self._cleanup_app)

    def _build_database_url(self, *, database_name: str) -> str:
        return (
            f"postgresql://{self.environment['DB_USER']}:{self.environment.get('DB_PASSWORD', '')}"
            f"@{self.environment['DB_HOST']}:{self.environment.get('DB_PORT', '5432')}/{database_name}"
        )

    def _run_script(self, relative_path: str) -> str:
        completed = subprocess.run(
            [sys.executable, "-X", "utf8", relative_path],
            cwd=self.project_root,
            env=self.environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            self.fail(
                f"{relative_path} failed with exit code {completed.returncode}\n"
                f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return completed.stdout

    def _cleanup_app(self) -> None:
        if hasattr(self, "app"):
            self.app.dependency_overrides.clear()

    def _dispose_engine(self) -> None:
        if hasattr(self, "engine"):
            self.engine.dispose()

    def _cleanup_postgresql_database(self) -> None:
        admin_engine = create_engine(
            self.admin_url,
            isolation_level="AUTOCOMMIT",
            pool_pre_ping=True,
        )
        try:
            with admin_engine.connect() as connection:
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) "
                        "FROM pg_stat_activity "
                        "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                    ),
                    {"database_name": self.database_name},
                )
                connection.execute(text(f"DROP DATABASE IF EXISTS {_quote_identifier(self.database_name)}"))
        finally:
            admin_engine.dispose()

    def test_postgresql_smoke_should_cover_migration_status_and_training_routes(self):
        self.assertIn("PostgreSQL", self.init_db_output)
        self.assertIn("training_sessions", self.init_db_output)
        self.assertIn("alembic_version", self.status_after_init_output)
        self.assertIn("training_sessions", self.status_after_init_output)

        init_response = self.client.post(
            "/api/v1/training/init",
            json={"user_id": "pg-smoke-user", "training_mode": "self-paced"},
        )
        self.assertEqual(init_response.status_code, 200)
        init_payload = init_response.json()["data"]
        session_id = init_payload["session_id"]
        scenario_id = init_payload["next_scenario"]["id"]

        next_response = self.client.post(
            "/api/v1/training/scenario/next",
            json={"session_id": session_id},
        )
        self.assertEqual(next_response.status_code, 200)

        submit_response = self.client.post(
            "/api/v1/training/round/submit",
            json={
                "session_id": session_id,
                "scenario_id": scenario_id,
                "user_input": "Verify the source before publishing.",
            },
        )
        self.assertEqual(submit_response.status_code, 200)

        progress_response = self.client.get(f"/api/v1/training/progress/{session_id}")
        self.assertEqual(progress_response.status_code, 200)
        self.assertEqual(progress_response.json()["data"]["round_no"], 1)

        report_response = self.client.get(f"/api/v1/training/report/{session_id}")
        self.assertEqual(report_response.status_code, 200)
        self.assertEqual(report_response.json()["data"]["history"][0]["scenario_id"], scenario_id)

        diagnostics_response = self.client.get(f"/api/v1/training/diagnostics/{session_id}")
        self.assertEqual(diagnostics_response.status_code, 200)
        self.assertGreaterEqual(len(diagnostics_response.json()["data"]["audit_events"]), 1)

        status_after_flow_output = self._run_script("scripts/check_database_status.py")
        self.assertIn("training_sessions", status_after_flow_output)
        self.assertIn("training_rounds", status_after_flow_output)
        self.assertIn("kt_observations", status_after_flow_output)


if __name__ == "__main__":
    unittest.main()
