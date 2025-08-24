from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, ConfigDict

from app.db.models import SubmissionStatus, SubmissionTiming
from app.schemas.camel_base_model import CamelCaseBaseModel as BaseModel


class CertificateSubmissionResponse(BaseModel):
    """Response schema for certificate submission"""

    id: UUID = Field(..., description="Submission ID")
    student_id: UUID = Field(..., description="Student ID")
    cert_type_id: UUID = Field(..., description="Certificate type ID")
    requirement_schedule_id: UUID = Field(..., description="Requirement schedule ID")
    file_object_name: str = Field(..., description="File object name in MinIO")
    filename: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="File MIME type")
    submission_status: SubmissionStatus = Field(
        ..., description="Current submission status"
    )
    agent_confidence_score: Optional[float] = Field(
        None, description="Agent confidence score"
    )
    submission_timing: SubmissionTiming = Field(
        ..., description="Submission timing status"
    )
    submitted_at: datetime = Field(..., description="Timestamp when submitted")

    model_config = ConfigDict(from_attributes=True)


class CertificateSubmissionCreate(BaseModel):
    """Schema for creating a certificate submission (used internally)"""

    student_id: UUID
    cert_type_id: UUID
    requirement_schedule_id: UUID
    file_object_name: str
    filename: str
    file_size: int
    mime_type: str
    agent_confidence_score: float = 0.0
    submission_timing: SubmissionTiming


class StudentRequirementWithSubmissionResponse(BaseModel):
    """Response schema for student requirements with submission status"""

    # Schedule data
    schedule_id: str = Field(..., description="Program requirement schedule ID")
    submission_deadline: str = Field(
        ..., description="Submission deadline (ISO format)"
    )

    # Requirement data
    requirement_id: str = Field(..., description="Program requirement ID")
    requirement_name: str = Field(..., description="Requirement name")
    target_year: int = Field(..., description="Target year for completion")
    is_mandatory: bool = Field(..., description="Whether requirement is mandatory")
    special_instruction: Optional[str] = Field(None, description="Special instructions")

    # Program data
    program_id: str = Field(..., description="Program ID")
    program_code: str = Field(..., description="Program code")
    program_name: str = Field(..., description="Program name")

    # Certificate type data
    cert_type_id: str = Field(..., description="Certificate type ID")
    cert_code: str = Field(..., description="Certificate code")
    cert_name: str = Field(..., description="Certificate name")
    cert_description: str = Field(..., description="Certificate description")

    # Submission data (None if not submitted)
    submission_id: Optional[str] = Field(None, description="Submission ID")
    file_object_name: Optional[str] = Field(
        None, description="File object name in MinIO"
    )
    filename: Optional[str] = Field(None, description="Original file name")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="File MIME type")
    submission_status: Optional[str] = Field(
        None, description="Current submission status"
    )
    agent_confidence_score: Optional[float] = Field(
        None, description="Agent confidence score"
    )
    submission_timing: Optional[str] = Field(
        None, description="Submission timing status"
    )
    submitted_at: Optional[str] = Field(
        None, description="Timestamp when submitted (ISO format)"
    )
    expired_at: Optional[str] = Field(
        None, description="Expiration timestamp (ISO format)"
    )

    model_config = ConfigDict(from_attributes=True)
