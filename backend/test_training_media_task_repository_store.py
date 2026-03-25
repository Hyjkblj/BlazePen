"""Repository/store tests for training media task persistence."""

from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.training  # noqa: F401 - register ORM models
from models.character import Base
from training.training_repository import SqlAlchemyTrainingRepository
from training.training_store import DatabaseTrainingStore, TrainingMediaTaskRecord


class TrainingMediaTaskRepositoryStoreTestCase(unittest.TestCase):
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

        session = self.repository.create_training_session(
            user_id="media-user",
            character_id=None,
            training_mode="guided",
            k_state={},
            s_state={},
            session_meta={},
        )
        self.session_id = session.session_id

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_should_create_get_and_list_media_tasks(self):
        created = self.store.create_media_task(
            session_id=self.session_id,
            round_no=1,
            task_type="image",
            idempotency_key="media-key-1",
            request_payload={"prompt": "draw skyline"},
            max_retries=2,
        )

        self.assertIsInstance(created, TrainingMediaTaskRecord)
        self.assertEqual(created.status, "pending")
        self.assertEqual(created.task_type, "image")

        fetched = self.store.get_media_task(created.task_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.task_id, created.task_id)

        fetched_by_key = self.store.get_media_task_by_idempotency_key("media-key-1")
        self.assertIsNotNone(fetched_by_key)
        self.assertEqual(fetched_by_key.task_id, created.task_id)

        listed = self.store.list_media_tasks(session_id=self.session_id)
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].task_id, created.task_id)

        listed_with_round_filter = self.store.list_media_tasks(session_id=self.session_id, round_no=1)
        self.assertEqual(len(listed_with_round_filter), 1)
        self.assertEqual(listed_with_round_filter[0].task_id, created.task_id)

    def test_should_return_existing_task_when_idempotency_key_is_duplicated(self):
        first = self.store.create_media_task(
            session_id=self.session_id,
            round_no=1,
            task_type="tts",
            idempotency_key="dup-key-1",
            request_payload={"text": "hello"},
            max_retries=0,
        )
        second = self.store.create_media_task(
            session_id=self.session_id,
            round_no=1,
            task_type="tts",
            idempotency_key="dup-key-1",
            request_payload={"text": "hello"},
            max_retries=0,
        )

        self.assertEqual(first.task_id, second.task_id)
        listed = self.store.list_media_tasks(session_id=self.session_id)
        self.assertEqual(len(listed), 1)

    def test_should_support_claim_and_complete_transitions(self):
        created = self.store.create_media_task(
            session_id=self.session_id,
            round_no=None,
            task_type="text",
            idempotency_key="status-key-1",
            request_payload={"prompt": "summarize"},
            max_retries=1,
        )

        claimed = self.store.claim_media_task(created.task_id)
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.status, "running")
        self.assertIsNotNone(claimed.started_at)

        claimed_again = self.store.claim_media_task(created.task_id)
        self.assertIsNone(claimed_again)

        completed = self.store.complete_media_task(
            created.task_id,
            status="succeeded",
            result_payload={"text": "done"},
            error_payload=None,
        )
        self.assertIsNotNone(completed)
        self.assertEqual(completed.status, "succeeded")
        self.assertEqual(completed.result_payload, {"text": "done"})
        self.assertIsNotNone(completed.finished_at)

        fetched = self.store.get_media_task(created.task_id)
        self.assertEqual(fetched.status, "succeeded")
        self.assertEqual(fetched.result_payload, {"text": "done"})


if __name__ == "__main__":
    unittest.main()
