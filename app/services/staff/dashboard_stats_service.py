import uuid

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import (
    DashboardStats,
    ProgramRequirementSchedule,
    ProgramRequirement,
    Program,
    AcademicYear,
)
from app.db.session import get_sync_session
from app.schemas.staff.dashboard_stats_schemas import DashboardStatsResponse
from app.services.staff.student_service import get_student_service
from app.utils.logging import get_logger
from app.utils.datetime_utils import naive_utc_now

logger = get_logger()


class DashboardStatsService:
    """Service for managing dashboard statistics."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.student_service = get_student_service(db_session)

    async def update_dashboard_stats_counts(
        self,
        dashboard_stats_id: str,
        submitted_count_delta: int = 0,
        approved_count_delta: int = 0,
        rejected_count_delta: int = 0,
        pending_count_delta: int = 0,
        manual_review_count_delta: int = 0,
        not_submitted_count_delta: int = 0,
        on_time_submissions_delta: int = 0,
        late_submissions_delta: int = 0,
        overdue_count_delta: int = 0,
        manual_verification_count_delta: int = 0,
        agent_verification_count_delta: int = 0,
    ) -> DashboardStats:
        """
        Update dashboard stats counts by incrementing or decrementing specific fields.

        Args:
            dashboard_stats_id: The ID of the dashboard stats record to update
            *_delta: The amount to add/subtract from each field (negative values for decrement)

        Returns:
            The updated DashboardStats instance

        Raises:
            ValueError: If the dashboard stats record is not found
        """
        result = self.db.execute(
            select(DashboardStats).where(DashboardStats.id == dashboard_stats_id)
        )
        dashboard_stats = result.scalar_one_or_none()

        if not dashboard_stats:
            raise ValueError(f"Dashboard stats with ID {dashboard_stats_id} not found")

        dashboard_stats.submitted_count += submitted_count_delta
        dashboard_stats.approved_count += approved_count_delta
        dashboard_stats.rejected_count += rejected_count_delta
        dashboard_stats.pending_count += pending_count_delta
        dashboard_stats.manual_review_count += manual_review_count_delta
        dashboard_stats.not_submitted_count += not_submitted_count_delta
        dashboard_stats.on_time_submissions += on_time_submissions_delta
        dashboard_stats.late_submissions += late_submissions_delta
        dashboard_stats.overdue_count += overdue_count_delta
        dashboard_stats.manual_verification_count += manual_verification_count_delta
        dashboard_stats.agent_verification_count += agent_verification_count_delta
        dashboard_stats.last_calculated_at = naive_utc_now()

        self.db.commit()
        self.db.refresh(dashboard_stats)

        logger.info(
            f"Updated dashboard stats {dashboard_stats_id} - submitted: {submitted_count_delta:+d}, "
            f"approved: {approved_count_delta:+d}, rejected: {rejected_count_delta:+d}, "
            f"pending: {pending_count_delta:+d}, manual_review: {manual_review_count_delta:+d}"
        )

        return dashboard_stats

    async def update_dashboard_stats_by_schedule(
        self,
        requirement_schedule_id: str,
        submitted_count_delta: int = 0,
        approved_count_delta: int = 0,
        rejected_count_delta: int = 0,
        pending_count_delta: int = 0,
        manual_review_count_delta: int = 0,
        not_submitted_count_delta: int = 0,
        on_time_submissions_delta: int = 0,
        late_submissions_delta: int = 0,
        overdue_count_delta: int = 0,
        manual_verification_count_delta: int = 0,
        agent_verification_count_delta: int = 0,
    ) -> DashboardStats:
        """
        Update dashboard stats counts by requirement schedule ID.

        Args:
            requirement_schedule_id: The ID of the requirement schedule
            *_delta: The amount to add/subtract from each field (negative values for decrement)

        Returns:
            The updated DashboardStats instance

        Raises:
            ValueError: If no dashboard stats record is found for the schedule
        """
        result = self.db.execute(
            select(DashboardStats).where(
                DashboardStats.requirement_schedule_id == requirement_schedule_id
            )
        )
        dashboard_stats = result.scalar_one_or_none()

        if not dashboard_stats:
            raise ValueError(
                f"Dashboard stats for schedule {requirement_schedule_id} not found"
            )

        return await self.update_dashboard_stats_counts(
            dashboard_stats_id=dashboard_stats.id,
            submitted_count_delta=submitted_count_delta,
            approved_count_delta=approved_count_delta,
            rejected_count_delta=rejected_count_delta,
            pending_count_delta=pending_count_delta,
            manual_review_count_delta=manual_review_count_delta,
            not_submitted_count_delta=not_submitted_count_delta,
            on_time_submissions_delta=on_time_submissions_delta,
            late_submissions_delta=late_submissions_delta,
            overdue_count_delta=overdue_count_delta,
            manual_verification_count_delta=manual_verification_count_delta,
            agent_verification_count_delta=agent_verification_count_delta,
        )

    def get_dashboard_stats_by_schedule(
        self, requirement_schedule_id: str
    ) -> DashboardStatsResponse:
        """
        Get dashboard stats by requirement schedule ID.

        Args:
            requirement_schedule_id: The ID of the requirement schedule

        Returns:
            The DashboardStatsResponse instance

        Raises:
            ValueError: If no dashboard stats record is found for the schedule
        """
        result = self.db.execute(
            select(DashboardStats).where(
                DashboardStats.requirement_schedule_id == requirement_schedule_id
            )
        )
        dashboard_stats = result.scalar_one_or_none()

        if not dashboard_stats:
            raise ValueError(
                f"Dashboard stats for schedule {requirement_schedule_id} not found"
            )

        dashboard_stats_response = DashboardStatsResponse(
            id=str(dashboard_stats.id),
            requirement_schedule_id=str(dashboard_stats.requirement_schedule_id),
            program_id=str(dashboard_stats.program_id),
            academic_year_id=str(dashboard_stats.academic_year_id),
            cert_type_id=str(dashboard_stats.cert_type_id),
            total_submissions_required=dashboard_stats.total_submissions_required,
            submitted_count=dashboard_stats.submitted_count,
            approved_count=dashboard_stats.approved_count,
            rejected_count=dashboard_stats.rejected_count,
            pending_count=dashboard_stats.pending_count,
            manual_review_count=dashboard_stats.manual_review_count,
            not_submitted_count=dashboard_stats.not_submitted_count,
            on_time_submissions=dashboard_stats.on_time_submissions,
            late_submissions=dashboard_stats.late_submissions,
            overdue_count=dashboard_stats.overdue_count,
            manual_verification_count=dashboard_stats.manual_verification_count,
            agent_verification_count=dashboard_stats.agent_verification_count,
            last_calculated_at=dashboard_stats.last_calculated_at,
            created_at=dashboard_stats.created_at,
            updated_at=dashboard_stats.updated_at,
        )

        return dashboard_stats_response

    async def create_dashboard_stats_by_schedule_id(
        self, schedule_id: str
    ) -> DashboardStats:
        """
        Create dashboard stats for a given schedule ID by automatically determining
        all necessary information from database relationships.

        Args:
            schedule_id: The ID of the program requirement schedule

        Returns:
            The created DashboardStats instance

        Raises:
            ValueError: If schedule not found or required data is missing
        """
        # Get schedule with all related data in a single query
        query = (
            select(
                ProgramRequirementSchedule,
                ProgramRequirement.program_id,
                ProgramRequirement.cert_type_id,
                Program.program_code,
                AcademicYear.year_code,
            )
            .select_from(ProgramRequirementSchedule)
            .join(
                ProgramRequirement,
                ProgramRequirementSchedule.program_requirement_id
                == ProgramRequirement.id,
            )
            .join(Program, ProgramRequirement.program_id == Program.id)
            .join(
                AcademicYear,
                ProgramRequirementSchedule.academic_year_id == AcademicYear.id,
            )
            .where(ProgramRequirementSchedule.id == schedule_id)
        )

        result = self.db.execute(query)
        row = result.first()

        if not row:
            raise ValueError(
                f"Schedule with ID {schedule_id} not found or has missing related data"
            )

        schedule, program_id, cert_type_id, program_code, academic_year_code = row

        # Get total student count for this program and academic year
        total_submissions_required = (
            await self.student_service.get_active_student_count_by_program_and_year(
                program_code=program_code,
                academic_year_code=academic_year_code,
            )
        )

        # Create dashboard stats record
        dashboard_stats = DashboardStats(
            id=uuid.uuid4(),
            requirement_schedule_id=schedule.id,
            program_id=program_id,
            academic_year_id=schedule.academic_year_id,
            cert_type_id=cert_type_id,
            total_submissions_required=total_submissions_required,
            submitted_count=0,
            approved_count=0,
            rejected_count=0,
            pending_count=0,
            manual_review_count=0,
            not_submitted_count=total_submissions_required,
            on_time_submissions=0,
            late_submissions=0,
            overdue_count=0,
            manual_verification_count=0,
            agent_verification_count=0,
            last_calculated_at=naive_utc_now(),
        )

        self.db.add(dashboard_stats)
        self.db.commit()
        self.db.refresh(dashboard_stats)

        logger.info(f"Created dashboard stats for schedule {schedule_id}")

        return dashboard_stats


def get_dashboard_stats_service(
    db: Session = Depends(get_sync_session),
) -> DashboardStatsService:
    return DashboardStatsService(db)
