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
    UniqueConstraint,
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
    MICROSOFT_TEAMS = "microsoft_teams"


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
    notification_recipients: Mapped[List["NotificationRecipient"]] = relationship(
        back_populates="recipient"
    )


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
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="staff")
    staff_permissions: Mapped[List["StaffPermission"]] = relationship(
        back_populates="staff", foreign_keys="StaffPermission.staff_id"
    )
    assigned_permissions: Mapped[List["StaffPermission"]] = relationship(
        back_populates="assigned_by_staff", foreign_keys="StaffPermission.assigned_by"
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id")
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="permissions")
    role: Mapped["Role"] = relationship(back_populates="permissions")
    staff_permissions: Mapped[List["StaffPermission"]] = relationship(
        back_populates="permission"
    )

    # Constraints
    __table_args__ = (UniqueConstraint("program_id", "role_id"),)


class StaffPermission(Base):
    __tablename__ = "staff_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id")
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id")
    )
    assigned_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    staff: Mapped["Staff"] = relationship(
        back_populates="staff_permissions", foreign_keys=[staff_id]
    )
    permission: Mapped["Permission"] = relationship(back_populates="staff_permissions")
    assigned_by_staff: Mapped[Optional["Staff"]] = relationship(
        back_populates="assigned_permissions", foreign_keys=[assigned_by]
    )

    # Constraints
    __table_args__ = (UniqueConstraint("staff_id", "permission_id"),)


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_code: Mapped[str] = mapped_column(String, unique=True)
    program_name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    duration_years: Mapped[int] = mapped_column(Integer, default=4)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
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
    permissions: Mapped[List["Permission"]] = relationship(back_populates="program")


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
    name: Mapped[str] = mapped_column(String)
    target_year: Mapped[int] = mapped_column(Integer)
    deadline_month: Mapped[int] = mapped_column(Integer)
    deadline_day: Mapped[int] = mapped_column(Integer)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    special_instruction: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    recurrence_type: Mapped[ProgReqRecurrenceType] = mapped_column(
        Enum(ProgReqRecurrenceType),
        default=ProgReqRecurrenceType.ANNUAL,
    )
    last_recurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="program_requirements")
    certificate_type: Mapped["CertificateType"] = relationship(
        back_populates="program_requirements"
    )
    requirement_schedules: Mapped[List["ProgramRequirementSchedule"]] = relationship(
        back_populates="program_requirement"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("program_id", "cert_type_id", "target_year"),
        Index("idx_program_requirements_program_active", "program_id", "is_active"),
    )


