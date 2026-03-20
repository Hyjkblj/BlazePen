"""Story persistence regression tests for PR-03."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.story  # noqa: F401
from models.character import Base, Character
from story.exceptions import DuplicateStoryRoundSubmissionError
from story.story_repository import SqlAlchemyStoryRepository


class _FakeVectorDatabase:
    def __init__(self, *args, **kwargs):
        pass


class _FakeEventGenerator:
    def __init__(self, *args, **kwargs):
        pass


class _FakeStoryEngine:
    def __init__(self, *args, **kwargs):
        self.current_event_count = 0
        self.current_event = None
        self.dialogue_history = []
        self.current_scene = "classroom"
        self.previous_event_contexts = []


class StoryRepositoryTestCase(unittest.TestCase):
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
                name="测试角色",
                gender="female",
                appearance="short hair",
                personality="calm",
            )
            session.add(character)
            session.commit()
            self.character_id = character.id

    def test_save_story_round_artifacts_should_advance_snapshot_and_session(self):
        self.repo.create_story_session(
            thread_id="thread-001",
            user_id="user-001",
            character_id=self.character_id,
            game_mode="solo",
            status="initialized",
            expires_at=None,
        )
        self.repo.save_story_snapshot(
            thread_id="thread-001",
            round_no=0,
            snapshot_payload={"current_states": {"trust": 10}},
            response_payload={"event_title": "初遇", "scene": "school"},
            status="in_progress",
            current_scene_id="school",
            is_initialized=True,
            expires_at=None,
        )

        round_row = self.repo.save_story_round_artifacts(
            thread_id="thread-001",
            round_no=1,
            input_kind="option",
            user_input_raw="",
            selected_option_index=0,
            request_payload={"option_id": 0},
            response_payload={"event_title": "回合1", "scene": "library"},
            state_before={"trust": 10},
            state_after={"trust": 25},
            snapshot_payload={"current_states": {"trust": 25}},
            status="in_progress",
            current_scene_id="library",
            expires_at=None,
        )

        session_row = self.repo.get_story_session("thread-001")
        snapshot_row = self.repo.get_latest_story_snapshot("thread-001")

        self.assertEqual(round_row.round_no, 1)
        self.assertEqual(session_row.current_round_no, 1)
        self.assertEqual(session_row.current_scene_id, "library")
        self.assertEqual(session_row.latest_snapshot_round_no, 1)
        self.assertEqual(snapshot_row.round_no, 1)
        self.assertEqual(snapshot_row.current_scene_id, "library")
        self.assertEqual(snapshot_row.response_payload["event_title"], "回合1")

    def test_duplicate_story_round_should_raise_domain_error(self):
        self.repo.create_story_session(
            thread_id="thread-dup",
            user_id="user-001",
            character_id=self.character_id,
            game_mode="solo",
            status="initialized",
            expires_at=None,
        )

        payload = dict(
            thread_id="thread-dup",
            round_no=1,
            input_kind="option",
            user_input_raw="",
            selected_option_index=0,
            request_payload={"option_id": 0},
            response_payload={"event_title": "回合1", "scene": "school_gate"},
            state_before={"trust": 0},
            state_after={"trust": 15},
            snapshot_payload={"current_states": {"trust": 15}},
            status="in_progress",
            current_scene_id="school_gate",
            expires_at=None,
        )
        self.repo.save_story_round_artifacts(**payload)

        with self.assertRaises(DuplicateStoryRoundSubmissionError):
            self.repo.save_story_round_artifacts(**payload)

    def test_get_latest_story_snapshot_should_follow_session_fact_source(self):
        self.repo.create_story_session(
            thread_id="thread-latest",
            user_id="user-001",
            character_id=self.character_id,
            game_mode="solo",
            status="initialized",
            expires_at=None,
        )
        self.repo.save_story_snapshot(
            thread_id="thread-latest",
            round_no=0,
            snapshot_payload={"current_states": {"trust": 5}},
            response_payload={"event_title": "Opening", "scene": "school"},
            status="in_progress",
            current_scene_id="school",
            is_initialized=True,
            expires_at=None,
        )
        self.repo.save_story_snapshot(
            thread_id="thread-latest",
            round_no=2,
            snapshot_payload={"current_states": {"trust": 25}},
            response_payload={"event_title": "Latest", "scene": "library"},
            status="in_progress",
            current_scene_id="library",
            is_initialized=True,
            expires_at=None,
        )
        self.repo.update_story_session(
            "thread-latest",
            {
                "latest_snapshot_round_no": 0,
            },
        )

        snapshot_row = self.repo.get_latest_story_snapshot("thread-latest")

        self.assertIsNotNone(snapshot_row)
        self.assertEqual(snapshot_row.round_no, 0)
        self.assertEqual(snapshot_row.response_payload["event_title"], "Opening")

    @patch("api.services.game_session.VectorDatabase", _FakeVectorDatabase)
    @patch("api.services.game_session.EventGenerator", _FakeEventGenerator)
    @patch("api.services.game_session.StoryEngine", _FakeStoryEngine)
    def test_game_session_snapshot_should_roundtrip_runtime_state(self):
        from api.services.game_session import GameSession

        session = GameSession(
            thread_id="thread-snapshot",
            user_id="user-001",
            character_id=self.character_id,
            game_mode="solo",
            initial_state_payload={"trust": 22, "emotion": 68},
        )
        session.is_initialized = True
        session.current_dialogue_round = {"player_options": [{"id": 1, "text": "继续"}]}
        session.story_engine.current_event_count = 2
        session.story_engine.current_event = {"title": "图书馆事件", "scene": "library"}
        session.story_engine.dialogue_history = [
            {"type": "character", "content": "你好"},
            {"type": "player", "content": "继续"},
        ]
        session.story_engine.current_scene = "library"
        session.story_engine.previous_event_contexts = ["在图书馆见面"]

        snapshot = session.build_snapshot_payload(
            status="in_progress",
            round_no=1,
            last_response={"event_title": "图书馆事件"},
        )

        restored = GameSession(
            thread_id="thread-snapshot",
            user_id="user-001",
            character_id=self.character_id,
            game_mode="solo",
        )
        restored.restore_from_snapshot(snapshot)

        self.assertTrue(restored.is_initialized)
        self.assertEqual(restored.story_engine.current_event_count, 2)
        self.assertEqual(restored.story_engine.current_scene, "library")
        self.assertEqual(restored.story_engine.current_event["title"], "图书馆事件")
        self.assertEqual(restored.story_engine.dialogue_history[1]["content"], "继续")
        self.assertEqual(restored.current_dialogue_round["player_options"][0]["text"], "继续")
        self.assertEqual(restored.db_manager.get_character_states(self.character_id).trust, 22.0)


if __name__ == "__main__":
    unittest.main()
