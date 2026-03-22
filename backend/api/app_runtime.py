"""Shared FastAPI runtime installers for API entrypoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request

from api.request_context import reset_trace_id, set_trace_id


_TRACE_CONTEXT_INSTALLED_FLAG = "_trace_context_installed"


def install_trace_context_middleware(app: FastAPI) -> None:
    """Attach the shared request trace context middleware to an app once."""

    if getattr(app.state, _TRACE_CONTEXT_INSTALLED_FLAG, False):
        return

    @app.middleware("http")
    async def bind_trace_id(request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id") or str(uuid4())
        token = set_trace_id(trace_id)
        request.state.trace_id = trace_id
        try:
            response = await call_next(request)
        finally:
            reset_trace_id(token)

        response.headers["X-Trace-Id"] = trace_id
        return response

    setattr(app.state, _TRACE_CONTEXT_INSTALLED_FLAG, True)
