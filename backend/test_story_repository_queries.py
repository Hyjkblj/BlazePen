from __future__ import annotations

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

        rows = self.repo.list_story_sessions_by_user("user-001", limit=10)

        self.assertEqual([row.thread_id for row in rows], ["thread-older", "thread-newer"])
        self.assertEqual(rows[0].current_scene_id, "library")
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
