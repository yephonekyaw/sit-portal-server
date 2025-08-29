from typing import Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from ldap3 import Server, Connection

from app.db.models import User
from app.utils.auth import AuthUtils, AuthTokens
from app.utils.errors import AuthenticationError
from app.config.settings import settings


class AuthService:
    """Authentication service for handling login, logout, and token management"""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password via calling to the LDAP server"""
        # Get user by username
        stmt = select(User).where(User.username == username, User.is_active == True)
        result = self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Determine base DN based on user type
        if user.user_type.value == "student":
            base_dn = settings.LDAP_STUDENT_BASE_DN
        elif user.user_type.value == "staff":
            base_dn = settings.LDAP_STAFF_BASE_DN
        else:
            return None

        # Verify the identity via the organization LDAP server
        ldap_server = Server(settings.LDAP_SERVER)
        conn = Connection(
            ldap_server,
            user=f"uid={username},{base_dn}",
            password=password,
        )

        if not conn.bind():
            return None

        return user

    async def login_user(self, username: str, password: str) -> Tuple[AuthTokens, User]:
        """Login user and generate authentication tokens"""
        # Authenticate user
        user = await self.authenticate_user(username, password)
        if not user:
            raise AuthenticationError(
                "Invalid username or password", "INVALID_CREDENTIALS"
            )

        # Increment token version first for new login session
        user.access_token_version += 1

        # Generate token set with new version
        tokens = AuthUtils.create_token_set(
            user_id=str(user.id),
            username=user.username,
            user_type=user.user_type.value,
            token_version=user.access_token_version,
        )

        # Store refresh token in database
        user.refresh_token = tokens.refresh_token
        user.last_login = datetime.now()
        self.db.commit()

        return tokens, user

    async def refresh_tokens(self, refresh_token: str) -> Optional[AuthTokens]:
        """Refresh access token using refresh token"""
        # Verify refresh token
        payload = AuthUtils.verify_refresh_token(refresh_token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # Get user from database
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or user.refresh_token != refresh_token:
            return None

        # Generate new access token with same version (no version increment during refresh)
        new_access_token = AuthUtils.generate_access_token(
            user_id=str(user.id),
            username=user.username,
            user_type=user.user_type.value,
            token_version=user.access_token_version,
        )

        # Generate new CSRF token for the new access token
        new_csrf_token = AuthUtils.generate_csrf_token(new_access_token)

        # Keep the existing refresh token (don't generate new one unless it's expired)
        tokens = AuthTokens(
            access_token=new_access_token,
            refresh_token=refresh_token,  # Reuse existing refresh token
            csrf_token=new_csrf_token,
        )

        # No need to update refresh_token or increment access_token_version
        self.db.commit()

        return tokens

    async def logout_user(self, user_id: str) -> bool:
        """Logout user by invalidating refresh token and incrementing token version"""
        stmt = select(User).where(User.id == user_id)
        result = self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return False

        # Clear refresh token and increment access token version
        user.refresh_token = None
        user.access_token_version += 1
        self.db.commit()

        return True

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def verify_token_version(self, user_id: str, token_version: int) -> bool:
        """Verify if the token version is still valid"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        return user.access_token_version == token_version
