"""Runtime configuration validation helpers."""

from __future__ import annotations

import os
from typing import List, Tuple

from api.cors_config import COMMON_ALLOWED_ORIGINS_ENV, SERVICE_ALLOWED_ORIGIN_ENVS
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigValidator:
    """Validate environment configuration before runtime."""

    # Required in production.
    REQUIRED_PROD_CONFIGS = {
        "VOLCENGINE_TTS_APP_ID": "Volcengine TTS app id",
        "VOLCENGINE_TTS_ACCESS_TOKEN": "Volcengine TTS access token",
        "VOLCENGINE_TTS_SECRET_KEY": "Volcengine TTS secret key",
    }

    # Optional but strongly recommended.
    RECOMMENDED_CONFIGS = {
        "VOLCENGINE_ARK_API_KEY": "Volcengine ARK API key (text/image generation)",
        "DASHSCOPE_API_KEY": "DashScope API key (optional provider)",
    }

    @classmethod
    def validate(cls, env: str | None = None) -> Tuple[bool, List[str], List[str]]:
        """Return `(is_valid, errors, warnings)` for the target environment."""

        resolved_env = (env or os.getenv("ENV", "dev")).lower()
        errors: list[str] = []
        warnings: list[str] = []

        if resolved_env == "prod":
            cls._validate_prod_required_configs(errors)
            cls._validate_prod_cors_allowlist(errors)

        cls._validate_recommended_configs(warnings)
        cls._validate_ai_provider_presence(warnings)
        cls._validate_tts_provider_config(env_name=resolved_env, errors=errors, warnings=warnings)

        return len(errors) == 0, errors, warnings

    @classmethod
    def print_validation_report(cls, env: str | None = None) -> bool:
        """Log validation details and return whether validation passed."""

        is_valid, errors, warnings = cls.validate(env)
        resolved_env = (env or os.getenv("ENV", "dev")).lower()

        logger.info("Configuration validation report (env=%s)", resolved_env)
        logger.info("=" * 60)

        if errors:
            logger.error("Found %s error(s):", len(errors))
            for error in errors:
                logger.error("  [error] %s", error)

        if warnings:
            logger.warning("Found %s warning(s):", len(warnings))
            for warning in warnings:
                logger.warning("  [warn] %s", warning)

        if not errors and not warnings:
            logger.info("Configuration validation passed with no warnings.")
        elif not errors:
            logger.info("Configuration validation passed with warnings.")
        else:
            logger.error("Configuration validation failed.")

        logger.info("=" * 60)
        return is_valid

    @classmethod
    def _validate_prod_required_configs(cls, errors: list[str]) -> None:
        for key, description in cls.REQUIRED_PROD_CONFIGS.items():
            if not os.getenv(key, "").strip():
                errors.append(f"{key} ({description}) is not set")

    @staticmethod
    def _validate_prod_cors_allowlist(errors: list[str]) -> None:
        story_origins_env = SERVICE_ALLOWED_ORIGIN_ENVS["story"]
        training_origins_env = SERVICE_ALLOWED_ORIGIN_ENVS["training"]

        common_allowed_origins = os.getenv(COMMON_ALLOWED_ORIGINS_ENV, "").strip()
        story_allowed_origins = os.getenv(story_origins_env, "").strip()
        training_allowed_origins = os.getenv(training_origins_env, "").strip()

        if not common_allowed_origins and (not story_allowed_origins or not training_allowed_origins):
            errors.append(
                "Production requires CORS allowlist: "
                f"{COMMON_ALLOWED_ORIGINS_ENV}, or both "
                f"{story_origins_env} + {training_origins_env}"
            )

    @classmethod
    def _validate_recommended_configs(cls, warnings: list[str]) -> None:
        for key, description in cls.RECOMMENDED_CONFIGS.items():
            if not os.getenv(key, "").strip():
                warnings.append(f"{key} ({description}) is not set")

    @staticmethod
    def _validate_ai_provider_presence(warnings: list[str]) -> None:
        ai_provider_keys = [
            "VOLCENGINE_ARK_API_KEY",
            "DASHSCOPE_API_KEY",
            "OPENAI_API_KEY",
            "ZHIPU_API_KEY",
            "BAIDU_API_KEY",
        ]
        if not any(os.getenv(key, "").strip() for key in ai_provider_keys):
            warnings.append("No AI provider key configured; text generation may be unavailable")

    @staticmethod
    def _validate_tts_provider_config(
        *,
        env_name: str,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        tts_provider = os.getenv("TTS_PROVIDER", "volcengine")
        if tts_provider != "volcengine":
            return

        tts_keys = [
            "VOLCENGINE_TTS_APP_ID",
            "VOLCENGINE_TTS_ACCESS_TOKEN",
            "VOLCENGINE_TTS_SECRET_KEY",
        ]
        has_tts_config = all(os.getenv(key, "").strip() for key in tts_keys)
        if has_tts_config:
            return

        message = (
            "TTS provider is volcengine but TTS credentials are incomplete: "
            "VOLCENGINE_TTS_APP_ID/VOLCENGINE_TTS_ACCESS_TOKEN/VOLCENGINE_TTS_SECRET_KEY"
        )
        if env_name == "prod":
            errors.append(message)
        else:
            warnings.append(message)


def validate_config_on_startup() -> None:
    """Validate current environment on startup.

    Production startup fails fast when required config is invalid.
    """

    env = os.getenv("ENV", "dev").lower()
    is_valid, errors, _warnings = ConfigValidator.validate(env)

    if env == "prod" and not is_valid:
        error_msg = "Production configuration validation failed:\n" + "\n".join(
            f"  - {error}" for error in errors
        )
        raise ValueError(error_msg)

    ConfigValidator.print_validation_report(env)
