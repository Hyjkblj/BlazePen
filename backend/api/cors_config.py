from __future__ import annotations

import os
from typing import Any, Literal


ServiceScope = Literal["story", "training"]

COMMON_ALLOWED_ORIGINS_ENV = "ALLOWED_ORIGINS"
SERVICE_ALLOWED_ORIGIN_ENVS: dict[ServiceScope, str] = {
    "story": "STORY_ALLOWED_ORIGINS",
    "training": "TRAINING_ALLOWED_ORIGINS",
}
DEFAULT_DEV_ALLOWED_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
)
PROD_ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
PROD_ALLOWED_HEADERS = [
    "Content-Type",
    "Authorization",
    "X-Requested-With",
    "X-Trace-Id",
]


def _parse_allowed_origins(raw_value: str) -> list[str]:
    seen: set[str] = set()
    origins: list[str] = []
    for item in raw_value.split(","):
        origin = item.strip()
        if not origin or origin in seen:
            continue
        seen.add(origin)
        origins.append(origin)
    return origins


def _service_allowed_origin_env(service_scope: ServiceScope) -> str:
    return SERVICE_ALLOWED_ORIGIN_ENVS[service_scope]


def build_allowed_origins(*, service_scope: ServiceScope, env_name: str | None = None) -> list[str]:
    """Build the allowed origins for the given backend entrypoint."""
    resolved_env_name = (env_name or os.getenv("ENV", "dev")).strip() or "dev"
    service_env_name = _service_allowed_origin_env(service_scope)
    service_origins = _parse_allowed_origins(os.getenv(service_env_name, ""))
    common_origins = _parse_allowed_origins(os.getenv(COMMON_ALLOWED_ORIGINS_ENV, ""))

    if resolved_env_name == "prod":
        allowed_origins = service_origins or common_origins
        if not allowed_origins:
            raise ValueError(
                "production requires an explicit origin allowlist: "
                f"{service_env_name} or {COMMON_ALLOWED_ORIGINS_ENV}"
            )
        return allowed_origins

    merged_origins: list[str] = []
    seen: set[str] = set()
    for origin in (*DEFAULT_DEV_ALLOWED_ORIGINS, *service_origins, *common_origins):
        if origin in seen:
            continue
        seen.add(origin)
        merged_origins.append(origin)
    return merged_origins


def build_cors_middleware_options(*, service_scope: ServiceScope) -> dict[str, Any]:
    """Build CORS options for FastAPI middleware without duplicating app wiring."""
    env_name = (os.getenv("ENV", "dev")).strip() or "dev"
    is_prod = env_name == "prod"
    return {
        "allow_origins": build_allowed_origins(service_scope=service_scope, env_name=env_name),
        "allow_credentials": True,
        "allow_methods": PROD_ALLOWED_METHODS if is_prod else ["*"],
        "allow_headers": PROD_ALLOWED_HEADERS if is_prod else ["*"],
    }
