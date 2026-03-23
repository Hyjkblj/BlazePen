from __future__ import annotations

import logging
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app_factory import create_api_app


class ApiAppFactoryMetadataTestCase(unittest.TestCase):
    def test_create_api_app_should_reject_root_extra_override_on_service_scope(self):
        with self.assertRaisesRegex(ValueError, "root_extra cannot override reserved root metadata keys"):
            create_api_app(
                title="training-test",
                description="metadata-guard-test",
                service_scope="training",
                logger=logging.getLogger("test.training.metadata"),
                root_message="training-root",
                root_extra={"service_scope": "training_only"},
            )

    def test_root_metadata_should_keep_service_scope_as_single_source_of_truth(self):
        app = create_api_app(
            title="training-test",
            description="metadata-contract-test",
            service_scope="training",
            logger=logging.getLogger("test.training.metadata"),
            root_message="training-root",
            root_extra={"entrypoint_kind": "training_only"},
        )

        with patch("api.app_factory.DatabaseManager"):
            with TestClient(app) as client:
                response = client.get("/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["service_scope"], "training")
        self.assertEqual(payload["entrypoint_kind"], "training_only")
        self.assertEqual(app.state.service_scope, payload["service_scope"])


if __name__ == "__main__":
    unittest.main()
