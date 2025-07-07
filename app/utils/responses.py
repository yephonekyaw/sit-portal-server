from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from enum import Enum
import uuid


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
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp",
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request identifier",
    )
    path: Optional[str] = Field(default=None, description="Request path")
    version: str = Field(default="1.0", description="API version")


class ResponseBuilder:
    """Builder class for creating standardized responses"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Request successful",
        meta: Optional[Dict[str, Any]] = None,
        pagination: Optional[PaginationMeta] = None,
        status_code: int = status.HTTP_200_OK,
        path: Optional[str] = None,
    ) -> JSONResponse:
        """Create a success response"""
        response = ApiResponse(
            success=True,
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data,
            meta=meta,
            pagination=pagination,
            path=path,
        )
        return JSONResponse(
            status_code=status_code, content=response.model_dump(exclude_none=True)
        )

    @staticmethod
    def error(
        message: str = "An error occurred",
        errors: Optional[List[Dict[str, Any]]] = None,
        error_code: Optional[str] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        data: Any = None,
        meta: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None,
    ) -> JSONResponse:
        """Create an error response"""
        response_meta = meta or {}
        if error_code:
            response_meta["error_code"] = error_code

        response = ApiResponse(
            success=False,
            status=ResponseStatus.ERROR,
            message=message,
            data=data,
            meta=response_meta if response_meta else None,
            errors=errors,
            path=path,
        )
        return JSONResponse(
            status_code=status_code, content=response.model_dump(exclude_none=True)
        )

    @staticmethod
    def warning(
        data: Any = None,
        message: str = "Request completed with warnings",
        warnings: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_200_OK,
        path: Optional[str] = None,
    ) -> JSONResponse:
        """Create a warning response"""
        response = ApiResponse(
            success=True,
            status=ResponseStatus.WARNING,
            message=message,
            data=data,
            meta=meta,
            warnings=warnings,
            path=path,
        )
        return JSONResponse(
            status_code=status_code, content=response.model_dump(exclude_none=True)
        )

    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        per_page: int,
        total: int,
        message: str = "Data retrieved successfully",
        meta: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None,
    ) -> JSONResponse:
        """Create a paginated response"""
        total_pages = (total + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1

        pagination = PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
            next_page=page + 1 if has_next else None,
            prev_page=page - 1 if has_prev else None,
        )

        return ResponseBuilder.success(
            data=data,
            message=message,
            meta=meta,
            pagination=pagination,
            path=path,
        )
