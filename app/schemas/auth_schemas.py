from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")


class UserResponse(BaseModel):
    """User response schema"""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    user_type: str = Field(..., description="User type")
    is_active: bool = Field(..., description="User active status")

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response schema"""

    user: UserResponse = Field(..., description="User information")
    message: str = Field(default="Login successful", description="Success message")


class TokenResponse(BaseModel):
    """Token response schema for refresh endpoint"""

    message: str = Field(
        default="Tokens refreshed successfully", description="Success message"
    )


class LogoutResponse(BaseModel):
    """Logout response schema"""

    message: str = Field(default="Logout successful", description="Success message")


class ErrorResponse(BaseModel):
    """Error response schema"""

    detail: str = Field(..., description="Error message")
