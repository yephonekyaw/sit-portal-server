from typing import Optional
from fastapi import Response
from app.config.settings import settings
from app.utils.auth import AuthTokens


class CookieUtils:
    """Utility class for managing authentication cookies"""

    @staticmethod
    def _get_cookie_settings() -> dict:
        """Get common cookie settings based on environment"""
        is_production = settings.ENVIRONMENT == "production"
        return {
            "secure": is_production,
            "samesite": "lax",
            "domain": settings.COOKIE_DOMAIN,
            "path": "/",
        }

    @staticmethod
    def set_auth_cookies(response: Response, tokens: AuthTokens) -> None:
        """Set all authentication cookies on response"""
        cookie_settings = CookieUtils._get_cookie_settings()

        # Set secure HTTP-only access token
        response.set_cookie(
            key="access_token",
            value=tokens.access_token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            **cookie_settings,
        )

        # Set secure HTTP-only refresh token
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            **cookie_settings,
        )

        # Set client-accessible CSRF token
        response.set_cookie(
            key="csrf_token",
            value=tokens.csrf_token,
            httponly=False,  # Client needs access to this
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            **cookie_settings,
        )

    @staticmethod
    def clear_auth_cookies(response: Response) -> None:
        """Clear all authentication cookies from response"""
        cookie_settings = CookieUtils._get_cookie_settings()

        # Clear access token
        response.delete_cookie(
            key="access_token",
            httponly=True,
            **cookie_settings,
        )

        # Clear refresh token
        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            **cookie_settings,
        )

        # Clear CSRF token
        response.delete_cookie(
            key="csrf_token",
            httponly=False,
            **cookie_settings,
        )

    @staticmethod
    def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
        """Extract Bearer token from Authorization header"""
        if not authorization_header:
            return None

        if not authorization_header.startswith("Bearer "):
            return None

        return authorization_header[7:]  # Remove "Bearer " prefix