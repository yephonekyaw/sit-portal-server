from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import uuid

from app.db.models import ProgReqRecurrenceType, ScheduleCreationTrigger


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
    schedule_creation_trigger: ScheduleCreationTrigger = Field(
        default=ScheduleCreationTrigger.AUTOMATIC,
        description="How schedule creation is triggered",
    )
    custom_trigger_month: Optional[int] = Field(
        default=None,
        ge=1,
        le=12,
        description="Custom trigger month (1-12) for custom_date trigger",
    )
    custom_trigger_day: Optional[int] = Field(
        default=None,
        ge=1,
        le=31,
        description="Custom trigger day (1-31) for custom_date trigger",
    )
    months_before_target_year: Optional[int] = Field(
        default=None,
        ge=1,
        le=24,
        description="Months before target year for relative trigger",
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

    @field_validator("custom_trigger_day", "custom_trigger_month")
    @classmethod
    def validate_custom_trigger_components(
        cls, v: Optional[int], info
    ) -> Optional[int]:
        """Validate custom trigger date components"""
        if v is not None:
            if info.field_name == "custom_trigger_day" and (v < 1 or v > 31):
                raise ValueError("Custom trigger day must be between 1 and 31")
            if info.field_name == "custom_trigger_month" and (v < 1 or v > 12):
                raise ValueError("Custom trigger month must be between 1 and 12")
        return v

    def model_post_init(self, __context) -> None:
        """Validate conditional field dependencies after model initialization"""
        # Validate custom_date trigger requirements
        if self.schedule_creation_trigger == ScheduleCreationTrigger.CUSTOM_DATE:
            if self.custom_trigger_month is None or self.custom_trigger_day is None:
                raise ValueError(
                    "custom_trigger_month and custom_trigger_day are required when "
                    "schedule_creation_trigger is 'custom_date'"
                )
        elif (
            self.schedule_creation_trigger
            == ScheduleCreationTrigger.RELATIVE_TO_TARGET_YEAR
        ):
            if self.months_before_target_year is None:
                raise ValueError(
                    "months_before_target_year is required when "
                    "schedule_creation_trigger is 'relative_to_target_year'"
                )

        # Validate deadline date is valid
        try:
            deadline_date = date(2000, self.deadline_month, self.deadline_day)
        except ValueError as e:
            raise ValueError(f"Invalid deadline date: {e}")

        # Validate custom trigger date if provided
        custom_trigger_date = None
        if (
            self.custom_trigger_month is not None
            and self.custom_trigger_day is not None
        ):
            try:
                custom_trigger_date = date(
                    2000, self.custom_trigger_month, self.custom_trigger_day
                )
            except ValueError as e:
                raise ValueError(f"Invalid custom trigger date: {e}")

        # Validate trigger date is not later than deadline date
        if custom_trigger_date is not None:
            if custom_trigger_date > deadline_date:
                raise ValueError(
                    "Custom trigger date cannot be later than deadline date"
                )

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
    schedule_creation_trigger: ScheduleCreationTrigger = Field(
        ..., description="Schedule creation trigger"
    )
    custom_trigger_date: Optional[date] = Field(None, description="Custom trigger date")
    months_before_target_year: Optional[int] = Field(
        None, description="Months before target year"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
