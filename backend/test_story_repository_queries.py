from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.story  # noqa: F401
from models.character import Base, Character
from story.story_repository import SqlAlchemyStoryRepository


class StoryRepositoryQueryTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        self.repo = SqlAlchemyStoryRepository(
            engine=self.engine,
            session_factory=self.SessionLocal,
        )
        with self.SessionLocal() as session:
            character = Character(
                name="story-query-character",
                gender="female",
                appearance="short hair",
                personality="calm",
            )
            session.add(character)
            session.commit()
            self.character_id = character.id

    def test_list_story_sessions_by_user_should_order_most_recent_first(self):
        self.repo.create_story_session(
            thread_id="thread-older",
            user_id="user-001",
            character_id=self.character_id,
            game_mode="solo",
            status="initialized",
            expires_at=None,
        )
        self.repo.create_story_session(
            thread_id="thread-newer",
            user_id="user-001",
            character_id=self.character_id,
            game_mode="solo",
            status="initialized",
            expires_at=None,
        )
        self.repo.create_story_session(
            thread_id="thread-other-user",
            user_id="user-002",
            character_id=self.character_id,
            game_mode="solo",
            status="initialized",
            expires_at=None,
        )

        self.repo.save_story_snapshot(
            thread_id="thread-older",
            round_no=1,
            snapshot_payload={"current_states": {"trust": 22}},
            response_payload={"scene": "library", "event_title": "Latest"},
            status="in_progress",
            current_scene_id="library",
            is_initialized=True,
            expires_at=None,
        )
        self.repo.update_story_session(
            "thread-older",
            {
                "last_active_at": datetime.utcnow() + timedelta(minutes=1),
            },
        )

        rows = self.repo.list_story_sessions_by_user("user-001", limit=10)

        self.assertEqual([row.thread_id for row in rows], ["thread-older", "thread-newer"])
        self.assertEqual(rows[0].current_scene_id, "library")
        self.assertEqual(len(rows), 2)

    def test_get_latest_story_snapshots_should_return_one_latest_snapshot_per_thread(self):
        for thread_id in ("thread-a", "thread-b", "thread-c"):
            self.repo.create_story_session(
                thread_id=thread_id,
                user_id="user-001",
                character_id=self.character_id,
                game_mode="solo",
                status="initialized",
                expires_at=None,
            )

        self.repo.save_story_snapshot(
            thread_id="thread-a",
            round_no=0,
            snapshot_payload={"current_states": {"trust": 10}},
            response_payload={"scene": "school", "event_title": "Opening"},
            status="in_progress",
            current_scene_id="school",
            is_initialized=True,
            expires_at=None,
        )
        self.repo.save_story_snapshot(
            thread_id="thread-a",
            round_no=2,
            snapshot_payload={"current_states": {"trust": 30}},
            response_payload={"scene": "library", "event_title": "Latest A"},
            status="in_progress",
            current_scene_id="library",
            is_initialized=True,
            expires_at=None,
        )
        self.repo.save_story_snapshot(
            thread_id="thread-b",
            round_no=1,
            snapshot_payload={"current_states": {"trust": 20}},
            response_payload={"scene": "rooftop", "event_title": "Latest B"},
            status="completed",
            current_scene_id="rooftop",
            is_initialized=True,
            expires_at=None,
        )

        rows = self.repo.get_latest_story_snapshots(["thread-a", "thread-b", "thread-c"])
        by_thread = {row.thread_id: row for row in rows}

        self.assertEqual(set(by_thread.keys()), {"thread-a", "thread-b"})
        self.assertEqual(by_thread["thread-a"].round_no, 2)
        self.assertEqual(by_thread["thread-a"].response_payload["event_title"], "Latest A")
        self.assertEqual(by_thread["thread-b"].round_no, 1)
        self.assertEqual(by_thread["thread-b"].response_payload["event_title"], "Latest B")

    def test_get_latest_story_snapshots_should_follow_session_latest_snapshot_round_no(self):
        for thread_id in ("thread-a", "thread-b"):
            self.repo.create_story_session(
                thread_id=thread_id,
                user_id="user-001",
                character_id=self.character_id,
                game_mode="solo",
                status="initialized",
                expires_at=None,
            )

        self.repo.save_story_snapshot(
            thread_id="thread-a",
            round_no=0,
            snapshot_payload={"current_states": {"trust": 10}},
            response_payload={"scene": "school", "event_title": "Opening A"},
            status="in_progress",
            current_scene_id="school",
            is_initialized=True,
            expires_at=None,
        )
        self.repo.save_story_snapshot(
            thread_id="thread-a",
            round_no=2,
            snapshot_payload={"current_states": {"trust": 30}},
            response_payload={"scene": "library", "event_title": "Latest A"},
            status="in_progress",
            current_scene_id="library",
            is_initialized=True,
            expires_at=None,
        )
        self.repo.save_story_snapshot(
            thread_id="thread-b",
            round_no=1,
            snapshot_payload={"current_states": {"trust": 20}},
            response_payload={"scene": "rooftop", "event_title": "Latest B"},
            status="completed",
            current_scene_id="rooftop",
            is_initialized=True,
            expires_at=None,
        )
        self.repo.update_story_session(
            "thread-a",
            {
                "latest_snapshot_round_no": 0,
            },
        )

        rows = self.repo.get_latest_story_snapshots(["thread-a", "thread-b"])
        by_thread = {row.thread_id: row for row in rows}

        self.assertEqual(set(by_thread.keys()), {"thread-a", "thread-b"})
        self.assertEqual(by_thread["thread-a"].round_no, 0)
        self.assertEqual(by_thread["thread-a"].response_payload["event_title"], "Opening A")
        self.assertEqual(by_thread["thread-b"].round_no, 1)

    def test_get_latest_story_snapshots_should_not_infer_latest_when_session_fact_is_missing(self):
        self.repo.create_story_session(
            thread_id="thread-missing-fact",
            user_id="user-001",
            character_id=self.character_id,
            game_mode="solo",
            status="initialized",
            expires_at=None,
        )
        self.repo.save_story_snapshot(
            thread_id="thread-missing-fact",
            round_no=1,
            snapshot_payload={"current_states": {"trust": 20}},
            response_payload={"scene": "rooftop", "event_title": "Only Snapshot"},
            status="in_progress",
            current_scene_id="rooftop",
            is_initialized=True,
            expires_at=None,
        )
        self.repo.update_story_session(
            "thread-missing-fact",
            {
                "latest_snapshot_round_no": None,
            },
        )

        rows = self.repo.get_latest_story_snapshots(["thread-missing-fact"])

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
