from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import uuid
import jwt
import secrets
from passlib.context import CryptContext
from passlib.hash import bcrypt
from app.config.settings import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthTokens:
    """Container for authentication tokens"""

    def __init__(self, access_token: str, refresh_token: str, csrf_token: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.csrf_token = csrf_token


class AuthUtils:
    """Authentication utilities for JWT token management and password hashing"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def generate_access_token(
        user_id: str, email: str, user_type: str, token_version: int = 0
    ) -> str:
        """Generate JWT access token with user information"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": str(user_id),  # Subject (user ID)
            "email": email,
            "user_type": user_type,
            "token_version": token_version,
            "iat": now,  # Issued at
            "exp": expire,  # Expiration
            "jti": str(uuid.uuid4()),  # JWT ID for uniqueness
        }

        return jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

    @staticmethod
    def generate_refresh_token(user_id: str) -> str:
        """Generate JWT refresh token"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4()),
        }

        return jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

    @staticmethod
    def generate_csrf_token(access_token: str) -> str:
        """Generate CSRF token by hashing the access token"""
        # Use bcrypt to hash the access token for CSRF protection
        return bcrypt.hash(access_token)

    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode access token"""
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )

            # Ensure it's not a refresh token
            if payload.get("type") == "refresh":
                return None

            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode refresh token"""
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )

            # Ensure it's a refresh token
            if payload.get("type") != "refresh":
                return None

            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def verify_csrf_token(access_token: str, csrf_token: str) -> bool:
        """Verify CSRF token against access token"""
        try:
            return bcrypt.verify(access_token, csrf_token)
        except Exception:
            return False

    @staticmethod
    def create_token_set(
        user_id: str, email: str, user_type: str, token_version: int = 0
    ) -> AuthTokens:
        """Create a complete set of authentication tokens"""
        access_token = AuthUtils.generate_access_token(
            user_id, email, user_type, token_version
        )
        refresh_token = AuthUtils.generate_refresh_token(user_id)
        csrf_token = AuthUtils.generate_csrf_token(access_token)

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            csrf_token=csrf_token,
        )

    @staticmethod
    def generate_secure_token() -> str:
        """Generate a cryptographically secure random token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def is_token_expired(token: str, buffer_minutes: int = 2) -> bool:
        """Check if token is expired or will expire within buffer time"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False},  # Don't raise error for expired token
            )

            exp_timestamp = payload.get("exp")
            if not exp_timestamp:
                return True

            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            buffer_time = datetime.now(timezone.utc) + timedelta(minutes=buffer_minutes)

            return exp_datetime <= buffer_time
        except Exception:
            return True  # Treat any error as expired

    @staticmethod
    def get_token_expiry(token: str) -> Optional[datetime]:
        """Get token expiration time"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False},
            )

            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            return None
        except Exception:
            return None
