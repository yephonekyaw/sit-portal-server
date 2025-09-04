import uuid
from datetime import datetime

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.models import (
    DashboardStats,
    ProgramRequirementSchedule,
)
from app.db.session import get_sync_session
from app.services.staff.student_service import get_student_service
from app.utils.logging import get_logger

logger = get_logger()


class DashboardStatsService:
    """Service for managing dashboard statistics."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.student_service = get_student_service(db_session)

    async def create_dashboard_stats_for_schedule(
        self,
        schedule_data: ProgramRequirementSchedule,
        program_code: str,
        academic_year_code: int,
        cert_type_id: uuid.UUID,
        program_id: uuid.UUID,
    ) -> DashboardStats:
        """
        Create a new dashboard stats record for a program requirement schedule.
        This is called when a new schedule is created in the monthly schedule creator task.
        Args:
            schedule_data: Dictionary containing schedule information
            program_code: Program code for student count lookup
            academic_year_code: Academic year code for student count lookup
            cert_type_id: Certificate type ID
            program_id: Program ID

        Returns:
            The created DashboardStats instance
        """
        # Get the total number of students who need to submit for this requirement
        total_submissions_required = (
            await self.student_service.get_active_student_count_by_program_and_year(
                program_code=program_code,
                academic_year_code=academic_year_code,
            )
        )

        # Create the dashboard stats record
        dashboard_stats = DashboardStats(
            id=uuid.uuid4(),
            requirement_schedule_id=schedule_data.id,
            program_id=program_id,
            academic_year_id=schedule_data.academic_year_id,
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
            last_calculated_at=datetime.now(),
        )

        self.db.add(dashboard_stats)

        logger.info(
            f"Created dashboard stats for schedule {schedule_data.id} - {program_code} year {academic_year_code}: {total_submissions_required} students"
        )

        return dashboard_stats

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
        dashboard_stats = (
            self.db.query(DashboardStats)
            .filter(DashboardStats.id == dashboard_stats_id)
            .first()
        )

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
        dashboard_stats.last_calculated_at = datetime.now()

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
        dashboard_stats = (
            self.db.query(DashboardStats)
            .filter(DashboardStats.requirement_schedule_id == requirement_schedule_id)
            .first()
        )

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


def get_dashboard_stats_service(
    db: Session = Depends(get_sync_session),
) -> DashboardStatsService:
    return DashboardStatsService(db)
