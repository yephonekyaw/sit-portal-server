from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.services.auth_service import AuthService
from app.schemas.auth_schemas import (
    LoginRequest,
    UserResponse,
)
from app.middlewares.auth_middleware import get_current_user, AuthState
from app.utils.responses import ResponseBuilder
from app.utils.errors import AuthenticationError
from app.utils.cookies import CookieUtils

auth_router = APIRouter()


@auth_router.post("/login")
async def login(
    login_request: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_sync_session)],
):
    """
    Login user with username and password.

    Sets secure HTTP-only cookies for tokens and client-accessible CSRF token.
    """
    auth_service = AuthService(db)

    try:
        tokens, user = await auth_service.login_user(
            login_request.username, login_request.password
        )

        user_data = UserResponse(
            id=str(user.id),
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            user_type=user.user_type.value,
            is_active=user.is_active,
        )

        # Create response with user data
        response = ResponseBuilder.success(
            request=request,
            data=user_data.model_dump(by_alias=True),
            message="Login successful",
        )

        # Set authentication cookies using utility function
        CookieUtils.set_auth_cookies(response, tokens)

        return response

    except AuthenticationError:
        raise
    except Exception:
        raise AuthenticationError("Login failed")


@auth_router.post("/logout")
async def logout(
    request: Request,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_sync_session)],
):
    """Logout user and invalidate all sessions"""
    auth_service = AuthService(db)

    # Invalidate refresh token in database
    await auth_service.logout_user(current_user.user_id)

    response = ResponseBuilder.success(request=request, message="Logout successful")

    # Clear all authentication cookies using utility function
    CookieUtils.clear_auth_cookies(response)

    return response


@auth_router.get("/me")
async def get_current_user_info(
    request: Request,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_sync_session)],
):
    """Get current authenticated user information"""
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(current_user.user_id)

    if not user:
        raise AuthenticationError("User not found")

    user_data = UserResponse(
        id=str(user.id),
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        user_type=user.user_type.value,
        is_active=user.is_active,
    )

    return ResponseBuilder.success(
        request=request,
        data=user_data.model_dump(by_alias=True),
        message="User information retrieved",
    )
