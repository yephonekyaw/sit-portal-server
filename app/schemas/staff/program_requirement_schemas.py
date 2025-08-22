from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import uuid

from app.db.models import ProgReqRecurrenceType


class CreateProgramRequirementRequest(BaseModel):
    """Request schema for creating a new program requirement"""

    program_id: uuid.UUID = Field(..., description="Program ID for the requirement")
    cert_type_id: uuid.UUID = Field(..., description="Certificate type ID")
    name: str = Field(..., min_length=1, max_length=200, description="Requirement name")
    target_year: int = Field(..., ge=1, le=10, description="Target year (1-10)")
    deadline_day: int = Field(..., ge=1, le=31, description="Deadline day (1-31)")
    deadline_month: int = Field(..., ge=1, le=12, description="Deadline month (1-12)")
    grace_period_days: Optional[int] = Field(
        default=7, ge=0, le=365, description="Grace period in days"
    )
    notification_days_before_deadline: Optional[int] = Field(
        default=90,
        ge=0,
        le=365,
        description="Days before deadline to send notifications",
    )
    is_mandatory: bool = Field(
        default=True, description="Whether requirement is mandatory"
    )
    is_active: bool = Field(default=True, description="Whether requirement is active")
    special_instruction: Optional[str] = Field(
        default=None, description="Special instructions for the requirement"
    )
    recurrence_type: ProgReqRecurrenceType = Field(
        default=ProgReqRecurrenceType.ANNUAL,
        description="How often the requirement recurs",
    )
    effective_from_year: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Academic year from which requirement is effective",
    )
    effective_until_year: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Academic year until which requirement is effective",
    )
    months_before_deadline: Optional[int] = Field(
        default=None,
        ge=1,
        le=6,
        description="Months before deadline to create schedules for cron jobs (1-6)",
    )

    @field_validator("deadline_day", "deadline_month")
    @classmethod
    def validate_date_components(cls, v: int, info) -> int:
        """Validate that deadline day/month form a valid date"""
        if info.field_name == "deadline_day" and v > 31:
            raise ValueError("Deadline day must be between 1 and 31")
        if info.field_name == "deadline_month" and v > 12:
            raise ValueError("Deadline month must be between 1 and 12")
        return v

    def model_post_init(self, __context) -> None:
        """Validate conditional field dependencies after model initialization"""
        # Validate deadline date is valid
        try:
            deadline_date = date(2000, self.deadline_month, self.deadline_day)
        except ValueError as e:
            raise ValueError(f"Invalid deadline date: {e}")

        # Validate effective year range
        if (
            self.effective_from_year is not None
            and self.effective_until_year is not None
        ):
            if self.effective_from_year > self.effective_until_year:
                raise ValueError(
                    "effective_from_year cannot be later than effective_until_year"
                )


class UpdateProgramRequirementRequest(BaseModel):
    """Request schema for updating an existing program requirement"""

    name: str = Field(..., min_length=1, max_length=200, description="Requirement name")
    target_year: int = Field(..., ge=1, le=10, description="Target year (1-10)")
    deadline_day: int = Field(..., ge=1, le=31, description="Deadline day (1-31)")
    deadline_month: int = Field(..., ge=1, le=12, description="Deadline month (1-12)")
    grace_period_days: Optional[int] = Field(
        default=7, ge=0, le=365, description="Grace period in days"
    )
    notification_days_before_deadline: Optional[int] = Field(
        default=90,
        ge=0,
        le=365,
        description="Days before deadline to send notifications",
    )
    is_mandatory: bool = Field(
        default=True, description="Whether requirement is mandatory"
    )
    special_instruction: Optional[str] = Field(
        default=None, description="Special instructions for the requirement"
    )
    recurrence_type: ProgReqRecurrenceType = Field(
        default=ProgReqRecurrenceType.ANNUAL,
        description="How often the requirement recurs",
    )
    effective_from_year: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Academic year from which requirement is effective",
    )
    effective_until_year: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Academic year until which requirement is effective",
    )
    months_before_deadline: Optional[int] = Field(
        default=None,
        ge=1,
        le=6,
        description="Months before deadline to create schedules for cron jobs (1-6)",
    )

    @field_validator("deadline_day", "deadline_month")
    @classmethod
    def validate_date_components(cls, v: int, info) -> int:
        """Validate that deadline day/month form a valid date"""
        if info.field_name == "deadline_day" and v > 31:
            raise ValueError("Deadline day must be between 1 and 31")
        if info.field_name == "deadline_month" and v > 12:
            raise ValueError("Deadline month must be between 1 and 12")
        return v

    def model_post_init(self, __context) -> None:
        """Validate conditional field dependencies after model initialization"""
        # Validate deadline date is valid
        try:
            deadline_date = date(2000, self.deadline_month, self.deadline_day)
        except ValueError as e:
            raise ValueError(f"Invalid deadline date: {e}")

        # Validate effective year range
        if (
            self.effective_from_year is not None
            and self.effective_until_year is not None
        ):
            if self.effective_from_year > self.effective_until_year:
                raise ValueError(
                    "effective_from_year cannot be later than effective_until_year"
                )


