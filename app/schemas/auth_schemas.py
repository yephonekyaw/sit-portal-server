from pydantic import Field
from .camel_base_model import CamelCaseBaseModel as BaseModel


class LoginRequest(BaseModel):
    """Login request schema"""

    username: str = Field(..., description="Username")
    password: str = Field(..., min_length=1, description="Password")
    remember_me: bool = Field(True, description="Remember me option")


class UserResponse(BaseModel):
    """User response schema"""

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    user_type: str = Field(..., description="User type")
    is_active: bool = Field(..., description="User active status")

    class Config:
        from_attributes = True
