from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class CreateProgramRequest(BaseModel):
    """Request schema for creating a new program"""

    program_code: str = Field(
        ..., min_length=1, max_length=20, description="Unique program code"
    )
    program_name: str = Field(
        ..., min_length=1, max_length=200, description="Program name"
    )
    description: str = Field(..., min_length=1, description="Program description")
    duration_years: int = Field(..., gt=0, description="Program duration in years")
    is_active: bool = Field(default=True, description="Whether the program is active")


class UpdateProgramRequest(BaseModel):
    """Request schema for updating an existing program"""

    program_code: str = Field(
        ..., min_length=1, max_length=20, description="Unique program code"
    )
    program_name: str = Field(
        ..., min_length=1, max_length=200, description="Program name"
    )
    description: str = Field(..., min_length=1, description="Program description")
    duration_years: int = Field(..., gt=0, description="Program duration in years")


class ProgramResponse(BaseModel):
    """Response schema for program data"""

    id: uuid.UUID = Field(..., description="Program ID")
    program_code: str = Field(..., description="Program code")
    program_name: str = Field(..., description="Program name")
    description: str = Field(..., description="Program description")
    duration_years: int = Field(..., description="Program duration in years")
    is_active: bool = Field(..., description="Program active status")


class ProgramListItemResponse(BaseModel):
    """Response schema for program list item with requirement counts"""

    id: uuid.UUID = Field(..., description="Program ID")
    program_code: str = Field(..., description="Program code")
    program_name: str = Field(..., description="Program name")
    description: str = Field(..., description="Program description")
    duration_years: int = Field(..., description="Program duration in years")
    is_active: bool = Field(..., description="Program active status")
    created_at: datetime = Field(..., description="Program creation timestamp")
    updated_at: Optional[datetime] = Field(
        None, description="Program last update timestamp"
    )
    active_requirements_count: int = Field(
        ..., description="Count of active requirements"
    )
    archived_requirements_count: int = Field(
        ..., description="Count of archived requirements"
    )


class ProgramListQueryParams(BaseModel):
    """Query parameters for program list filtering and sorting"""

    is_active: Optional[bool] = Field(None, description="Filter by active status")
    program_code: Optional[str] = Field(None, description="Filter by program code")
    sort_by: Optional[
        Literal[
            "created_at", "updated_at", "program_code", "program_name", "duration_years"
        ]
    ] = Field("created_at", description="Field to sort by")
    order: Optional[Literal["asc", "desc"]] = Field("desc", description="Sort order")
