"""Request-scoped trace context helpers."""

from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import uuid4


_trace_id_var: ContextVar[str | None] = ContextVar("api_trace_id", default=None)


def set_trace_id(trace_id: str) -> Token:
    return _trace_id_var.set(str(trace_id))


def reset_trace_id(token: Token) -> None:
    _trace_id_var.reset(token)


def get_trace_id() -> str | None:
    return _trace_id_var.get()


def ensure_trace_id() -> str:
    trace_id = get_trace_id()
    if trace_id:
        return trace_id

    trace_id = str(uuid4())
    _trace_id_var.set(trace_id)
    return trace_id
