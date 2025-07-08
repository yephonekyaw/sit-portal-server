import contextvars
import threading
import uuid
from typing import Optional, Dict, Any


class RequestContext:
    """Utility class for managing request context globally across the application."""

    def __init__(self):
        self._request_id_context: contextvars.ContextVar[Optional[str]] = (
            contextvars.ContextVar("request_id", default=None)
        )
        self._user_id_context: contextvars.ContextVar[Optional[str]] = (
            contextvars.ContextVar("user_id", default=None)
        )

    def set_request_id(self, request_id: Optional[str] = None) -> str:
        """Set the request ID in the current context."""
        request_id = request_id or str(uuid.uuid4())
        self._request_id_context.set(request_id)
        return request_id

    def get_request_id(self) -> Optional[str]:
        """Get the current request ID from context."""
        return self._request_id_context.get()

    def set_user_id(self, user_id: Optional[str]) -> None:
        """Set the user ID in the current context."""
        user_id = user_id or str(uuid.uuid4())
        self._user_id_context.set(user_id)

    def get_user_id(self) -> Optional[str]:
        """Get the current user ID from context."""
        return self._user_id_context.get()

    def clear_context(self) -> None:
        self._request_id_context.set(None)
        self._user_id_context.set(None)

    def get_all_context(self) -> Dict[str, Any]:
        """Get all context data as a dictionary."""
        return {
            "request_id": self.get_request_id(),
            "user_id": self.get_user_id(),
        }
