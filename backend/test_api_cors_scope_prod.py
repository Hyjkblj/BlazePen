from __future__ import annotations

import logging
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app_factory import create_api_app


def _create_test_app(service_scope: str):
    return create_api_app(
        title=f"{service_scope}-test",
        description="cors-scope-test",
        service_scope=service_scope,
        logger=logging.getLogger(f"test.{service_scope}"),
        root_message=f"{service_scope}-root",
    )


def _preflight(client: TestClient, *, origin: str):
    return client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Trace-Id,Content-Type",
        },
    )


class ApiCorsScopeProdTestCase(unittest.TestCase):
    def test_prod_cors_should_keep_story_training_allowlists_isolated(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ALLOWED_ORIGINS": "",
                "STORY_ALLOWED_ORIGINS": "https://story.example.com",
                "TRAINING_ALLOWED_ORIGINS": "https://training.example.com",
            },
            clear=True,
        ):
            story_app = _create_test_app("story")
            training_app = _create_test_app("training")

        with patch("api.app_factory.DatabaseManager"):
            with TestClient(story_app) as story_client:
                story_allowed = story_client.get(
                    "/health",
                    headers={"Origin": "https://story.example.com"},
                )
                story_blocked = story_client.get(
                    "/health",
                    headers={"Origin": "https://training.example.com"},
                )

            with TestClient(training_app) as training_client:
                training_allowed = training_client.get(
                    "/health",
                    headers={"Origin": "https://training.example.com"},
                )
                training_blocked = training_client.get(
                    "/health",
                    headers={"Origin": "https://story.example.com"},
                )

        self.assertEqual(
            story_allowed.headers.get("access-control-allow-origin"),
            "https://story.example.com",
        )
        self.assertIsNone(story_blocked.headers.get("access-control-allow-origin"))
        self.assertEqual(
            training_allowed.headers.get("access-control-allow-origin"),
            "https://training.example.com",
        )
        self.assertIsNone(training_blocked.headers.get("access-control-allow-origin"))

    def test_prod_cors_should_allow_common_fallback_for_both_entrypoints(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ALLOWED_ORIGINS": "https://shared.example.com",
                "STORY_ALLOWED_ORIGINS": "",
                "TRAINING_ALLOWED_ORIGINS": "",
            },
            clear=True,
        ):
            story_app = _create_test_app("story")
            training_app = _create_test_app("training")

        with patch("api.app_factory.DatabaseManager"):
            with TestClient(story_app) as story_client:
                story_response = story_client.get(
                    "/health",
                    headers={"Origin": "https://shared.example.com"},
                )
            with TestClient(training_app) as training_client:
                training_response = training_client.get(
                    "/health",
                    headers={"Origin": "https://shared.example.com"},
                )

        self.assertEqual(
            story_response.headers.get("access-control-allow-origin"),
            "https://shared.example.com",
        )
        self.assertEqual(
            training_response.headers.get("access-control-allow-origin"),
            "https://shared.example.com",
        )

    def test_prod_cors_preflight_should_use_restricted_headers_and_methods(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ALLOWED_ORIGINS": "",
                "STORY_ALLOWED_ORIGINS": "https://story.example.com",
                "TRAINING_ALLOWED_ORIGINS": "https://training.example.com",
            },
            clear=True,
        ):
            story_app = _create_test_app("story")
            training_app = _create_test_app("training")

        with patch("api.app_factory.DatabaseManager"):
            with TestClient(story_app) as story_client:
                story_preflight = _preflight(
                    story_client,
                    origin="https://story.example.com",
                )
            with TestClient(training_app) as training_client:
                training_preflight = _preflight(
                    training_client,
                    origin="https://training.example.com",
                )

        for response, expected_origin in (
            (story_preflight, "https://story.example.com"),
            (training_preflight, "https://training.example.com"),
        ):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.headers.get("access-control-allow-origin"),
                expected_origin,
            )
            allow_methods = response.headers.get("access-control-allow-methods", "")
            self.assertIn("GET", allow_methods)
            self.assertIn("POST", allow_methods)
            self.assertNotIn("*", allow_methods)
            allow_headers = response.headers.get("access-control-allow-headers", "").lower()
            self.assertIn("x-trace-id", allow_headers)
            self.assertNotIn("*", allow_headers)

    def test_prod_cors_preflight_should_reject_disallowed_origin(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ALLOWED_ORIGINS": "",
                "STORY_ALLOWED_ORIGINS": "https://story.example.com",
                "TRAINING_ALLOWED_ORIGINS": "https://training.example.com",
            },
            clear=True,
        ):
            story_app = _create_test_app("story")

        with patch("api.app_factory.DatabaseManager"):
            with TestClient(story_app) as story_client:
                blocked_preflight = _preflight(
                    story_client,
                    origin="https://training.example.com",
                )

        self.assertEqual(blocked_preflight.status_code, 400)
        self.assertIsNone(blocked_preflight.headers.get("access-control-allow-origin"))


if __name__ == "__main__":
    unittest.main()
