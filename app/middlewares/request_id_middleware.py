from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from typing import Callable
import uuid
from app.utils.context import set_request_id

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            request_id = str(uuid.UUID(request.headers.get(REQUEST_ID_HEADER)))
        except (ValueError, TypeError):
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        # Set in context variable for global access to logger
        set_request_id(request_id)

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
