from typing import Optional, Callable
from fastapi import Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from typing import cast

from app.utils.auth import AuthUtils
from app.services.auth_service import AuthService
from app.db.session import get_sync_session
from app.utils.errors import AuthenticationError, AuthorizationError
from app.utils.responses import ResponseBuilder
from app.utils.logging import get_logger
from app.utils.cookies import CookieUtils

logger = get_logger()


class AuthState:
    """Authentication state to be stored in request.state"""

    def __init__(
        self,
        user_id: str,
        username: str,
        user_type: str,
        token_version: int,
        is_authenticated: bool = True,
        tokens_refreshed: bool = False,
    ):
        self.user_id = user_id
        self.username = username
        self.user_type = user_type
        self.token_version = token_version
        self.is_authenticated = is_authenticated
        self.tokens_refreshed = tokens_refreshed


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for JWT token validation and refresh"""

    # Paths that don't require authentication
    EXCLUDED_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/shared/auth/login",
        "/api/v1/shared/health",
        "/webhook/v1",
    }

    def __init__(self, app, excluded_paths: Optional[set] = None):
        super().__init__(app)
        if excluded_paths:
            self.EXCLUDED_PATHS.update(excluded_paths)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware"""

        # Skip authentication for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        try:
            # Extract and validate tokens, with automatic refresh if needed
            auth_result = await self._authenticate_request_with_refresh(request)

            if auth_result:
                # Set authentication state
                request.state.auth = auth_result
                response = await call_next(request)

                # Set new cookies if tokens were refreshed
                if auth_result.tokens_refreshed:
                    await self._set_refreshed_cookies(request, response)

                return response
            else:
                response = ResponseBuilder.error(
                    request=request,
                    message="Invalid or expired authentication",
                    error_code="UNAUTHORIZED",
                    status_code=401,
                )
                return response

        except Exception as e:
            response = ResponseBuilder.error(
                request=request,
                message="Authentication failed",
                error_code="AUTH_ERROR",
                status_code=401,
            )
            return response

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication"""
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)

    async def _authenticate_request_with_refresh(
        self, request: Request
    ) -> Optional[AuthState]:
        """Authenticate request with automatic token refresh if needed"""

        # Get tokens from cookies and headers
        csrf_token = CookieUtils.extract_bearer_token(
            request.headers.get("authorization")
        ) or request.cookies.get("csrf_token")
        access_token = request.cookies.get("access_token")
        refresh_token = request.cookies.get("refresh_token")

        # If we don't have a refresh token, we can't authenticate
        if not refresh_token:
            return None

        # Check if we have valid access and csrf tokens
        has_valid_tokens = access_token and csrf_token
        tokens_expired = False

        if has_valid_tokens:
            # Check if access token is expired or will expire soon
            tokens_expired = (
                AuthUtils.is_token_expired(access_token, buffer_minutes=2)
                if access_token
                else True
            )

        # If we don't have tokens or they're expired, try to refresh
        if not has_valid_tokens or tokens_expired:
            refreshed_tokens = await self._refresh_tokens_automatically(request)
            if refreshed_tokens:
                # Use new tokens
                access_token = refreshed_tokens.access_token
                csrf_token = refreshed_tokens.csrf_token
                # Store new tokens in request for later cookie setting
                request.state.new_tokens = refreshed_tokens
                tokens_refreshed = True
            else:
                # Refresh failed, authentication invalid
                return None
        else:
            tokens_refreshed = False

        # Verify CSRF token against access token
        if not AuthUtils.verify_csrf_token(
            cast(str, access_token), cast(str, csrf_token)
        ):
            return None

        # Verify access token
        payload = AuthUtils.verify_access_token(cast(str, access_token))
        if not payload:
            return None

        # Extract user information
        user_id = payload.get("sub")
        username = payload.get("username")
        user_type = payload.get("user_type")
        token_version = payload.get("token_version", 0)

        if not all([user_id, username, user_type]):
            return None

        # Verify token version with database
        for session in get_sync_session():
            auth_service = AuthService(session)
            is_valid = await auth_service.verify_token_version(
                str(user_id), token_version
            )
            if not is_valid:
                return None

        return AuthState(
            user_id=str(user_id),
            username=str(username),
            user_type=str(user_type),
            token_version=token_version,
            tokens_refreshed=tokens_refreshed,
        )

    async def _refresh_tokens_automatically(self, request: Request):
        """Automatically refresh tokens using refresh token from cookies"""
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            return None

        try:
            # Use auth service to refresh tokens
            for session in get_sync_session():
                auth_service = AuthService(session)
                new_tokens = await auth_service.refresh_tokens(refresh_token)
                return new_tokens
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")
            return None

    async def _set_refreshed_cookies(self, request: Request, response: Response):
        """Set new cookies after token refresh"""
        new_tokens = getattr(request.state, "new_tokens", None)
        if not new_tokens:
            return

        CookieUtils.set_auth_cookies(response, new_tokens)


class JWTBearer(HTTPBearer):
    """Custom JWT Bearer authentication for dependency injection"""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        """Validate JWT token from request"""
        credentials = await super().__call__(request)

        if not credentials:
            raise AuthenticationError(
                "Invalid authorization credentials", "INVALID_CREDENTIALS"
            )

        if not credentials.scheme == "Bearer":
            raise AuthenticationError("Invalid authentication scheme", "INVALID_SCHEME")

        # Verify token
        payload = AuthUtils.verify_access_token(credentials.credentials)
        if not payload:
            raise AuthenticationError("Invalid or expired token", "INVALID_TOKEN")

        return credentials


# Dependency for getting current user from request state
def get_current_user(request: Request) -> AuthState:
    """Dependency to get current authenticated user from request state"""
    auth_state = getattr(request.state, "auth", None)

    if not auth_state or not auth_state.is_authenticated:
        raise AuthenticationError("Not authenticated", "NOT_AUTHENTICATED")

    return auth_state


# Dependency for requiring specific user types
def require_user_type(*allowed_types: str):
    """Create dependency that requires specific user types"""
    from fastapi import Depends

    def check_user_type(
        current_user: AuthState = Depends(get_current_user),
    ) -> AuthState:
        if current_user.user_type not in allowed_types:
            raise AuthorizationError(
                "Insufficient permissions", "INSUFFICIENT_PERMISSIONS"
            )
        return current_user

    return check_user_type


# Pre-defined dependencies for common user types
require_student = require_user_type("student")
require_staff = require_user_type("staff")
require_any_user = require_user_type("student", "staff")
