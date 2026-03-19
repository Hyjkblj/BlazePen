"""Global API exception handlers."""

from __future__ import annotations

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.error_codes import INTERNAL_ERROR
from api.exceptions import ServiceException
from api.request_context import ensure_trace_id
from api.response import build_error_payload

logger = logging.getLogger(__name__)


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
