from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from app.db.models import SubmissionStatus, SubmissionTiming, VerificationType


class UserInfo(BaseModel):
    """User information schema"""

    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")


class StudentInfo(BaseModel):
    """Student information schema"""

    sit_email: str = Field(..., description="Student's SIT email")
    roll_number: str = Field(..., description="Student's roll number")


class ProgramInfo(BaseModel):
    """Program information schema"""

    program_code: str = Field(..., description="Program code")
    program_name: str = Field(..., description="Program name")


class CertificateInfo(BaseModel):
    """Certificate information schema"""

    cert_code: str = Field(..., description="Certificate type code")
    cert_name: str = Field(..., description="Certificate type name")


class ProgramRequirementInfo(BaseModel):
    """Program requirement information schema"""

    target_year: int = Field(..., description="Target academic year")
    is_mandatory: bool = Field(..., description="Whether the requirement is mandatory")


class ProgramRequirementScheduleInfo(BaseModel):
    """Program requirement schedule information schema"""

    submission_deadline: datetime = Field(..., description="Submission deadline")
    grace_period_deadline: datetime = Field(..., description="Grace period deadline")


class CertificateSubmissionResponse(BaseModel):
    """Response schema for certificate submission with related information"""

    # Certificate submission fields (excluding foreign keys)
    id: uuid.UUID = Field(..., description="Certificate submission ID")
    file_object_name: str = Field(..., description="File object name in storage")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="File MIME type")
    submission_status: SubmissionStatus = Field(..., description="Submission status")
    agent_confidence_score: Optional[float] = Field(
        None, description="Agent confidence score"
    )
    submission_timing: SubmissionTiming = Field(..., description="Submission timing")
    submitted_at: datetime = Field(..., description="Submission timestamp")
    expired_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Related information
    user: UserInfo = Field(..., description="User information")
    student: StudentInfo = Field(..., description="Student information")
    program: ProgramInfo = Field(..., description="Program information")
    certificate: CertificateInfo = Field(..., description="Certificate information")
    program_requirement: ProgramRequirementInfo = Field(
        ..., description="Program requirement information"
    )
    program_requirement_schedule: ProgramRequirementScheduleInfo = Field(
        ..., description="Program requirement schedule information"
    )


class CertificateSubmissionNotSubmittedResponse(BaseModel):
    """Response schema for students who haven't submitted certificates"""

    # User and student information
    user: UserInfo = Field(..., description="User information")
    student: StudentInfo = Field(..., description="Student information")
    program: ProgramInfo = Field(..., description="Program information")
    certificate: CertificateInfo = Field(..., description="Certificate information")
    program_requirement: ProgramRequirementInfo = Field(
        ..., description="Program requirement information"
    )
    program_requirement_schedule: ProgramRequirementScheduleInfo = Field(
        ..., description="Program requirement schedule information"
    )

    # Null certificate submission fields
    id: None = Field(None, description="No submission ID")
    file_object_name: None = Field(None, description="No file object name")
    filename: None = Field(None, description="No filename")
    file_size: None = Field(None, description="No file size")
    mime_type: None = Field(None, description="No MIME type")
    submission_status: None = Field(None, description="No submission status")
    agent_confidence_score: None = Field(None, description="No confidence score")
    submission_timing: None = Field(None, description="No submission timing")
    submitted_at: None = Field(None, description="No submission timestamp")
    expired_at: None = Field(None, description="No expiration timestamp")
    created_at: None = Field(None, description="No creation timestamp")
    updated_at: None = Field(None, description="No update timestamp")


class CertificateSubmissionsListResponse(BaseModel):
    """Response schema for list of certificate submissions"""

    submissions: list[CertificateSubmissionResponse] = Field(
        ..., description="List of certificate submissions"
    )
    total_count: int = Field(..., description="Total number of submissions")
    year_code: int = Field(..., description="Academic year code")
    is_submitted_filter: bool = Field(
        ..., description="Whether filtered by submitted status"
    )


class VerificationHistoryResponse(BaseModel):
    """Response schema for verification history"""

    id: uuid.UUID = Field(..., description="Verification history ID")
    verification_type: VerificationType = Field(
        ..., description="Type of verification (manual/agent)"
    )
    old_status: SubmissionStatus = Field(..., description="Previous submission status")
    new_status: SubmissionStatus = Field(..., description="New submission status")
    comments: Optional[str] = Field(None, description="Verification comments")
    reasons: Optional[str] = Field(None, description="Verification reasons")
    agent_analysis_result: Optional[Dict[str, Any]] = Field(
        None, description="Agent analysis result data"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class VerificationHistoryListResponse(BaseModel):
    """Response schema for list of verification history"""

    verification_history: list[VerificationHistoryResponse] = Field(
        ..., description="List of verification history records"
    )
    total_count: int = Field(
        ..., description="Total number of verification history records"
    )
    submission_id: uuid.UUID = Field(..., description="Certificate submission ID")


class CreateVerificationHistoryRequest(BaseModel):
    """Request schema for creating verification history"""

    verification_type: VerificationType = Field(
        ..., description="Type of verification (manual/agent)"
    )
    old_status: SubmissionStatus = Field(..., description="Previous submission status")
    new_status: SubmissionStatus = Field(..., description="New submission status")
    comments: Optional[str] = Field(
        None, description="Verification comments", max_length=1000
    )
    reasons: Optional[str] = Field(
        None, description="Verification reasons", max_length=1000
    )
    verifier_id: Optional[uuid.UUID] = Field(
        None, description="ID of the staff member who performed verification"
    )
    agent_analysis_result: Optional[Dict[str, Any]] = Field(
        None, description="Agent analysis result data"
    )


class CertificateSubmissionDataResponse(BaseModel):
    """Response schema for certificate submission data only (no related information)"""

    id: uuid.UUID = Field(..., description="Certificate submission ID")
    student_id: uuid.UUID = Field(..., description="Student ID")
    cert_type_id: uuid.UUID = Field(..., description="Certificate type ID")
    requirement_schedule_id: Optional[uuid.UUID] = Field(
        None, description="Program requirement schedule ID"
    )
    file_object_name: str = Field(..., description="File object name in storage")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="File MIME type")
    submission_status: SubmissionStatus = Field(..., description="Submission status")
    agent_confidence_score: Optional[float] = Field(
        None, description="Agent confidence score"
    )
    submission_timing: SubmissionTiming = Field(..., description="Submission timing")
    submitted_at: datetime = Field(..., description="Submission timestamp")
    expired_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
