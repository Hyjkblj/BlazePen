from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_game_service
from api.routers import game
from story.exceptions import StorySessionAccessDeniedError, StorySessionNotFoundError
from story.story_asset_service import StoryAssetService
from story.story_session_query_policy import StorySessionQueryPolicy


class _FakeStoryQueryGameService:
    story_asset_service = StoryAssetService()

    def list_story_sessions(
        self,
        *,
        user_id: str,
        limit: int = 10,
        actor_user_id: str | None = None,
    ):
        return {
            "user_id": user_id,
            "sessions": [
                {
                    "thread_id": "thread-001",
                    "user_id": user_id,
                    "character_id": 7,
                    "game_mode": "solo",
                    "status": "in_progress",
                    "round_no": 2,
                    "scene": "library",
                    "event_title": "Library Scene",
                    "is_initialized": True,
                    "has_ending": False,
                    "can_resume": True,
                    "updated_at": "2026-03-20T10:00:00",
                    "expires_at": "2026-03-21T10:00:00",
                }
            ][:limit],
        }

    def get_story_history(self, thread_id: str):
        if thread_id == "missing-thread":
            raise StorySessionNotFoundError(thread_id=thread_id)
        return {
            "thread_id": thread_id,
            "status": "completed",
            "current_round_no": 2,
            "latest_scene": "rooftop",
            "updated_at": "2026-03-20T12:00:00",
            "expires_at": "2026-03-21T12:00:00",
            "latest_snapshot": {
                "thread_id": thread_id,
                "status": "completed",
                "round_no": 2,
                "scene": "rooftop",
            },
            "history": [
                {
                    "round_no": 1,
                    "status": "in_progress",
                    "scene": "library",
                    "event_title": "Clue Found",
                    "character_dialogue": "Archive first.",
                    "user_action": {
                        "kind": "option",
                        "summary": "Ask about the clue",
                        "option_index": 0,
                        "option_text": "Ask about the clue",
                        "option_type": "curious",
                    },
                    "state_summary": {
                        "changes": {"trust": 10},
                        "current_states": {"trust": 60},
                    },
                    "is_event_finished": True,
                    "is_game_finished": False,
                    "created_at": "2026-03-20T11:00:00",
                }
            ],
        }

    def get_story_ending_summary(self, thread_id: str):
        return {
            "thread_id": thread_id,
            "status": "completed",
            "round_no": 2,
            "has_ending": True,
            "ending": {
                "type": "good_ending",
                "description": "resolved ending",
                "scene": "ending",
                "event_title": "Ending",
                "key_states": {
                    "favorability": 70,
                    "trust": 65,
                    "hostility": 10,
                    "dependence": 20,
                },
            },
            "updated_at": "2026-03-20T12:00:00",
            "expires_at": "2026-03-21T12:00:00",
        }

    def check_ending(self, thread_id: str):
        if thread_id == "missing-thread":
            raise StorySessionNotFoundError(thread_id=thread_id)
        return {
            "has_ending": True,
            "ending": {
                "type": "good_ending",
                "description": "resolved ending",
                "favorability": 70,
                "trust": 65,
                "hostility": 10,
            },
        }


class _DeniedStoryQueryGameService(_FakeStoryQueryGameService):
    def list_story_sessions(
        self,
        *,
        user_id: str,
        limit: int = 10,
        actor_user_id: str | None = None,
    ):
        raise StorySessionAccessDeniedError(
            requested_user_id=user_id,
            actor_user_id=actor_user_id,
            policy_mode="actor_header_match",
        )


class _DefaultSecureStoryQueryGameService(_FakeStoryQueryGameService):
    def __init__(self):
        self.policy = StorySessionQueryPolicy()

    def list_story_sessions(
        self,
        *,
        user_id: str,
        limit: int = 10,
        actor_user_id: str | None = None,
    ):
        authorized_user_id = self.policy.authorize_recent_sessions_query(
            requested_user_id=user_id,
            actor_user_id=actor_user_id,
        )
        return super().list_story_sessions(
            user_id=authorized_user_id,
            limit=limit,
            actor_user_id=actor_user_id,
        )


class StoryQueryRoutesTestCase(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(game.router, prefix="/api")
        app.dependency_overrides[get_game_service] = lambda: _FakeStoryQueryGameService()
        self.app = app
        self.client = TestClient(app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_recent_sessions_route_should_return_stable_contract(self):
        response = self.client.get("/api/v1/game/sessions", params={"user_id": "user-001"})

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["user_id"], "user-001")
        self.assertEqual(payload["data"]["sessions"][0]["thread_id"], "thread-001")
        self.assertTrue(payload["data"]["sessions"][0]["can_resume"])

    def test_recent_sessions_route_should_return_stable_forbidden_contract(self):
        self.app.dependency_overrides[get_game_service] = lambda: _DeniedStoryQueryGameService()

        response = self.client.get(
            "/api/v1/game/sessions",
            params={"user_id": "user-001"},
            headers={"X-Story-Actor-Id": "user-002"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(payload["error"]["code"], "STORY_SESSION_ACCESS_DENIED")
        self.assertEqual(payload["error"]["details"]["policy_mode"], "actor_header_match")
        self.assertTrue(payload["error"]["traceId"])

    def test_recent_sessions_route_should_deny_missing_actor_under_default_policy(self):
        self.app.dependency_overrides[get_game_service] = lambda: _DefaultSecureStoryQueryGameService()

        response = self.client.get("/api/v1/game/sessions", params={"user_id": "user-001"})

        payload = response.json()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(payload["error"]["code"], "STORY_SESSION_ACCESS_DENIED")
        self.assertEqual(
            payload["error"]["details"]["policy_mode"],
            StorySessionQueryPolicy.MODE_ACTOR_HEADER_MATCH,
        )

    def test_story_history_route_should_return_persisted_history_contract(self):
        response = self.client.get("/api/v1/game/sessions/thread-001/history")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["thread_id"], "thread-001")
        self.assertEqual(payload["data"]["history"][0]["user_action"]["summary"], "Ask about the clue")
        self.assertEqual(payload["data"]["history"][0]["state_summary"]["changes"]["trust"], 10.0)

    def test_story_history_route_should_return_not_found_error_code(self):
        response = self.client.get("/api/v1/game/sessions/missing-thread/history")

        payload = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(payload["error"]["code"], "STORY_SESSION_NOT_FOUND")

    def test_story_ending_summary_route_should_return_product_facing_contract(self):
        response = self.client.get("/api/v1/game/sessions/thread-001/ending")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["data"]["has_ending"])
        self.assertEqual(payload["data"]["ending"]["type"], "good_ending")
        self.assertEqual(payload["data"]["ending"]["key_states"]["trust"], 65.0)

    def test_story_check_ending_route_should_return_legacy_contract(self):
        response = self.client.get("/api/v1/game/check-ending/thread-001")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["data"]["has_ending"])
        self.assertEqual(payload["data"]["ending"]["type"], "good_ending")
        self.assertEqual(payload["data"]["ending"]["trust"], 65)

    def test_story_check_ending_route_should_return_not_found_error_code(self):
        response = self.client.get("/api/v1/game/check-ending/missing-thread")

        payload = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(payload["error"]["code"], "STORY_SESSION_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
