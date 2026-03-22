"""Story route smoke tests backed by SQLite.

This suite mirrors training route smoke intent:
1. story router/service/repository should work end-to-end on a real SQLAlchemy DB
2. story read/write route contracts should stay stable for the core recovery paths
"""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.story  # noqa: F401 - register story models on Base.metadata
from api.dependencies import get_game_service
from api.middleware.error_handler import install_common_exception_handlers
from api.routers import game
from api.services.game_service import GameService
from api.services.game_session import GameSessionManager
from models.character import Base, Character
from story.story_asset_service import StoryAssetService
from story.story_ending_service import StoryEndingService
from story.story_history_service import StoryHistoryService
from story.story_repository import SqlAlchemyStoryRepository
from story.story_session_query_policy import StorySessionQueryPolicy
from story.story_session_service import StorySessionService
from story.story_store import DatabaseStoryStore
from story.story_turn_service import StoryTurnService


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
            name="Story Smoke Character",
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
        self.current_scene = "school"
        self.previous_event_contexts = []

    def get_opening_event(self, *, character_id: int, scene_id: str, opening_event_id: str | None = None):
        self.current_scene = scene_id
        self.current_event = {
            "title": "Opening Event",
            "story_background": "A calm start.",
            "scene": scene_id,
        }
        return dict(self.current_event)

    def get_next_dialogue_round(self, character_id: int):
        if self.current_event_count == 0:
            return {
                "character_dialogue": "Welcome to the first scene.",
                "player_options": [
                    {
                        "id": 1,
                        "text": "Ask about the clue",
                        "type": "curious",
                        "state_changes": {"trust": 2},
                    },
                    {
                        "id": 2,
                        "text": "Stay silent",
                        "type": "neutral",
                        "state_changes": {},
                    },
                ],
            }
        return {
            "character_dialogue": "We can move to the library.",
            "player_options": [
                {
                    "id": 1,
                    "text": "Continue",
                    "type": "neutral",
                    "state_changes": {},
                }
            ],
        }

    def record_character_dialogue(self, dialogue: str):
        self.dialogue_history.append({"type": "character", "content": dialogue})

    def process_player_choice(self, character_id: int, choice):
        choice_text = choice.get("text") if isinstance(choice, dict) else str(choice)
        self.dialogue_history.append({"type": "player", "content": choice_text})
        self.current_event_count += 1
        self.current_scene = "library"
        self.current_event = {
            "title": "Library Event",
            "story_background": "Rows of books.",
            "scene": "library",
        }

    def should_continue_dialogue(self, character_id: int):
        return True

    def save_event_to_vector_db(self, character_id: int):
        return None

    def get_next_event(self, character_id: int):
        return {
            "title": "Fallback Event",
            "story_background": "Fallback background",
            "scene": "library",
        }

    def is_game_finished(self):
        return False

    def get_ending_event(self, character_id: int):
        self.current_scene = "ending"
        return {
            "title": "Finale",
            "story_background": "The story wraps up.",
            "scene": "ending",
            "ending_type": "open_ending",
        }

    def save_dialogue_round_to_vector_db(
        self,
        *,
        character_id: int,
        dialogue_round: int,
        state_changes: dict,
    ):
        return None


class _ReadyStoryAssetService(StoryAssetService):
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


