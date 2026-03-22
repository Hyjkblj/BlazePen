"""Entry-level shared runtime tests for story and training apps."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import app as story_app
from api.training_app import app as training_app


class ApiEntryCommonMiddlewareTestCase(unittest.TestCase):
    """Verify both backend entrypoints share the same runtime contract."""

    def test_story_health_should_echo_trace_id(self):
        with patch("api.app_factory.DatabaseManager"):
            with TestClient(story_app) as client:
                response = client.get(
                    "/health",
                    headers={"X-Trace-Id": "story-trace-001"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Trace-Id"], "story-trace-001")
        self.assertEqual(response.json()["message"], "服务正常运行")

    def test_training_root_should_return_training_metadata(self):
        with patch("api.app_factory.DatabaseManager"):
            with TestClient(training_app) as client:
                response = client.get("/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["docs"], "/docs")
        self.assertEqual(payload["service_scope"], "training")
        self.assertEqual(payload["entrypoint_kind"], "training_only")
        self.assertEqual(payload["message"], "烽火笔锋训练引擎 API")

    def test_story_root_should_return_story_metadata(self):
        with patch("api.app_factory.DatabaseManager"):
            with TestClient(story_app) as client:
                response = client.get("/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["docs"], "/docs")
        self.assertEqual(payload["service_scope"], "story")
        self.assertNotIn("entrypoint_kind", payload)

    def test_story_health_should_allow_story_frontend_origin(self):
        with patch("api.app_factory.DatabaseManager"):
            with TestClient(story_app) as client:
                response = client.get(
                    "/health",
                    headers={"Origin": "http://localhost:3000"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )

    def test_training_health_should_allow_training_frontend_origin(self):
        with patch("api.app_factory.DatabaseManager"):
            with TestClient(training_app) as client:
                response = client.get(
                    "/health",
                    headers={"Origin": "http://localhost:3001"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:3001",
        )

    def test_story_health_preflight_should_return_cors_headers(self):
        with patch("api.app_factory.DatabaseManager"):
            with TestClient(story_app) as client:
                response = client.options(
                    "/health",
                    headers={
                        "Origin": "http://localhost:3000",
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "X-Trace-Id,Content-Type",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )
        allow_methods = response.headers.get("access-control-allow-methods", "")
        self.assertIn("POST", allow_methods)
        allow_headers = response.headers.get("access-control-allow-headers", "").lower()
        self.assertIn("x-trace-id", allow_headers)

    def test_training_health_preflight_should_return_cors_headers(self):
        with patch("api.app_factory.DatabaseManager"):
            with TestClient(training_app) as client:
                response = client.options(
                    "/health",
                    headers={
                        "Origin": "http://localhost:3001",
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "X-Trace-Id,Content-Type",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:3001",
        )
        allow_methods = response.headers.get("access-control-allow-methods", "")
        self.assertIn("POST", allow_methods)
        allow_headers = response.headers.get("access-control-allow-headers", "").lower()
        self.assertIn("x-trace-id", allow_headers)


if __name__ == "__main__":
    unittest.main()
