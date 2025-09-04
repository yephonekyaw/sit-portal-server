from datetime import datetime
import uuid

from pydantic import Field

from app.schemas.camel_base_model import CamelCaseBaseModel as BaseModel


class GetAcademicYearsItem(BaseModel):
    """Response schema for academic year list item"""

    id: uuid.UUID = Field(..., description="Academic year ID")
    year_code: int = Field(..., description="Academic year code")
    start_date: datetime = Field(..., description="Academic year start date")
    end_date: datetime = Field(..., description="Academic year end date")
    is_current: bool = Field(..., description="Whether the academic year is current")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