class ProgramRequirementSchedule(Base):
    """
    Academic year-specific deadlines for program requirements
    This table gets populated by scheduled jobs for each new academic year
    """

    __tablename__ = "program_requirement_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("program_requirements.id")
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id")
    )
    submission_deadline: Mapped[datetime] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

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
        # One schedule per requirement per academic year
        UniqueConstraint("program_requirement_id", "academic_year_id"),
        Index("idx_requirement_schedules_academic_year", "academic_year_id"),
        Index("idx_requirement_schedules_deadline", "submission_deadline"),
    )


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    year_code: Mapped[str] = mapped_column(String, unique=True)  # e.g., "2023", "2024"
    start_date: Mapped[datetime]
    end_date: Mapped[datetime]
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    students: Mapped[List["Student"]] = relationship(back_populates="academic_year")
    requirement_schedules: Mapped[List["ProgramRequirementSchedule"]] = relationship(
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
    code: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    verification_template: Mapped[str] = mapped_column(Text)
    has_expiration: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

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
    requirement_schedule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("program_requirement_schedules.id")
    )

    file_name: Mapped[str] = mapped_column(String)
    file_key: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.PENDING
    )
    agent_confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    submitted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())
    expired_at: Mapped[Optional[datetime]]

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="certificate_submissions")
    certificate_type: Mapped["CertificateType"] = relationship(
        back_populates="certificate_submissions"
    )
    requirement_schedule: Mapped[Optional["ProgramRequirementSchedule"]] = relationship(
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
    comments: Mapped[Optional[str]] = mapped_column(Text)
    reasons: Mapped[Optional[str]] = mapped_column(
        Text
    )  # rejection reasons from staff or agent
    agent_analysis_result: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    submission: Mapped["CertificateSubmission"] = relationship(
        back_populates="verification_history"
    )


class NotificationType(Base):
    __tablename__ = "notification_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    entity_type: Mapped[str] = mapped_column(String)
    default_priority: Mapped[Priority] = mapped_column(
        Enum(Priority), default=Priority.MEDIUM
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    channel_templates: Mapped[List["NotificationChannelTemplate"]] = relationship(
        back_populates="notification_type"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="notification_type"
    )

    # Constraints
    __table_args__ = (UniqueConstraint("entity_type", "code"),)


class NotificationChannelTemplate(Base):
    __tablename__ = "notification_channel_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    notification_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notification_types.id")
    )
    channel_type: Mapped[ChannelType] = mapped_column(Enum(ChannelType))
    template_subject: Mapped[Optional[str]] = mapped_column(String)
    template_body: Mapped[str] = mapped_column(String)
    template_format: Mapped[TemplateFormat] = mapped_column(
        Enum(TemplateFormat), default=TemplateFormat.TEXT
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    notification_type: Mapped["NotificationType"] = relationship(
        back_populates="channel_templates"
    )

    # Constraints
    __table_args__ = (UniqueConstraint("notification_type_id", "channel_type"),)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    notification_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notification_types.id")
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    actor_type: Mapped[ActorType] = mapped_column(Enum(ActorType))
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.MEDIUM)
    notification_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    scheduled_for: Mapped[Optional[datetime]]
    expires_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    notification_type: Mapped["NotificationType"] = relationship(
        back_populates="notifications"
    )
    recipients: Mapped[List["NotificationRecipient"]] = relationship(
        back_populates="notification"
    )

    # Indexes
    __table_args__ = (
        Index("idx_notifications_entity_type", "entity_id", "notification_type_id"),
        Index("idx_notifications_created_at", "created_at"),
        Index("idx_notifications_scheduled_for", "scheduled_for"),
        Index("idx_notifications_expires_at", "expires_at"),
    )


class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id")
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    microsoft_teams_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.PENDING
    )
    microsoft_teams_sent_at: Mapped[Optional[datetime]]
    delivered_at: Mapped[Optional[datetime]]
    read_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

    # Relationships
    notification: Mapped["Notification"] = relationship(back_populates="recipients")
    recipient: Mapped["User"] = relationship(back_populates="notification_recipients")

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("notification_id", "recipient_id"),
        Index("idx_notification_recipients_status", "recipient_id", "status"),
        Index("idx_notification_recipients_status_created", "status", "created_at"),
    )


class DashboardStats(Base):
    __tablename__ = "dashboard_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    requirement_schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("program_requirement_schedules.id")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id")
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id")
    )
    cert_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certificate_types.id")
    )
    total_submissions_required: Mapped[int] = mapped_column(Integer, default=0)
    submitted_count: Mapped[int] = mapped_column(Integer, default=0)
    approved_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    pending_count: Mapped[int] = mapped_column(Integer, default=0)
    manual_review_count: Mapped[int] = mapped_column(Integer, default=0)
    not_submitted_count: Mapped[int] = mapped_column(Integer, default=0)
    on_time_submissions: Mapped[int] = mapped_column(Integer, default=0)
    late_submissions: Mapped[int] = mapped_column(Integer, default=0)
    overdue_count: Mapped[int] = mapped_column(Integer, default=0)
    manual_verification_count: Mapped[int] = mapped_column(Integer, default=0)
    agent_verification_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_calculated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
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

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("requirement_schedule_id"),
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
        Index(
            "idx_dashboard_stats_summary_covering",
            "program_id",
            "academic_year_id",
            "cert_type_id",
            "total_students_required",
            "submitted_count",
            "approved_count",
            "last_calculated_at",
        ),
    )
