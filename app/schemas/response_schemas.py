from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, List
import uuid

from pydantic import Field

from app.schemas.camel_base_model import CamelCaseBaseModel as BaseModel


class ResponseStatus(str, Enum):
    """Response status enumeration"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there's a next page")
    has_prev: bool = Field(..., description="Whether there's a previous page")
    next_page: Optional[int] = Field(None, description="Next page number")
    prev_page: Optional[int] = Field(None, description="Previous page number")


class ApiResponse(BaseModel):
    """Standardized API response format"""

    success: bool = Field(..., description="Whether the request was successful")
    status: ResponseStatus = Field(..., description="Response status")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(default=None, description="Response data")
    meta: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )
    pagination: Optional[PaginationMeta] = Field(
        default=None, description="Pagination information"
    )
    errors: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Error details"
    )
    warnings: Optional[List[str]] = Field(default=None, description="Warning messages")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp",
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request identifier",
    )
    path: Optional[str] = Field(default=None, description="Request path")
    version: str = Field(default="1.0", description="API version")
