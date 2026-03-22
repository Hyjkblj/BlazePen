"""App-entry boundary tests for story and training backends."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import app as story_app
from api.training_app import app as training_app


class ApiEntrypointBoundaryTestCase(unittest.TestCase):
    """Lock route exposure to a single backend entrypoint per domain."""

    def test_story_app_should_not_expose_training_routes(self):
        with patch("api.app_factory.DatabaseManager"):
            with TestClient(story_app) as client:
                response = client.post(
                    "/api/v1/training/init",
                    json={
                        "user_id": "story-app-user",
                        "training_mode": "guided",
                    },
                )

        self.assertEqual(response.status_code, 404)

    def test_training_app_should_not_expose_story_routes(self):
        with patch("api.app_factory.DatabaseManager"):
            with TestClient(training_app) as client:
                response = client.get(
                    "/api/v1/game/sessions",
                    params={"user_id": "training-app-user"},
                )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
