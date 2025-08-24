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
    db: Annotated[AsyncSession, Depends(get_async_session)],
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

        # When returning the response object directly instead of returning data structure,
        # we need to use the actual response object to attach the cookies onto
        # Latter case, we can use temporal response object as FastAPI will reconstruct the
        # actual response object and attach the cookies from the temporal response before
        # sending it to the client. Visit: https://fastapi.tiangolo.com/advanced/response-cookies/#return-a-response-directly
        response = ResponseBuilder.success(
            request=request,
            data=user_data.model_dump(by_alias=True),
            message="Login successful",
        )

        # Determine environment settings
        is_production = settings.ENVIRONMENT == "production"
        cookie_domain = settings.COOKIE_DOMAIN

        # Set secure HTTP-only cookies for tokens on the actual response
        response.set_cookie(
            key="access_token",
            value=tokens.access_token,
            httponly=True,
            secure=is_production,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            domain=cookie_domain,
            path="/",
        )

        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            secure=is_production,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            domain=cookie_domain,
            path="/",
        )

        # Set client-accessible CSRF token
        response.set_cookie(
            key="csrf_token",
            value=tokens.csrf_token,
            httponly=False,  # Client needs access to this
            secure=is_production,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            domain=cookie_domain,
            path="/",
        )

        return response

    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError("Login failed")


@auth_router.post("/logout")
async def logout(
    request: Request,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Logout user and invalidate all sessions"""
    auth_service = AuthService(db)

    # Invalidate refresh token in database
    await auth_service.logout_user(current_user.user_id)

    response = ResponseBuilder.success(request=request, message="Logout successful")

    # Determine environment settings
    is_production = settings.ENVIRONMENT == "production"
    cookie_domain = settings.COOKIE_DOMAIN

    # Clear all authentication cookies with consistent settings
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=is_production,
        samesite="lax",
        domain=cookie_domain,
        path="/",
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=is_production,
        samesite="lax",
        domain=cookie_domain,
        path="/",
    )
    response.delete_cookie(
        key="csrf_token",
        httponly=False,
        secure=is_production,
        samesite="lax",
        domain=cookie_domain,
        path="/",
    )

    return response


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
