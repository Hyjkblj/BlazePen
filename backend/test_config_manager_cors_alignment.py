from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from config_manager import Config


class ConfigManagerCorsAlignmentTestCase(unittest.TestCase):
    def test_dev_config_should_share_cors_defaults_with_api_cors_config(self):
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
            config = Config(env="dev")

        self.assertIn("http://localhost:3000", config.story_allowed_origins)
        self.assertIn("http://localhost:3001", config.story_allowed_origins)
        self.assertIn("http://localhost:3001", config.training_allowed_origins)
        self.assertEqual(config.allowed_origins, config.story_allowed_origins)

    def test_prod_config_should_support_shared_allowlist(self):
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
            config = Config(env="prod")

        self.assertEqual(
            config.story_allowed_origins,
            ["https://shared.example.com", "https://shared-alt.example.com"],
        )
        self.assertEqual(config.training_allowed_origins, config.story_allowed_origins)
        self.assertEqual(config.allowed_origins, config.story_allowed_origins)

    def test_prod_config_should_support_explicit_per_backend_allowlists(self):
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
            config = Config(env="prod")

        self.assertEqual(config.story_allowed_origins, ["https://story.example.com"])
        self.assertEqual(config.training_allowed_origins, ["https://training.example.com"])
        self.assertEqual(config.allowed_origins, ["https://story.example.com"])


if __name__ == "__main__":
    unittest.main()
