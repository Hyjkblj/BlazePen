"""Shared FastAPI app factory for story and training entrypoints."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import asynccontextmanager
from logging import Logger
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.app_runtime import install_trace_context_middleware
from api.cors_config import ServiceScope, build_cors_middleware_options
from api.middleware.error_handler import install_common_exception_handlers
from database.db_manager import DatabaseManager

_RESERVED_ROOT_METADATA_KEYS = frozenset(
    {
        "message",
        "version",
        "docs",
        "service_scope",
    }
)


def _build_database_check_lifespan(
    *,
    logger: Logger,
    database_label: str,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            logger.info("正在检查%s连接...", database_label)
            db_manager = DatabaseManager()
            db_manager.check_connection()
            logger.info("%s连接检查通过", database_label)
        except Exception as exc:
            logger.error("%s连接检查失败: %s", database_label, str(exc), exc_info=True)
        yield

    return lifespan


def _install_service_metadata_routes(
    app: FastAPI,
    *,
    version: str,
    service_scope: ServiceScope,
    health_message: str,
    root_message: str,
    root_extra: Mapping[str, Any] | None = None,
) -> None:
    @app.get("/health")
    async def check_server_health():
        return JSONResponse(
            status_code=200,
            content={"status": "healthy", "message": health_message},
        )

    @app.get("/")
    async def root():
        payload: dict[str, Any] = {
            "message": root_message,
            "version": version,
            "docs": "/docs",
            # Keep scope metadata aligned with runtime/cors scope as a single source of truth.
            "service_scope": service_scope,
        }
        if root_extra:
            payload.update(dict(root_extra))
        return payload


def _validate_root_extra_metadata(root_extra: Mapping[str, Any] | None) -> None:
    if not root_extra:
        return

    conflicts = sorted(set(root_extra.keys()) & _RESERVED_ROOT_METADATA_KEYS)
    if conflicts:
        conflict_list = ", ".join(conflicts)
        raise ValueError(
            "root_extra cannot override reserved root metadata keys: "
            f"{conflict_list}"
        )


def create_api_app(
    *,
    title: str,
    description: str,
    service_scope: ServiceScope,
    logger: Logger,
    version: str = "1.0.0",
    database_label: str = "数据库",
    health_message: str = "服务正常运行",
    root_message: str,
    root_extra: Mapping[str, Any] | None = None,
) -> FastAPI:
    """Create a backend entrypoint with shared runtime wiring."""

    _validate_root_extra_metadata(root_extra)

    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=_build_database_check_lifespan(
            logger=logger,
            database_label=database_label,
        ),
    )
    app.state.service_scope = service_scope

    install_common_exception_handlers(app)
    install_trace_context_middleware(app)
    app.add_middleware(
        CORSMiddleware,
        **build_cors_middleware_options(service_scope=service_scope),
    )
    _install_service_metadata_routes(
        app,
        version=version,
        service_scope=service_scope,
        health_message=health_message,
        root_message=root_message,
        root_extra=root_extra,
    )
    return app
