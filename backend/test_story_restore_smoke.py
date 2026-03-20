from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.story  # noqa: F401
from api.dependencies import get_game_service
from api.routers import game
from api.services.game_service import GameService
from api.services.game_session import GameSessionManager
from models.character import Base, Character
from story.story_asset_service import StoryAssetService
from story.story_ending_service import StoryEndingService
from story.story_repository import SqlAlchemyStoryRepository
from story.story_session_service import StorySessionService
from story.story_store import DatabaseStoryStore


def _make_states(**overrides):
    payload = {
        "favorability": 10.0,
        "trust": 20.0,
        "hostility": 5.0,
        "dependence": 15.0,
        "emotion": 60.0,
        "stress": 10.0,
        "anxiety": 8.0,
        "happiness": 55.0,
        "sadness": 6.0,
        "confidence": 50.0,
        "initiative": 40.0,
        "caution": 45.0,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class _FakeDatabaseManager:
    def __init__(self, *args, **kwargs):
        pass

    def get_character_states(self, character_id: int):
        return _make_states()

    def get_character(self, character_id: int):
        return SimpleNamespace(
            id=character_id,
            name="测试角色",
            gender="female",
            appearance="short hair",
            personality="calm",
        )

    def get_character_attributes(self, character_id: int):
        return None


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
        self.current_scene = None
        self.previous_event_contexts = []
        self._game_finished = False

    def is_game_finished(self):
        return self._game_finished

    def get_ending_event(self, character_id: int):
        self._game_finished = True
        return {
            "title": "结局",
            "story_background": "结局背景",
            "scene": "ending",
            "ending_type": "good_ending",
        }

    def get_next_dialogue_round(self, character_id: int):
        return {
            "character_dialogue": "我们终于走到了这里。",
            "player_options": [],
        }

    def record_character_dialogue(self, dialogue: str):
        self.dialogue_history.append({"type": "character", "content": dialogue})


class _ReadySnapshotAssetService(StoryAssetService):
    def resolve_scene_image_url(self, scene_id: str | None) -> str | None:
        if not scene_id:
            return None
        return f"/static/images/scenes/{scene_id}.png"

    def find_latest_composite_image_url(
        self,
        *,
        character_id: int,
        scene_id: str | None,
    ) -> str | None:
        if not scene_id:
            return None
        return f"/static/images/composite/{scene_id}.png"


class StoryRestoreSmokeTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

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

    @patch("api.services.game_session.DatabaseManager", _FakeDatabaseManager)
    @patch("api.services.game_session.VectorDatabase", _FakeVectorDatabase)
    @patch("api.services.game_session.EventGenerator", _FakeEventGenerator)
    @patch("api.services.game_session.StoryEngine", _FakeStoryEngine)
    def test_story_snapshot_route_should_restore_after_manager_restart(self):
        repository = SqlAlchemyStoryRepository(
            engine=self.engine,
            session_factory=self.SessionLocal,
        )
        story_store = DatabaseStoryStore(storage_backend=repository)

        first_manager = GameSessionManager(story_store=story_store)
        first_session = first_manager.create_session(
            user_id="user-001",
            character_id=self.character_id,
            game_mode="solo",
        )
        first_session.is_initialized = True
        first_session.current_dialogue_round = {
            "player_options": [{"id": 1, "text": "继续"}],
        }
        first_session.story_engine.current_event_count = 2
        first_session.story_engine.current_event = {
            "title": "图书馆事件",
            "scene": "library",
        }
        first_session.story_engine.dialogue_history = [
            {"type": "character", "content": "先别急着走。"},
            {"type": "player", "content": "继续"},
        ]
        first_session.story_engine.current_scene = "library"
        first_session.story_engine.previous_event_contexts = ["在图书馆见面"]
        first_session.db_manager.update_character_states(
            self.character_id,
            {"trust": 15, "favorability": 5},
        )

        first_manager.save_story_snapshot(
            session=first_session,
            round_no=2,
            response_payload={
                "thread_id": first_session.thread_id,
                "character_dialogue": "图书馆见面后，你想继续问什么？",
                "player_options": [{"id": 1, "text": "继续"}],
                "story_background": "图书馆内很安静",
                "event_title": "图书馆事件",
                "scene": "library",
                "current_states": {
                    "favorability": 15.0,
                    "trust": 35.0,
                },
            },
            status="in_progress",
        )
        thread_id = first_session.thread_id

        restarted_manager = GameSessionManager(story_store=story_store)
        restored_session = restarted_manager.get_session(thread_id)

        self.assertTrue(restored_session.is_initialized)
        self.assertEqual(restored_session.story_engine.current_scene, "library")
        self.assertEqual(restored_session.story_engine.current_event["title"], "图书馆事件")
        self.assertEqual(restored_session.current_dialogue_round["player_options"][0]["text"], "继续")
        self.assertEqual(
            restored_session.db_manager.get_character_states(self.character_id).trust,
            35.0,
        )

        image_service = SimpleNamespace()
        asset_service = _ReadySnapshotAssetService(image_service=image_service)
        story_session_service = StorySessionService(
            session_manager=restarted_manager,
            story_asset_service=asset_service,
        )
        character_service = SimpleNamespace(db_manager=SimpleNamespace())
        image_executor = object()
        story_turn_service = SimpleNamespace(
            session_manager=restarted_manager,
            character_service=character_service,
            story_session_service=story_session_service,
            story_asset_service=asset_service,
            image_executor=image_executor,
            initialize_story=lambda *args, **kwargs: {},
            process_input=lambda *args, **kwargs: {},
            submit_turn=lambda *args, **kwargs: {},
        )
        story_ending_service = SimpleNamespace(
            session_manager=restarted_manager,
            story_asset_service=asset_service,
            check_ending=lambda thread_id: {"has_ending": False, "ending": None},
            trigger_ending=lambda thread_id: {},
        )
        game_service = GameService(
            session_manager=restarted_manager,
            image_service=image_service,
            character_service=character_service,
            story_asset_service=asset_service,
            story_session_service=story_session_service,
            story_turn_service=story_turn_service,
            story_ending_service=story_ending_service,
            image_executor=image_executor,
        )

        app = FastAPI()
        app.include_router(game.router, prefix="/api")
        app.dependency_overrides[get_game_service] = lambda: game_service
        client = TestClient(app)

        response = client.get(f"/api/v1/game/sessions/{thread_id}")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["thread_id"], thread_id)
        self.assertEqual(payload["data"]["round_no"], 2)
        self.assertEqual(payload["data"]["status"], "in_progress")
        self.assertEqual(payload["data"]["event_title"], "图书馆事件")
        self.assertEqual(payload["data"]["scene"], "library")
        self.assertEqual(payload["data"]["assets"]["scene_image"]["status"], "ready")
        self.assertEqual(
            payload["data"]["assets"]["scene_image"]["url"],
            "/static/images/scenes/library.png",
        )
        self.assertEqual(payload["data"]["assets"]["composite_image"]["status"], "ready")
        self.assertEqual(
            payload["data"]["assets"]["composite_image"]["url"],
            "/static/images/composite/library.png",
        )
        self.assertEqual(payload["data"]["snapshot"]["round_no"], 2)
        self.assertEqual(payload["data"]["snapshot"]["scene"], "library")
        self.assertTrue(payload["data"]["updated_at"])
        self.assertIn(thread_id, restarted_manager.get_cached_session_ids())

    @patch("api.services.game_session.DatabaseManager", _FakeDatabaseManager)
    @patch("api.services.game_session.VectorDatabase", _FakeVectorDatabase)
    @patch("api.services.game_session.EventGenerator", _FakeEventGenerator)
    @patch("api.services.game_session.StoryEngine", _FakeStoryEngine)
    def test_check_ending_should_survive_manager_restart_after_trigger_ending(self):
        repository = SqlAlchemyStoryRepository(
            engine=self.engine,
            session_factory=self.SessionLocal,
        )
        story_store = DatabaseStoryStore(storage_backend=repository)

        first_manager = GameSessionManager(story_store=story_store)
        first_session = first_manager.create_session(
            user_id="user-001",
            character_id=self.character_id,
            game_mode="solo",
        )
        first_session.is_initialized = True
        first_session.story_engine.current_scene = "library"
        first_session.db_manager.update_character_states(
            self.character_id,
            {"favorability": 70, "trust": 65, "hostility": 10},
        )

        asset_service = _ReadySnapshotAssetService(image_service=SimpleNamespace())
        first_ending_service = StoryEndingService(
            session_manager=first_manager,
            story_asset_service=asset_service,
        )

        trigger_result = first_ending_service.trigger_ending(first_session.thread_id)
        self.assertTrue(trigger_result["is_game_finished"])
        self.assertEqual(trigger_result["status"], "completed")

        restarted_manager = GameSessionManager(story_store=story_store)
        restarted_ending_service = StoryEndingService(
            session_manager=restarted_manager,
            story_asset_service=asset_service,
        )

        check_result = restarted_ending_service.check_ending(first_session.thread_id)
        summary_result = restarted_ending_service.get_ending_summary(first_session.thread_id)

        self.assertTrue(check_result["has_ending"])
        self.assertEqual(check_result["ending"]["type"], "good_ending")
        self.assertEqual(check_result["ending"]["trust"], 85.0)
        self.assertTrue(summary_result["has_ending"])
        self.assertEqual(summary_result["ending"]["type"], "good_ending")
        self.assertEqual(summary_result["ending"]["key_states"]["trust"], 85.0)


if __name__ == "__main__":
    unittest.main()
