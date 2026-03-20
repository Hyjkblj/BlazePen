"""API response helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi.responses import JSONResponse

from api.error_codes import INTERNAL_ERROR, NOT_FOUND, VALIDATION_ERROR
from api.request_context import ensure_trace_id


def build_success_payload(data: Any = None, message: str = "success") -> Dict[str, Any]:
    """Build a success payload that can still be validated by response_model."""

    return {
        "code": 200,
        "message": message,
        "data": data,
    }


def build_error_payload(
    *,
    code: int,
    message: str,
    error_code: str,
    data: Any = None,
    details: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a stable error envelope."""

    resolved_trace_id = trace_id or ensure_trace_id()
    return {
        "code": code,
        "message": message,
        "data": data,
        "error": {
            "code": error_code,
            "details": details or {},
            "traceId": resolved_trace_id,
        },
    }


def _default_error_code_from_status(status_code: int) -> str:
    if status_code == 404:
        return NOT_FOUND
    if 400 <= status_code < 500:
        return VALIDATION_ERROR
    return INTERNAL_ERROR


def success_response(data: Any = None, message: str = "success") -> JSONResponse:
    """Return a successful JSON response."""

    return JSONResponse(
        status_code=200,
        content=build_success_payload(data=data, message=message),
    )


def error_response(
    code: int = 400,
    message: str = "error",
    data: Any = None,
    error: Optional[Dict[str, Any]] = None,
    *,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> JSONResponse:
    """Return an error JSON response with a stable error contract."""

    structured_error = dict(error or {})
    resolved_error_code = str(
        structured_error.pop("code", error_code or _default_error_code_from_status(code))
    )
    resolved_details = dict(details or {})
    legacy_details = structured_error.pop("details", None)
    if isinstance(legacy_details, dict):
        resolved_details.update(legacy_details)
    if structured_error:
        resolved_details.setdefault("legacy", structured_error)

    return JSONResponse(
        status_code=code,
        content=build_error_payload(
            code=code,
            message=message,
            error_code=resolved_error_code,
            data=data,
            details=resolved_details,
            trace_id=trace_id,
        ),
    )


def not_found_response(
    message: str = "resource not found",
    *,
    error_code: str = NOT_FOUND,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Return a 404 JSON response."""

    return error_response(code=404, message=message, error_code=error_code, details=details)


def unauthorized_response(message: str = "unauthorized") -> JSONResponse:
    """Return a 401 JSON response."""

    return error_response(code=401, message=message, error_code="UNAUTHORIZED")


def forbidden_response(
    message: str = "forbidden",
    *,
    error_code: str = "FORBIDDEN",
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Return a 403 JSON response."""

    return error_response(
        code=403,
        message=message,
        error_code=error_code,
        details=details,
    )


def server_error_response(message: str = "internal server error") -> JSONResponse:
    """Return a 500 JSON response."""

    return error_response(code=500, message=message, error_code=INTERNAL_ERROR)
