from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.db.models import SubmissionStatus, SubmissionTiming


class CertificateSubmissionResponse(BaseModel):
    """Response schema for certificate submission"""

    id: UUID = Field(..., description="Submission ID")
    student_id: UUID = Field(..., description="Student ID")
    cert_type_id: UUID = Field(..., description="Certificate type ID")
    requirement_schedule_id: UUID = Field(..., description="Requirement schedule ID")
    file_object_name: str = Field(..., description="File object name in MinIO")
    file_name: str = Field(..., description="Original file name")
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
    file_name: str
    file_size: int
    mime_type: str
    agent_confidence_score: float = 0.0
    submission_timing: SubmissionTiming
