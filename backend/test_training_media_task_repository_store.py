"""Repository/store tests for training media task persistence."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.training  # noqa: F401 - register ORM models
from models.character import Base
from training.exceptions import TrainingStorageUnavailableError
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

    def test_claim_media_task_should_allow_only_one_concurrent_winner(self):
        temp_db_path = Path("backend/.tmp_claim_race.db").resolve()
        if temp_db_path.exists():
            temp_db_path.unlink()
        try:
            engine = create_engine(
                f"sqlite:///{temp_db_path.as_posix()}",
                connect_args={"check_same_thread": False},
            )
            session_local = sessionmaker(bind=engine, expire_on_commit=False)
            Base.metadata.create_all(engine)

            repository = SqlAlchemyTrainingRepository(
                engine=engine,
                session_factory=session_local,
            )
            store = DatabaseTrainingStore(repository)
            session = repository.create_training_session(
                user_id="claim-race-user",
                character_id=None,
                training_mode="guided",
                k_state={},
                s_state={},
                session_meta={},
            )
            created = store.create_media_task(
                session_id=session.session_id,
                round_no=1,
                task_type="image",
                idempotency_key="claim-race-key-1",
                request_payload={"prompt": "draw skyline"},
                max_retries=0,
            )
            barrier = threading.Barrier(3)

            def _claim_once():
                barrier.wait(timeout=2)
                return store.claim_media_task(created.task_id)

            with ThreadPoolExecutor(max_workers=2) as pool:
                future_a = pool.submit(_claim_once)
                future_b = pool.submit(_claim_once)
                barrier.wait(timeout=2)
                claim_results = [future_a.result(timeout=2), future_b.result(timeout=2)]

            claimed_records = [record for record in claim_results if record is not None]
            self.assertEqual(len(claimed_records), 1)
            self.assertEqual(claimed_records[0].status, "running")

            Base.metadata.drop_all(engine)
            engine.dispose()
        finally:
            if temp_db_path.exists():
                temp_db_path.unlink()

    def test_should_raise_storage_unavailable_when_media_table_is_missing(self):
        with self.engine.begin() as connection:
            connection.execute(text("DROP TABLE training_media_tasks"))

        with self.assertRaises(TrainingStorageUnavailableError) as create_error:
            self.store.create_media_task(
                session_id=self.session_id,
                round_no=1,
                task_type="image",
                idempotency_key="missing-table-create-key",
                request_payload={"prompt": "draw skyline"},
                max_retries=0,
            )
        self.assertEqual(
            str(create_error.exception),
            "training media task storage unavailable: training_media_tasks table is missing",
        )
        self.assertEqual(create_error.exception.details.get("operation"), "create_media_task")

        with self.assertRaises(TrainingStorageUnavailableError) as get_error:
            self.store.get_media_task("missing-task-id")
        self.assertEqual(
            str(get_error.exception),
            "training media task storage unavailable: training_media_tasks table is missing",
        )
        self.assertEqual(get_error.exception.details.get("operation"), "get_media_task")

        with self.assertRaises(TrainingStorageUnavailableError) as get_by_key_error:
            self.store.get_media_task_by_idempotency_key("missing-table-lookup-key")
        self.assertEqual(
            str(get_by_key_error.exception),
            "training media task storage unavailable: training_media_tasks table is missing",
        )
        self.assertEqual(
            get_by_key_error.exception.details.get("operation"),
            "get_media_task_by_idempotency_key",
        )

        with self.assertRaises(TrainingStorageUnavailableError) as list_error:
            self.store.list_media_tasks(session_id=self.session_id)
        self.assertEqual(
            str(list_error.exception),
            "training media task storage unavailable: training_media_tasks table is missing",
        )
        self.assertEqual(list_error.exception.details.get("operation"), "list_media_tasks")

        with self.assertRaises(TrainingStorageUnavailableError) as status_error:
            self.store.list_media_tasks_by_status(["pending", "running"])
        self.assertEqual(
            str(status_error.exception),
            "training media task storage unavailable: training_media_tasks table is missing",
        )
        self.assertEqual(status_error.exception.details.get("operation"), "list_media_tasks_by_status")

        with self.assertRaises(TrainingStorageUnavailableError) as claim_error:
            self.store.claim_media_task("missing-task-id")
        self.assertEqual(
            str(claim_error.exception),
            "training media task storage unavailable: training_media_tasks table is missing",
        )
        self.assertEqual(claim_error.exception.details.get("operation"), "claim_media_task")

        with self.assertRaises(TrainingStorageUnavailableError) as complete_error:
            self.store.complete_media_task("missing-task-id", status="failed")
        self.assertEqual(
            str(complete_error.exception),
            "training media task storage unavailable: training_media_tasks table is missing",
        )
        self.assertEqual(complete_error.exception.details.get("operation"), "complete_media_task")


if __name__ == "__main__":
    unittest.main()