class ProgramRequirementResponse(BaseModel):
    """Response schema for program requirement data"""

    id: uuid.UUID = Field(..., description="Requirement ID")
    program_id: uuid.UUID = Field(..., description="Program ID")
    cert_type_id: uuid.UUID = Field(..., description="Certificate type ID")
    name: str = Field(..., description="Requirement name")
    target_year: int = Field(..., description="Target year")
    deadline_date: date = Field(..., description="Deadline date")
    grace_period_days: int = Field(..., description="Grace period in days")
    notification_days_before_deadline: int = Field(
        ..., description="Days before deadline to start sending notifications"
    )
    is_mandatory: bool = Field(..., description="Whether requirement is mandatory")
    is_active: bool = Field(..., description="Whether requirement is active")
    special_instruction: Optional[str] = Field(None, description="Special instructions")
    recurrence_type: ProgReqRecurrenceType = Field(..., description="Recurrence type")
    effective_from_year: Optional[str] = Field(None, description="Effective from year")
    effective_until_year: Optional[str] = Field(
        None, description="Effective until year"
    )
    months_before_deadline: Optional[int] = Field(
        None, description="Months before deadline to create schedules"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class ProgramRequirementDetailResponse(BaseModel):
    """Comprehensive response schema for program requirement with related data"""

    # Program requirement fields
    id: uuid.UUID = Field(..., description="Requirement ID")
    name: str = Field(..., description="Requirement name")
    target_year: int = Field(..., description="Target year")
    deadline_date: date = Field(..., description="Deadline date")
    grace_period_days: int = Field(..., description="Grace period in days")
    notification_days_before_deadline: int = Field(
        ..., description="Days before deadline to start sending notifications"
    )
    is_mandatory: bool = Field(..., description="Whether requirement is mandatory")
    is_active: bool = Field(..., description="Whether requirement is active")
    special_instruction: Optional[str] = Field(None, description="Special instructions")
    recurrence_type: ProgReqRecurrenceType = Field(..., description="Recurrence type")
    last_recurrence_at: datetime = Field(..., description="Last recurrence timestamp")
    effective_from_year: Optional[str] = Field(None, description="Effective from year")
    effective_until_year: Optional[str] = Field(
        None, description="Effective until year"
    )
    months_before_deadline: Optional[int] = Field(
        None, description="Months before deadline to create schedules"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Program information
    program_id: uuid.UUID = Field(..., description="Program ID")
    program_code: str = Field(..., description="Program code")
    program_name: str = Field(..., description="Program name")

    # Certificate type information
    cert_type_id: uuid.UUID = Field(..., description="Certificate type ID")
    cert_code: str = Field(..., description="Certificate type code")
    cert_name: str = Field(..., description="Certificate type name")

    # Schedule statistics
    schedules_count: int = Field(
        ..., description="Number of schedules created for this requirement"
    )
    latest_schedule_deadline: Optional[datetime] = Field(
        None, description="Deadline of the latest schedule created"
    )
