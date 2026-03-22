from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from api.cors_config import build_allowed_origins, build_cors_middleware_options


class ApiCorsConfigTestCase(unittest.TestCase):
    def test_dev_story_origins_should_include_dual_frontend_ports(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "dev",
                "ALLOWED_ORIGINS": "",
                "STORY_ALLOWED_ORIGINS": "",
                "TRAINING_ALLOWED_ORIGINS": "",
            },
            clear=True,
        ):
            allowed_origins = build_allowed_origins(service_scope="story")

        self.assertIn("http://localhost:3000", allowed_origins)
        self.assertIn("http://localhost:3001", allowed_origins)
        self.assertIn("http://127.0.0.1:3000", allowed_origins)
        self.assertIn("http://127.0.0.1:3001", allowed_origins)

    def test_prod_story_origins_should_prefer_story_specific_allowlist(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ALLOWED_ORIGINS": "https://shared.example.com",
                "STORY_ALLOWED_ORIGINS": "https://story.example.com, https://story-alt.example.com",
                "TRAINING_ALLOWED_ORIGINS": "https://training.example.com",
            },
            clear=True,
        ):
            allowed_origins = build_allowed_origins(service_scope="story")

        self.assertEqual(
            allowed_origins,
            [
                "https://story.example.com",
                "https://story-alt.example.com",
            ],
        )

    def test_prod_training_origins_should_fallback_to_common_allowlist(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ALLOWED_ORIGINS": "https://shared.example.com, https://shared-alt.example.com",
                "STORY_ALLOWED_ORIGINS": "",
                "TRAINING_ALLOWED_ORIGINS": "",
            },
            clear=True,
        ):
            allowed_origins = build_allowed_origins(service_scope="training")

        self.assertEqual(
            allowed_origins,
            [
                "https://shared.example.com",
                "https://shared-alt.example.com",
            ],
        )

    def test_prod_allowlist_should_raise_when_no_explicit_origins_exist(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ALLOWED_ORIGINS": "",
                "STORY_ALLOWED_ORIGINS": "",
                "TRAINING_ALLOWED_ORIGINS": "",
            },
            clear=True,
        ):
            with self.assertRaises(ValueError) as cm:
                build_allowed_origins(service_scope="training")

        self.assertIn("TRAINING_ALLOWED_ORIGINS", str(cm.exception))
        self.assertIn("ALLOWED_ORIGINS", str(cm.exception))

    def test_prod_cors_options_should_use_restricted_methods_and_headers(self):
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
            cors_options = build_cors_middleware_options(service_scope="training")

        self.assertEqual(cors_options["allow_origins"], ["https://shared.example.com"])
        self.assertNotEqual(cors_options["allow_methods"], ["*"])
        self.assertNotEqual(cors_options["allow_headers"], ["*"])
        self.assertIn("X-Trace-Id", cors_options["allow_headers"])


if __name__ == "__main__":
    unittest.main()
