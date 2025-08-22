from typing import List, Optional
from datetime import datetime, date
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
    UniqueConstraint,
    CheckConstraint,
    DateTime,
    Date,
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


class EnrollmentStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    GRADUATED = "graduated"


class SubmissionStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class VerificationType(enum.Enum):
    MANUAL = "manual"
    AGENT = "agent"


class ActorType(enum.Enum):
    USER = "user"
    SYSTEM = "system"
    SCHEDULED = "scheduled"


class Priority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ChannelType(enum.Enum):
    IN_APP = "in_app"
    LINE_APP = "line_app"


class TemplateFormat(enum.Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


class NotificationStatus(enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    EXPIRED = "expired"


class ProgReqRecurrenceType(enum.Enum):
    ONCE = "once"
    ANNUAL = "annual"


class SubmissionTiming(enum.Enum):
    ON_TIME = "on_time"
    LATE = "late"
    OVERDUE = "overdue"


# Base model with common audit fields
class AuditMixin:
    """Mixin for common audit fields"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


# Models
class User(Base, AuditMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),  # Use database function
    )
    email: Mapped[str] = mapped_column(String(320), unique=True)  # RFC 5321 max length
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_type: Mapped[UserType] = mapped_column(Enum(UserType), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(500))
    access_token_version: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    student: Mapped[Optional["Student"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    staff: Mapped[Optional["Staff"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notification_recipients: Mapped[List["NotificationRecipient"]] = relationship(
        back_populates="recipient", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_type_active", "user_type", "is_active"),
        Index("idx_users_last_login", "last_login"),
    )


class Student(Base, AuditMixin):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # One-to-one relationship
        nullable=False,
    )
    sit_email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    roll_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_years.id", ondelete="RESTRICT"),
        nullable=False,
    )
    line_application_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    enrollment_status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus), default=EnrollmentStatus.ACTIVE, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="student")
    program: Mapped["Program"] = relationship(back_populates="students")
    academic_year: Mapped["AcademicYear"] = relationship(back_populates="students")
    certificate_submissions: Mapped[List["CertificateSubmission"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        Index("idx_students_user_id", "user_id"),
        Index("idx_students_program_id", "program_id"),
        Index("idx_students_academic_year_id", "academic_year_id"),
        Index("idx_students_enrollment_status", "enrollment_status"),
        Index("idx_students_roll_number", "roll_number"),
    )


class Staff(Base, AuditMixin):
    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # One-to-one relationship
        nullable=False,
    )
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="staff")
    staff_permissions: Mapped[List["StaffPermission"]] = relationship(
        back_populates="staff",
        foreign_keys="StaffPermission.staff_id",
        cascade="all, delete-orphan",
    )
    assigned_permissions: Mapped[List["StaffPermission"]] = relationship(
        back_populates="assigned_by_staff", foreign_keys="StaffPermission.assigned_by"
    )

    # Constraints
    __table_args__ = (
        Index("idx_staff_user_id", "user_id"),
        Index("idx_staff_employee_id", "employee_id"),
        Index("idx_staff_department", "department"),
    )


class Role(Base, AuditMixin):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (Index("idx_roles_name", "name"),)


class Permission(Base, AuditMixin):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="permissions")
    role: Mapped["Role"] = relationship(back_populates="permissions")
    staff_permissions: Mapped[List["StaffPermission"]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("program_id", "role_id", name="uq_permissions_program_role"),
        Index("idx_permissions_program_id", "program_id"),
        Index("idx_permissions_role_id", "role_id"),
    )


class StaffPermission(Base, AuditMixin):
    __tablename__ = "staff_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL")
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    staff: Mapped["Staff"] = relationship(
        back_populates="staff_permissions", foreign_keys=[staff_id]
    )
    permission: Mapped["Permission"] = relationship(back_populates="staff_permissions")
    assigned_by_staff: Mapped[Optional["Staff"]] = relationship(
        back_populates="assigned_permissions", foreign_keys=[assigned_by]
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "staff_id", "permission_id", name="uq_staff_permissions_staff_permission"
        ),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > assigned_at",
            name="ck_staff_permissions_expires_after_assigned",
        ),
        Index("idx_staff_permissions_staff_id", "staff_id"),
        Index("idx_staff_permissions_permission_id", "permission_id"),
        Index("idx_staff_permissions_is_active", "is_active"),
        Index("idx_staff_permissions_expires_at", "expires_at"),
    )


class Program(Base, AuditMixin):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    program_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    program_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration_years: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    students: Mapped[List["Student"]] = relationship(back_populates="program")
    program_requirements: Mapped[List["ProgramRequirement"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )
    dashboard_stats: Mapped[List["DashboardStats"]] = relationship(
        back_populates="program"
    )
    permissions: Mapped[List["Permission"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("duration_years > 0", name="ck_programs_duration_positive"),
        Index("idx_programs_code", "program_code"),
        Index("idx_programs_is_active", "is_active"),
    )


class ProgramRequirement(Base, AuditMixin):
    __tablename__ = "program_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    cert_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certificate_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    deadline_date: Mapped[date] = mapped_column(Date, nullable=False)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    special_instruction: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    recurrence_type: Mapped[ProgReqRecurrenceType] = mapped_column(
        Enum(ProgReqRecurrenceType),
        default=ProgReqRecurrenceType.ANNUAL,
        nullable=False,
    )
    last_recurrence_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notification_days_before_deadline: Mapped[int] = mapped_column(
        Integer, default=90, nullable=False
    )
    effective_from_year: Mapped[Optional[str]] = mapped_column(String(10))
    effective_until_year: Mapped[Optional[str]] = mapped_column(
        String(10)
    )  # Up to this academic year
    months_before_deadline: Mapped[Optional[int]] = mapped_column(Integer, default=1)

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="program_requirements")
    certificate_type: Mapped["CertificateType"] = relationship(
        back_populates="program_requirements"
    )
    requirement_schedules: Mapped[List["ProgramRequirementSchedule"]] = relationship(
        back_populates="program_requirement", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "program_id",
            "cert_type_id",
            "target_year",
            name="uq_program_requirements_program_cert_year",
        ),
        CheckConstraint(
            "target_year >= 1", name="ck_program_requirements_target_year_positive"
        ),
        CheckConstraint(
            "EXTRACT(YEAR FROM deadline_date) = 2000",
            name="ck_program_requirements_deadline_year_2000",
        ),
        Index("idx_program_requirements_program_id", "program_id"),
        Index("idx_program_requirements_cert_type_id", "cert_type_id"),
        Index("idx_program_requirements_program_active", "program_id", "is_active"),
        CheckConstraint(
            "months_before_deadline IS NULL OR (months_before_deadline >= 1 AND months_before_deadline <= 6)",
            name="ck_program_requirements_months_before_deadline_range",
        ),
    )


class ProgramRequirementSchedule(Base, AuditMixin):
    """Academic year-specific deadlines for program requirements"""

    __tablename__ = "program_requirement_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    program_requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("program_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_years.id", ondelete="RESTRICT"),
        nullable=False,
    )
    submission_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    grace_period_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    start_notify_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_notified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    program_requirement: Mapped["ProgramRequirement"] = relationship(
        back_populates="requirement_schedules"
    )
    academic_year: Mapped["AcademicYear"] = relationship(
        back_populates="requirement_schedules"
    )
    certificate_submissions: Mapped[List["CertificateSubmission"]] = relationship(
        back_populates="requirement_schedule"
    )
    dashboard_stats: Mapped[List["DashboardStats"]] = relationship(
        back_populates="requirement_schedule"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "program_requirement_id",
            "academic_year_id",
            name="uq_requirement_schedules_requirement_year",
        ),
        Index("idx_requirement_schedules_academic_year", "academic_year_id"),
        Index("idx_requirement_schedules_deadline", "submission_deadline"),
        Index(
            "idx_requirement_schedules_program_requirement", "program_requirement_id"
        ),
    )


class AcademicYear(Base, AuditMixin):
    __tablename__ = "academic_years"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    year_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    students: Mapped[List["Student"]] = relationship(back_populates="academic_year")
    requirement_schedules: Mapped[List["ProgramRequirementSchedule"]] = relationship(
        back_populates="academic_year"
    )
    dashboard_stats: Mapped[List["DashboardStats"]] = relationship(
        back_populates="academic_year"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "end_date > start_date", name="ck_academic_years_end_after_start"
        ),
        Index("idx_academic_years_year_code", "year_code"),
        Index("idx_academic_years_is_current", "is_current"),
        Index("idx_academic_years_dates", "start_date", "end_date"),
    )


class CertificateType(Base, AuditMixin):
    __tablename__ = "certificate_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    verification_template: Mapped[str] = mapped_column(Text, nullable=False)
    has_expiration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    program_requirements: Mapped[List["ProgramRequirement"]] = relationship(
        back_populates="certificate_type"
    )
    certificate_submissions: Mapped[List["CertificateSubmission"]] = relationship(
        back_populates="certificate_type"
    )
    dashboard_stats: Mapped[List["DashboardStats"]] = relationship(
        back_populates="certificate_type"
    )

    # Constraints
    __table_args__ = (
        Index("idx_certificate_types_code", "code"),
        Index("idx_certificate_types_is_active", "is_active"),
    )


class CertificateSubmission(Base, AuditMixin):
    __tablename__ = "certificate_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    cert_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certificate_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requirement_schedule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("program_requirement_schedules.id", ondelete="SET NULL"),
    )
    file_object_name: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    submission_status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.PENDING, nullable=False
    )
    agent_confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    submission_timing: Mapped[SubmissionTiming] = mapped_column(
        Enum(SubmissionTiming), default=SubmissionTiming.ON_TIME, nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="certificate_submissions")
    certificate_type: Mapped["CertificateType"] = relationship(
        back_populates="certificate_submissions"
    )
    requirement_schedule: Mapped[Optional["ProgramRequirementSchedule"]] = relationship(
        back_populates="certificate_submissions"
    )
    verification_history: Mapped[List["VerificationHistory"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "cert_type_id",
            "requirement_schedule_id",
            name="uq_certificate_submissions_student_cert_schedule",
        ),
        CheckConstraint(
            "file_size > 0", name="ck_certificate_submissions_file_size_positive"
        ),
        CheckConstraint(
            "agent_confidence_score IS NULL OR (agent_confidence_score >= 0 AND agent_confidence_score <= 1)",
            name="ck_certificate_submissions_confidence_score_range",
        ),
        CheckConstraint(
            "expired_at IS NULL OR expired_at > submitted_at",
            name="ck_certificate_submissions_expired_after_submitted",
        ),
        Index("idx_certificate_submissions_student_id", "student_id"),
        Index("idx_certificate_submissions_cert_type_id", "cert_type_id"),
        Index(
            "idx_certificate_submissions_requirement_schedule_id",
            "requirement_schedule_id",
        ),
        Index("idx_certificate_submissions_submission_status", "submission_status"),
        Index("idx_certificate_submissions_submission_timing", "submission_timing"),
        Index("idx_certificate_submissions_submitted_at", "submitted_at"),
        Index("idx_certificate_submissions_expired_at", "expired_at"),
    )


class VerificationHistory(Base, AuditMixin):
    __tablename__ = "verification_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certificate_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    verifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    verification_type: Mapped[VerificationType] = mapped_column(
        Enum(VerificationType), nullable=False
    )
    old_status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), nullable=False
    )
    new_status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), nullable=False
    )
    comments: Mapped[Optional[str]] = mapped_column(Text)
    reasons: Mapped[Optional[str]] = mapped_column(Text)
    agent_analysis_result: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    submission: Mapped["CertificateSubmission"] = relationship(
        back_populates="verification_history"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "old_status != new_status", name="ck_verification_history_status_change"
        ),
        Index("idx_verification_history_submission_id", "submission_id"),
        Index("idx_verification_history_verifier_id", "verifier_id"),
        Index("idx_verification_history_verification_type", "verification_type"),
        Index("idx_verification_history_created_at", "created_at"),
    )


class NotificationType(Base, AuditMixin):
    __tablename__ = "notification_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    default_priority: Mapped[Priority] = mapped_column(
        Enum(Priority), default=Priority.MEDIUM, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    channel_templates: Mapped[List["NotificationChannelTemplate"]] = relationship(
        back_populates="notification_type", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="notification_type"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "entity_type", "code", name="uq_notification_types_entity_code"
        ),
        Index("idx_notification_types_code", "code"),
        Index("idx_notification_types_entity_type", "entity_type"),
        Index("idx_notification_types_is_active", "is_active"),
    )


class NotificationChannelTemplate(Base, AuditMixin):
    __tablename__ = "notification_channel_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    notification_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_type: Mapped[ChannelType] = mapped_column(Enum(ChannelType), nullable=False)
    template_subject: Mapped[Optional[str]] = mapped_column(String(500))
    template_body: Mapped[str] = mapped_column(Text, nullable=False)
    template_format: Mapped[TemplateFormat] = mapped_column(
        Enum(TemplateFormat), default=TemplateFormat.TEXT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    notification_type: Mapped["NotificationType"] = relationship(
        back_populates="channel_templates"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "notification_type_id",
            "channel_type",
            name="uq_notification_channel_templates_type_channel",
        ),
        Index(
            "idx_notification_channel_templates_notification_type",
            "notification_type_id",
        ),
        Index("idx_notification_channel_templates_channel_type", "channel_type"),
        Index("idx_notification_channel_templates_is_active", "is_active"),
    )


class Notification(Base, AuditMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    notification_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_type: Mapped[ActorType] = mapped_column(Enum(ActorType), nullable=False)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority), default=Priority.MEDIUM, nullable=False
    )
    notification_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    notification_type: Mapped["NotificationType"] = relationship(
        back_populates="notifications"
    )
    recipients: Mapped[List["NotificationRecipient"]] = relationship(
        back_populates="notification", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at",
            name="ck_notifications_expires_after_created",
        ),
        CheckConstraint(
            "scheduled_for IS NULL OR scheduled_for >= created_at",
            name="ck_notifications_scheduled_not_before_created",
        ),
        Index("idx_notifications_entity_type", "entity_id", "notification_type_id"),
        Index("idx_notifications_created_at", "created_at"),
        Index("idx_notifications_scheduled_for", "scheduled_for"),
        Index("idx_notifications_expires_at", "expires_at"),
        Index("idx_notifications_priority", "priority"),
        Index("idx_notifications_actor", "actor_type", "actor_id"),
    )


class NotificationRecipient(Base, AuditMixin):
    __tablename__ = "notification_recipients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    line_app_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False
    )
    # delivered_at will be set when the notification for this recipient is processed by the notification processing task
    # for each delivery channel, such as line, the corresponding sent_at will be set from the channel's delivery task
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    line_app_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    # Relationships
    notification: Mapped["Notification"] = relationship(back_populates="recipients")
    recipient: Mapped["User"] = relationship(back_populates="notification_recipients")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "recipient_id",
            name="uq_notification_recipients_notification_recipient",
        ),
        CheckConstraint(
            "delivered_at IS NULL OR delivered_at >= created_at",
            name="ck_notification_recipients_delivered_after_created",
        ),
        CheckConstraint(
            "read_at IS NULL OR read_at >= delivered_at",
            name="ck_notification_recipients_read_after_delivered",
        ),
        Index("idx_notification_recipients_notification_id", "notification_id"),
        Index("idx_notification_recipients_recipient_id", "recipient_id"),
        Index("idx_notification_recipients_status", "status"),
        Index("idx_notification_recipients_status_created", "status", "created_at"),
        Index("idx_notification_recipients_recipient_status", "recipient_id", "status"),
    )


class DashboardStats(Base, AuditMixin):
    __tablename__ = "dashboard_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    requirement_schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("program_requirement_schedules.id", ondelete="CASCADE"),
        nullable=False,
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    cert_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certificate_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_submissions_required: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    submitted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_submitted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    on_time_submissions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    late_submissions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overdue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_verification_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    agent_verification_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    requirement_schedule: Mapped["ProgramRequirementSchedule"] = relationship(
        back_populates="dashboard_stats"
    )
    academic_year: Mapped["AcademicYear"] = relationship(
        back_populates="dashboard_stats"
    )
    program: Mapped["Program"] = relationship(back_populates="dashboard_stats")
    certificate_type: Mapped["CertificateType"] = relationship(
        back_populates="dashboard_stats"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "requirement_schedule_id", name="uq_dashboard_stats_requirement_schedule"
        ),
        CheckConstraint(
            "submitted_count = approved_count + rejected_count + pending_count + manual_review_count",
            name="ck_dashboard_stats_submitted_count_consistency",
        ),
        CheckConstraint(
            "total_submissions_required = submitted_count + not_submitted_count",
            name="ck_dashboard_stats_total_count_consistency",
        ),
        CheckConstraint(
            "submitted_count = on_time_submissions + late_submissions",
            name="ck_dashboard_stats_timing_consistency",
        ),
        Index("idx_dashboard_stats_requirement_schedule", "requirement_schedule_id"),
        Index("idx_dashboard_stats_program_id", "program_id"),
        Index("idx_dashboard_stats_academic_year_id", "academic_year_id"),
        Index("idx_dashboard_stats_cert_type_id", "cert_type_id"),
        Index("idx_dashboard_stats_created_at", "created_at"),
        Index("idx_dashboard_stats_last_calculated_at", "last_calculated_at"),
        Index(
            "idx_dashboard_stats_program_academic_year",
            "program_id",
            "academic_year_id",
        ),
        Index("idx_dashboard_stats_program_cert_type", "program_id", "cert_type_id"),
        Index(
            "idx_dashboard_stats_academic_year_cert_type",
            "academic_year_id",
            "cert_type_id",
        ),
        Index(
            "idx_dashboard_stats_program_year_cert",
            "program_id",
            "academic_year_id",
            "cert_type_id",
        ),
        Index("idx_dashboard_stats_overdue_count", "overdue_count"),
        Index("idx_dashboard_stats_pending_count", "pending_count"),
        Index("idx_dashboard_stats_manual_review_count", "manual_review_count"),
        # Covering index for common dashboard queries
        Index(
            "idx_dashboard_stats_summary_covering",
            "program_id",
            "academic_year_id",
            "cert_type_id",
            "total_submissions_required",
            "submitted_count",
            "approved_count",
            "last_calculated_at",
        ),
    )
