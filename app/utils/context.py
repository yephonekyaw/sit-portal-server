from contextvars import ContextVar
from typing import Optional

request_id_context: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_context.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in context."""
    request_id_context.set(request_id)
