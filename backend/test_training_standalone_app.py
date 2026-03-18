"""训练专用独立应用测试。

目标：
1. 验证训练专用应用只挂训练路由时仍能正常提供基础健康接口。
2. 验证训练专用应用可以在不依赖真实数据库的情况下通过依赖覆盖完成接口契约测试。
"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from api.dependencies import get_training_service
from api.training_app import app


class _FakeTrainingService:
    """最小训练服务桩，用来验证训练专用应用的路由接线。"""

    def init_training(self, user_id, character_id=None, training_mode="guided", player_profile=None):
        return {
            "session_id": "standalone-s1",
            "status": "in_progress",
            "round_no": 0,
            "k_state": {"K1": 0.45},
            "s_state": {"credibility": 0.6},
            "player_profile": player_profile,
            "next_scenario": {"id": "S1", "title": "训练题目"},
            "scenario_candidates": [{"id": "S1", "title": "训练题目"}],
        }


class TrainingStandaloneAppTestCase(unittest.TestCase):
    """验证训练专用应用可独立提供训练接口。"""

    def setUp(self):
        app.dependency_overrides[get_training_service] = lambda: _FakeTrainingService()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_health_endpoint_should_return_training_service_scope(self):
        """健康检查应明确返回训练服务正常状态。"""
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "healthy")

    def test_init_endpoint_should_work_on_training_only_app(self):
        """训练专用应用应能独立响应训练初始化接口。"""
        response = self.client.post(
            "/api/v1/training/init",
            json={
                "user_id": "standalone-user",
                "training_mode": "guided",
                "player_profile": {
                    "name": "李敏",
                    "gender": "女",
                    "identity": "战地记者",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["session_id"], "standalone-s1")
        self.assertEqual(payload["data"]["player_profile"]["name"], "李敏")
        self.assertEqual(payload["data"]["next_scenario"]["id"], "S1")


if __name__ == "__main__":
    unittest.main()
