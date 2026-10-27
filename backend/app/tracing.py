"""Request-local tracing; never store bearer tokens or uploaded content."""
from contextvars import ContextVar

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
