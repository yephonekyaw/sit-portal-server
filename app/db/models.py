from typing import List, Optional
from datetime import datetime
from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Float,
    Text,
    ForeignKey,
    Enum,
    JSON,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum
import uuid


class Base(DeclarativeBase):
    pass


# Enums
class UserType(enum.Enum):
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"


class EnrollmentStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SubmissionStatus(enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    EXPIRED = "expired"


class VerificationType(enum.Enum):
    MANUAL = "manual"
    AGENT = "agent"


class NotificationType(enum.Enum):
    SUBMISSION_REMINDER = "submission_reminder"
    DEADLINE_WARNING = "deadline_warning"
    OVERDUE_ALERT = "overdue_alert"
    SUBMISSION_CONFIRMED = "submission_confirmed"


class RelatedEntityType(enum.Enum):
    PROGRAM_REQUIREMENT = "program_requirement"
    SUBMISSION = "submission"


# Models
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, unique=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    user_type: Mapped[UserType] = mapped_column(Enum(UserType))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    refresh_tk: Mapped[Optional[str]] = mapped_column(String)
    access_tk_ver: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())
    last_login: Mapped[Optional[datetime]]

    # Relationships
    student: Mapped[Optional["Student"]] = relationship(back_populates="user")
    staff: Mapped[Optional["Staff"]] = relationship(back_populates="user")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    sit_email: Mapped[str] = mapped_column(String, unique=True)
    roll_number: Mapped[str] = mapped_column(String, unique=True)
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id")
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id")
    )
    enrollment_status: Mapped[EnrollmentStatus] = mapped_column(Enum(EnrollmentStatus))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="student")
    program: Mapped["Program"] = relationship(back_populates="students")
    academic_year: Mapped["AcademicYear"] = relationship(back_populates="students")
    certificate_submissions: Mapped[List["CertificateSubmission"]] = relationship(
        back_populates="student"
    )


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    employee_id: Mapped[str] = mapped_column(String, unique=True)
    department: Mapped[str] = mapped_column(String)
    permissions: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="staff")


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_code: Mapped[str] = mapped_column(String, unique=True)
    program_name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    students: Mapped[List["Student"]] = relationship(back_populates="program")
    program_requirements: Mapped[List["ProgramRequirement"]] = relationship(
        back_populates="program"
    )
    dashboard_stats: Mapped[List["DashboardStats"]] = relationship(
        back_populates="program"
    )


class ProgramRequirement(Base):
    __tablename__ = "program_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id")
    )
    cert_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certificate_types.id")
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id")
    )
    is_mandatory: Mapped[bool] = mapped_column(Boolean)
    submission_deadline: Mapped[datetime]
    special_instruction: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="program_requirements")
    certificate_type: Mapped["CertificateType"] = relationship(
        back_populates="program_requirements"
    )
    academic_year: Mapped["AcademicYear"] = relationship(
        back_populates="program_requirements"
    )


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    year_code: Mapped[str] = mapped_column(String, unique=True)
    start_date: Mapped[datetime]
    end_date: Mapped[datetime]
    is_current: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    students: Mapped[List["Student"]] = relationship(back_populates="academic_year")
    program_requirements: Mapped[List["ProgramRequirement"]] = relationship(
        back_populates="academic_year"
    )
    dashboard_stats: Mapped[List["DashboardStats"]] = relationship(
        back_populates="academic_year"
    )


class CertificateType(Base):
    __tablename__ = "certificate_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type_name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    validation_rules: Mapped[str] = mapped_column(Text)
    has_expiration: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    program_requirements: Mapped[List["ProgramRequirement"]] = relationship(
        back_populates="certificate_type"
    )
    certificate_submissions: Mapped[List["CertificateSubmission"]] = relationship(
        back_populates="certificate_type"
    )


class CertificateSubmission(Base):
    __tablename__ = "certificate_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id")
    )
    cert_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certificate_types.id")
    )
    file_name: Mapped[str] = mapped_column(String)
    file_key: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String)
    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus))
    ml_confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    submitted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())
    expired_at: Mapped[Optional[datetime]]

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="certificate_submissions")
    certificate_type: Mapped["CertificateType"] = relationship(
        back_populates="certificate_submissions"
    )
    verification_history: Mapped[List["VerificationHistory"]] = relationship(
        back_populates="submission"
    )


class VerificationHistory(Base):
    __tablename__ = "verification_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certificate_submissions.id")
    )
    verifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True)
    )  # FK or Agent
    verification_type: Mapped[VerificationType] = mapped_column(Enum(VerificationType))
    old_status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus))
    new_status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus))
    reasons: Mapped[Optional[str]] = mapped_column(Text)
    comments: Mapped[Optional[str]] = mapped_column(Text)
    agent_analysis_result: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    submission: Mapped["CertificateSubmission"] = relationship(
        back_populates="verification_history"
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    related_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True)
    )  # program_requirement_id or submission_id
    related_entity_type: Mapped[Optional[RelatedEntityType]] = mapped_column(
        Enum(RelatedEntityType)
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]]
    read_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notifications")

    # Indexes
    __table_args__ = (
        Index("idx_notifications_user_is_read", "user_id", "is_read"),
        Index("idx_notifications_user_created_at", "user_id", "created_at"),
    )


class DashboardStats(Base):
    __tablename__ = "dashboard_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id")
    )
    total_students: Mapped[int] = mapped_column(Integer)
    submitted_count: Mapped[int] = mapped_column(Integer)
    verified_count: Mapped[int] = mapped_column(Integer)
    rejected_count: Mapped[int] = mapped_column(Integer)
    pending_count: Mapped[int] = mapped_column(Integer)
    manual_verification_count: Mapped[int] = mapped_column(Integer)
    agent_verification_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_calculated_at: Mapped[datetime]

    # Relationships
    academic_year: Mapped["AcademicYear"] = relationship(
        back_populates="dashboard_stats"
    )
    program: Mapped["Program"] = relationship(back_populates="dashboard_stats")
