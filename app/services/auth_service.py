from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import User
from app.utils.auth import AuthUtils, AuthTokens
from app.utils.errors import AuthenticationError


class AuthService:
    """Authentication service for handling login, logout, and token management"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password"""
        # Get user by email
        stmt = select(User).where(User.email == email, User.is_active == True)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Verify password
        if not AuthUtils.verify_password(password, user.password_hash):
            return None

        return user

    async def login_user(self, email: str, password: str) -> Tuple[AuthTokens, User]:
        """Login user and generate authentication tokens"""
        # Authenticate user
        user = await self.authenticate_user(email, password)
        if not user:
            raise AuthenticationError(
                "Invalid email or password", "INVALID_CREDENTIALS"
            )

        # Generate token set
        tokens = AuthUtils.create_token_set(
            user_id=str(user.id),
            email=user.email,
            user_type=user.user_type.value,
            token_version=user.access_token_version,
        )

        # Store refresh token in database
        user.refresh_token = tokens.refresh_token
        user.last_login = datetime.now()
        await self.db.commit()

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
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or user.refresh_token != refresh_token:
            return None

        # Generate new token set
        tokens = AuthUtils.create_token_set(
            user_id=str(user.id),
            email=user.email,
            user_type=user.user_type.value,
            token_version=user.access_token_version,
        )

        # Update refresh token in database
        user.refresh_token = tokens.refresh_token
        await self.db.commit()

        return tokens

    async def logout_user(self, user_id: str) -> bool:
        """Logout user by invalidating refresh token and incrementing token version"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return False

        # Clear refresh token and increment access token version
        user.refresh_token = None
        user.access_token_version += 1
        await self.db.commit()

        return True

    async def invalidate_all_sessions(self, user_id: str) -> bool:
        """Invalidate all user sessions by clearing refresh token and incrementing version"""
        return await self.logout_user(user_id)

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def verify_token_version(self, user_id: str, token_version: int) -> bool:
        """Verify if the token version is still valid"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        return user.access_token_version == token_version
