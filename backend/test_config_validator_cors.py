from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from api.cors_config import COMMON_ALLOWED_ORIGINS_ENV, SERVICE_ALLOWED_ORIGIN_ENVS
from utils.config_validator import ConfigValidator


class ConfigValidatorCorsTestCase(unittest.TestCase):
    _TTS_BASE_ENV = {
        "VOLCENGINE_TTS_APP_ID": "app-id",
        "VOLCENGINE_TTS_ACCESS_TOKEN": "token",
        "VOLCENGINE_TTS_SECRET_KEY": "secret",
    }

    def test_prod_validation_should_fail_when_no_cors_allowlist_exists(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ALLOWED_ORIGINS": "",
                "STORY_ALLOWED_ORIGINS": "",
                "TRAINING_ALLOWED_ORIGINS": "",
                **self._TTS_BASE_ENV,
            },
            clear=True,
        ):
            is_valid, errors, _warnings = ConfigValidator.validate("prod")

        self.assertFalse(is_valid)
        self.assertTrue(
            any("CORS allowlist" in message for message in errors),
            msg=f"expected CORS validation error, got: {errors}",
        )
        self.assertTrue(
            any(COMMON_ALLOWED_ORIGINS_ENV in message for message in errors),
            msg=f"expected {COMMON_ALLOWED_ORIGINS_ENV} in CORS error, got: {errors}",
        )
        self.assertTrue(
            any(SERVICE_ALLOWED_ORIGIN_ENVS["story"] in message for message in errors),
            msg=f"expected story origins env in CORS error, got: {errors}",
        )
        self.assertTrue(
            any(SERVICE_ALLOWED_ORIGIN_ENVS["training"] in message for message in errors),
            msg=f"expected training origins env in CORS error, got: {errors}",
        )

    def test_prod_validation_should_pass_when_common_cors_allowlist_exists(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ALLOWED_ORIGINS": "https://shared.example.com",
                "STORY_ALLOWED_ORIGINS": "",
                "TRAINING_ALLOWED_ORIGINS": "",
                **self._TTS_BASE_ENV,
            },
            clear=True,
        ):
            is_valid, errors, _warnings = ConfigValidator.validate("prod")

        self.assertTrue(is_valid)
        self.assertFalse(
            any("CORS allowlist" in message for message in errors),
            msg=f"unexpected CORS validation error: {errors}",
        )

    def test_prod_validation_should_pass_when_per_backend_cors_allowlists_exist(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ALLOWED_ORIGINS": "",
                "STORY_ALLOWED_ORIGINS": "https://story.example.com",
                "TRAINING_ALLOWED_ORIGINS": "https://training.example.com",
                **self._TTS_BASE_ENV,
            },
            clear=True,
        ):
            is_valid, errors, _warnings = ConfigValidator.validate("prod")

        self.assertTrue(is_valid)
        self.assertFalse(
            any("CORS allowlist" in message for message in errors),
            msg=f"unexpected CORS validation error: {errors}",
        )


if __name__ == "__main__":
    unittest.main()
