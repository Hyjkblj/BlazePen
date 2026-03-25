"""故事主线独立应用测试。

目标：
1. 验证故事主线入口可独立提供健康检查与核心路由契约。
2. 验证故事入口不会暴露 training 域路由。
"""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import app
from api.dependencies import get_story_service_bundle


class _FakeStoryGameService:
    story_asset_service = type(
        "_AssetService",
        (),
        {
            "merge_story_assets": staticmethod(lambda payload, **_: dict(payload or {})),
        },
    )()

    def init_game(self, user_id=None, character_id=None, game_mode="solo"):
        return {
            "thread_id": "story-thread-001",
            "user_id": user_id or "story-user-001",
            "game_mode": game_mode,
            "status": "initialized",
        }


def _build_story_bundle(service: _FakeStoryGameService):
    return SimpleNamespace(
        story_asset_service=service.story_asset_service,
        story_session_service=SimpleNamespace(
            init_game=service.init_game,
            get_session_snapshot=lambda thread_id: {"thread_id": thread_id},
            list_recent_sessions=lambda **_: {"user_id": "story-user-001", "sessions": []},
        ),
        story_turn_service=SimpleNamespace(
            initialize_story=lambda *args, **kwargs: {},
            submit_turn=lambda *args, **kwargs: {},
        ),
        story_ending_service=SimpleNamespace(
            get_ending_summary=lambda thread_id: {
                "thread_id": thread_id,
                "status": "initialized",
                "round_no": 0,
                "has_ending": False,
                "ending": None,
            },
            check_ending=lambda thread_id: {"has_ending": False, "ending": None},
            trigger_ending=lambda thread_id: {},
        ),
        story_history_service=SimpleNamespace(
            get_story_history=lambda thread_id: {"thread_id": thread_id, "history": []},
        ),
    )


class StoryStandaloneAppTestCase(unittest.TestCase):
    def setUp(self):
        self.database_manager_patcher = patch("api.app_factory.DatabaseManager")
        self.database_manager_patcher.start()
        app.dependency_overrides[get_story_service_bundle] = (
            lambda: _build_story_bundle(_FakeStoryGameService())
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.database_manager_patcher.stop()

    def test_story_health_should_return_trace_header(self):
        response = self.client.get(
            "/health",
            headers={"X-Trace-Id": "story-standalone-trace-001"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Trace-Id"], "story-standalone-trace-001")
        self.assertEqual(response.json()["status"], "healthy")

    def test_story_init_should_work_on_story_entrypoint(self):
        response = self.client.post(
            "/api/v1/game/init",
            json={
                "user_id": "story-user-a",
                "character_id": "7",
                "game_mode": "solo",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["thread_id"], "story-thread-001")
        self.assertEqual(payload["data"]["status"], "initialized")

    def test_story_entrypoint_should_not_expose_training_routes(self):
        response = self.client.post(
            "/api/v1/training/init",
            json={
                "user_id": "story-user-a",
                "training_mode": "guided",
            },
        )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
