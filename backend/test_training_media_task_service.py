"""Unit tests for training media task service idempotency scope handling."""

from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.training  # noqa: F401 - register ORM models
from api.services.training_media_task_service import TrainingMediaTaskService
from models.character import Base
from training.exceptions import TrainingMediaTaskConflictError
from training.training_repository import SqlAlchemyTrainingRepository
from training.training_store import DatabaseTrainingStore


class TrainingMediaTaskServiceTestCase(unittest.TestCase):
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
        self.service = TrainingMediaTaskService(training_store=self.store)

        session = self.repository.create_training_session(
            user_id="media-service-user",
            training_mode="guided",
            k_state={},
            s_state={},
            session_meta={},
        )
        self.session_id = session.session_id

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_should_reuse_task_when_idempotency_scope_is_identical(self):
        idempotency_key = "service-idempotency-identical-1"

        first = self.service.create_task(
            session_id=self.session_id,
            round_no=1,
            task_type="image",
            payload={"prompt": "draw skyline", "seed": 7},
            idempotency_key=idempotency_key,
            max_retries=0,
        )
        duplicate = self.service.create_task(
            session_id=self.session_id,
            round_no=1,
            task_type="image",
            payload={"seed": 7, "prompt": "draw skyline"},
            idempotency_key=idempotency_key,
            max_retries=0,
        )

        self.assertEqual(first["task_id"], duplicate["task_id"])

    def test_should_raise_conflict_when_idempotency_scope_changes(self):
        idempotency_key = "service-idempotency-conflict-1"
        self.service.create_task(
            session_id=self.session_id,
            round_no=1,
            task_type="image",
            payload={"prompt": "draw skyline", "seed": 7},
            idempotency_key=idempotency_key,
            max_retries=0,
        )

        with self.assertRaises(TrainingMediaTaskConflictError):
            self.service.create_task(
                session_id=self.session_id,
                round_no=2,
                task_type="image",
                payload={"prompt": "draw skyline", "seed": 7},
                idempotency_key=idempotency_key,
                max_retries=0,
            )


if __name__ == "__main__":
    unittest.main()
