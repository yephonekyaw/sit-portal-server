import uuid
from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    DashboardStats,
    ProgramRequirementSchedule,
)
from app.db.session import get_async_session
from app.services.student_service import get_student_service
from app.utils.logging import get_logger

logger = get_logger()


class DashboardStatsService:
    """Service for managing dashboard statistics."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.student_service = get_student_service(db_session)

    async def create_dashboard_stats_for_schedule(
        self, schedule: ProgramRequirementSchedule
    ) -> DashboardStats:
        """
        Create a new dashboard stats record for a program requirement schedule.

        This is called when a new schedule is created in the monthly schedule creator task.

        Args:
            schedule: The ProgramRequirementSchedule instance

        Returns:
            The created DashboardStats instance
        """
        # Get the total number of students who need to submit for this requirement
        total_submissions_required = (
            await self.student_service.get_active_student_count_by_program_and_year(
                program_code=schedule.program_requirement.program.program_code,
                academic_year_code=schedule.academic_year.year_code,
            )
        )

        # Create the dashboard stats record
        dashboard_stats = DashboardStats(
            id=uuid.uuid4(),
            requirement_schedule_id=schedule.id,
            program_id=schedule.program_requirement.program_id,
            academic_year_id=schedule.academic_year_id,
            cert_type_id=schedule.program_requirement.cert_type_id,
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
            last_calculated_at=datetime.now(timezone.utc),
        )

        self.db.add(dashboard_stats)
        await self.db.commit()
        await self.db.refresh(dashboard_stats)

        logger.info(
            "Created dashboard stats for new schedule",
            schedule_id=str(schedule.id),
            program_code=schedule.program_requirement.program.program_code,
            academic_year_code=schedule.academic_year.year_code,
            total_submissions_required=total_submissions_required,
        )

        return dashboard_stats

    async def create_dashboard_stats_for_schedule_data(
        self,
        schedule_data: dict,
        program_code: str,
        academic_year_code: int,
        cert_type_id: uuid.UUID,
        program_id: uuid.UUID,
    ) -> DashboardStats:
        """
        Create dashboard stats when we only have schedule data (for batch creation scenarios).

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
            requirement_schedule_id=schedule_data["id"],
            program_id=program_id,
            academic_year_id=schedule_data["academic_year_id"],
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
            last_calculated_at=datetime.now(timezone.utc),
        )

        self.db.add(dashboard_stats)

        logger.info(
            "Created dashboard stats for schedule data",
            schedule_id=str(schedule_data["id"]),
            program_code=program_code,
            academic_year_code=academic_year_code,
            total_submissions_required=total_submissions_required,
        )

        return dashboard_stats


def get_dashboard_stats_service(
    db: AsyncSession = Depends(get_async_session),
) -> DashboardStatsService:
    return DashboardStatsService(db)
