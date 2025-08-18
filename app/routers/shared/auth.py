from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.services.auth_service import AuthService
from app.schemas.auth_schemas import (
    LoginRequest,
    UserResponse,
)
from app.middlewares.auth_middleware import get_current_user, AuthState
from app.config.settings import settings
from app.utils.responses import ResponseBuilder
from app.utils.errors import AuthenticationError

auth_router = APIRouter()


@auth_router.post("/login")
async def login(
    login_request: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Login user with email and password.

    Sets secure HTTP-only cookies for tokens and client-accessible CSRF token.
    """
    auth_service = AuthService(db)

    try:
        tokens, user = await auth_service.login_user(
            login_request.email, login_request.password
        )

        # Set secure HTTP-only cookies for tokens
        response.set_cookie(
            key="access_token",
            value=tokens.access_token,
            httponly=True,
            secure=True,  # Use HTTPS in production
            samesite="strict",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        )

        # Set client-accessible CSRF token
        response.set_cookie(
            key="csrf_token",
            value=tokens.csrf_token,
            httponly=False,  # Client needs access to this
            secure=True,
            samesite="strict",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        user_data = UserResponse(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            user_type=user.user_type.value,
            is_active=user.is_active,
        )

        return ResponseBuilder.success(
            request=request,
            data=user_data.model_dump(),
            message="Login successful",
        )

    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError("Login failed")


@auth_router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Logout user and invalidate all sessions"""
    auth_service = AuthService(db)

    # Invalidate refresh token in database
    await auth_service.logout_user(current_user.user_id)

    # Clear all authentication cookies
    response.delete_cookie(
        key="access_token", httponly=True, secure=True, samesite="strict"
    )
    response.delete_cookie(
        key="refresh_token", httponly=True, secure=True, samesite="strict"
    )
    response.delete_cookie(
        key="csrf_token", httponly=False, secure=True, samesite="strict"
    )

    return ResponseBuilder.success(request=request, message="Logout successful")


@auth_router.get("/me")
async def get_current_user_info(
    request: Request,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get current authenticated user information"""
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(current_user.user_id)

    if not user:
        raise AuthenticationError("User not found")

    user_data = UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        user_type=user.user_type.value,
        is_active=user.is_active,
    )

    return ResponseBuilder.success(
        request=request,
        data=user_data.model_dump(),
        message="User information retrieved",
    )


@auth_router.post("/logout-all-sessions")
async def logout_all_sessions(
    request: Request,
    response: Response,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Logout from all sessions by invalidating all user tokens"""
    auth_service = AuthService(db)

    # Invalidate all sessions
    await auth_service.invalidate_all_sessions(current_user.user_id)

    # Clear cookies
    response.delete_cookie(
        key="access_token", httponly=True, secure=True, samesite="strict"
    )
    response.delete_cookie(
        key="refresh_token", httponly=True, secure=True, samesite="strict"
    )
    response.delete_cookie(
        key="csrf_token", httponly=False, secure=True, samesite="strict"
    )

    return ResponseBuilder.success(
        request=request, message="Logged out from all sessions"
    )
