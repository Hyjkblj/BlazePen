"""Global API exception handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.error_codes import INTERNAL_ERROR, VALIDATION_ERROR
from api.exceptions import ServiceException
from api.request_context import ensure_trace_id
from api.response import build_error_payload

logger = logging.getLogger(__name__)


def _normalize_validation_error_item(error: dict[str, Any]) -> dict[str, Any]:
    raw_loc = list(error.get("loc") or [])
    source = str(raw_loc[0]) if raw_loc else "request"
    field_parts = [str(part) for part in raw_loc[1:]]
    field = ".".join(field_parts) if field_parts else None
    normalized = {
        "source": source,
        "type": str(error.get("type") or "validation_error"),
        "message": str(error.get("msg") or "request validation failed"),
    }
    if field is not None:
        normalized["field"] = field
    return normalized


async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation failures with the common error contract."""

    trace_id = ensure_trace_id()
    normalized_errors = [_normalize_validation_error_item(item) for item in exc.errors()]
    logger.warning(
        "request validation failed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "validation_errors": normalized_errors,
            "trace_id": trace_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_error_payload(
            code=422,
            message="request validation failed",
            error_code=VALIDATION_ERROR,
            details={
                "path": request.url.path,
                "method": request.method,
                "errors": normalized_errors,
            },
            trace_id=trace_id,
        ),
    )


async def service_exception_handler(request: Request, exc: ServiceException):
    """Handle service-layer exceptions with the common error contract."""

    trace_id = ensure_trace_id()
    logger.error(
        "service exception: %s",
        exc.message,
        extra={
            "http_code": exc.code,
            "error_code": exc.error_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "trace_id": trace_id,
        },
    )
    return JSONResponse(
        status_code=exc.code,
        content=build_error_payload(
            code=exc.code,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
            trace_id=trace_id,
        ),
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions with the common error contract."""

    trace_id = ensure_trace_id()
    logger.exception(
        "unhandled exception: %s",
        str(exc),
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "trace_id": trace_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_payload(
            code=500,
            message="internal server error",
            error_code=INTERNAL_ERROR,
            details={"exception_type": type(exc).__name__},
            trace_id=trace_id,
        ),
    )


def install_common_exception_handlers(app: FastAPI) -> None:
    """Install the shared API exception handlers on an app instance."""

    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(ServiceException, service_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