class StoryRouteSqliteSmokeTestCase(unittest.TestCase):
    def setUp(self):
        self._patchers = [
            patch("api.services.game_session.DatabaseManager", _FakeDatabaseManager),
            patch("api.services.game_session.VectorDatabase", _FakeVectorDatabase),
            patch("api.services.game_session.EventGenerator", _FakeEventGenerator),
            patch("api.services.game_session.StoryEngine", _FakeStoryEngine),
        ]
        for patcher in self._patchers:
            patcher.start()

        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        with self.SessionLocal() as session:
            character = Character(
                name="Story Smoke Character",
                gender="female",
                appearance="short hair",
                personality="calm",
            )
            session.add(character)
            session.commit()
            self.character_id = character.id

        self.repository = SqlAlchemyStoryRepository(
            engine=self.engine,
            session_factory=self.SessionLocal,
        )
        self.store = DatabaseStoryStore(storage_backend=self.repository)
        self.session_manager = GameSessionManager(story_store=self.store)

        self.asset_service = _ReadyStoryAssetService(image_service=SimpleNamespace())
        self.story_session_service = StorySessionService(
            session_manager=self.session_manager,
            story_asset_service=self.asset_service,
            session_query_policy=StorySessionQueryPolicy(
                mode=StorySessionQueryPolicy.MODE_ACTOR_HEADER_MATCH,
            ),
        )
        self.story_turn_service = StoryTurnService(
            session_manager=self.session_manager,
            character_service=SimpleNamespace(db_manager=SimpleNamespace()),
            story_session_service=self.story_session_service,
            story_asset_service=self.asset_service,
            image_executor=None,
        )
        self.story_ending_service = StoryEndingService(
            session_manager=self.session_manager,
            story_asset_service=self.asset_service,
        )
        self.story_history_service = StoryHistoryService(
            session_manager=self.session_manager,
        )
        self.game_service = GameService(
            story_asset_service=self.asset_service,
            story_session_service=self.story_session_service,
            story_turn_service=self.story_turn_service,
            story_ending_service=self.story_ending_service,
            story_history_service=self.story_history_service,
        )

        self.app = FastAPI()
        install_common_exception_handlers(self.app)
        self.app.include_router(game.router, prefix="/api")
        self.app.dependency_overrides[get_game_service] = lambda: self.game_service
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        for patcher in reversed(self._patchers):
            patcher.stop()

    def test_story_routes_should_complete_real_db_smoke_flow(self):
        init_response = self.client.post(
            "/api/v1/game/init",
            json={
                "user_id": "story-smoke-user",
                "character_id": str(self.character_id),
                "game_mode": "solo",
            },
        )
        self.assertEqual(init_response.status_code, 200)
        init_payload = init_response.json()["data"]
        thread_id = init_payload["thread_id"]
        self.assertEqual(init_payload["status"], "initialized")

        initialize_response = self.client.post(
            "/api/v1/game/initialize-story",
            json={
                "thread_id": thread_id,
                "character_id": str(self.character_id),
                "scene_id": "school",
            },
        )
        self.assertEqual(initialize_response.status_code, 200)
        initialize_payload = initialize_response.json()["data"]
        self.assertEqual(initialize_payload["thread_id"], thread_id)
        self.assertEqual(initialize_payload["round_no"], 0)
        self.assertEqual(initialize_payload["status"], "in_progress")
        self.assertEqual(initialize_payload["assets"]["scene_image"]["status"], "ready")
        self.assertEqual(initialize_payload["assets"]["composite_image"]["status"], "ready")

        submit_response = self.client.post(
            "/api/v1/game/input",
            json={
                "thread_id": thread_id,
                "user_input": "Keep moving.",
                "user_id": "story-smoke-user",
                "character_id": str(self.character_id),
            },
        )
        self.assertEqual(submit_response.status_code, 200)
        submit_payload = submit_response.json()["data"]
        self.assertEqual(submit_payload["thread_id"], thread_id)
        self.assertEqual(submit_payload["round_no"], 1)
        self.assertEqual(submit_payload["status"], "in_progress")
        self.assertFalse(submit_payload["is_game_finished"])

        snapshot_response = self.client.get(f"/api/v1/game/sessions/{thread_id}")
        self.assertEqual(snapshot_response.status_code, 200)
        snapshot_payload = snapshot_response.json()["data"]
        self.assertEqual(snapshot_payload["thread_id"], thread_id)
        self.assertEqual(snapshot_payload["round_no"], 1)
        self.assertEqual(snapshot_payload["scene"], "library")
        self.assertEqual(snapshot_payload["assets"]["scene_image"]["status"], "ready")
        self.assertEqual(snapshot_payload["assets"]["composite_image"]["status"], "ready")

        sessions_response = self.client.get(
            "/api/v1/game/sessions",
            params={"user_id": "story-smoke-user"},
            headers={"X-Story-Actor-Id": "story-smoke-user"},
        )
        self.assertEqual(sessions_response.status_code, 200)
        sessions_payload = sessions_response.json()["data"]
        self.assertEqual(sessions_payload["user_id"], "story-smoke-user")
        self.assertEqual(sessions_payload["sessions"][0]["thread_id"], thread_id)
        self.assertEqual(sessions_payload["sessions"][0]["round_no"], 1)

        history_response = self.client.get(f"/api/v1/game/sessions/{thread_id}/history")
        self.assertEqual(history_response.status_code, 200)
        history_payload = history_response.json()["data"]
        self.assertEqual(history_payload["thread_id"], thread_id)
        self.assertEqual(history_payload["current_round_no"], 1)
        self.assertEqual(history_payload["history"][0]["round_no"], 1)
        self.assertEqual(history_payload["history"][0]["scene"], "library")

        trigger_ending_response = self.client.post(
            "/api/v1/game/trigger-ending",
            json={"thread_id": thread_id},
        )
        self.assertEqual(trigger_ending_response.status_code, 200)
        trigger_payload = trigger_ending_response.json()["data"]
        self.assertEqual(trigger_payload["status"], "completed")
        self.assertTrue(trigger_payload["is_game_finished"])

        ending_summary_response = self.client.get(f"/api/v1/game/sessions/{thread_id}/ending")
        self.assertEqual(ending_summary_response.status_code, 200)
        ending_summary_payload = ending_summary_response.json()["data"]
        self.assertTrue(ending_summary_payload["has_ending"])
        self.assertEqual(ending_summary_payload["ending"]["type"], "open_ending")

        ending_check_response = self.client.get(f"/api/v1/game/check-ending/{thread_id}")
        self.assertEqual(ending_check_response.status_code, 200)
        ending_check_payload = ending_check_response.json()["data"]
        self.assertTrue(ending_check_payload["has_ending"])
        self.assertEqual(ending_check_payload["ending"]["type"], "open_ending")

    def test_story_read_routes_should_return_not_found_error_for_missing_thread(self):
        missing_thread_id = "missing-thread-id"
        read_routes = [
            f"/api/v1/game/sessions/{missing_thread_id}",
            f"/api/v1/game/sessions/{missing_thread_id}/history",
            f"/api/v1/game/sessions/{missing_thread_id}/ending",
            f"/api/v1/game/check-ending/{missing_thread_id}",
        ]

        for path in read_routes:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "STORY_SESSION_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
