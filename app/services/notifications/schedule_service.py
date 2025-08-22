from typing import Dict, Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .base import BaseNotificationService
from .deadline_utils import DeadlineCalculator
from app.db.models import (
    ProgramRequirementSchedule,
    ProgramRequirement,
)
from app.utils.logging import get_logger
from app.utils.errors import BusinessLogicError

logger = get_logger()


class ProgramRequirementScheduleNotificationService(BaseNotificationService):
    """Unified program requirement schedule notification service"""

    def _format_deadline_data(
        self, schedule: ProgramRequirementSchedule
    ) -> Dict[str, Any]:
        """Extract and format all deadline-related data"""
        deadline_date = (
            schedule.submission_deadline.date()
            if schedule.submission_deadline
            else None
        )

        grace_deadline_date = (
            schedule.grace_period_deadline.date()
            if schedule.grace_period_deadline
            else None
        )

        return {
            "deadline_date": (
                deadline_date.strftime("%Y-%m-%d") if deadline_date else "N/A"
            ),
            "grace_period_deadline": (
                grace_deadline_date.strftime("%Y-%m-%d")
                if grace_deadline_date
                else "N/A"
            ),
            "days_remaining": DeadlineCalculator.calculate_days_remaining(
                deadline_date
            ),
            "days_late": DeadlineCalculator.calculate_days_late(deadline_date),
            "days_overdue": DeadlineCalculator.calculate_days_overdue(
                grace_deadline_date
            ),
            "is_overdue": DeadlineCalculator.is_deadline_passed(deadline_date),
        }

    def _format_requirement_data(
        self, schedule: ProgramRequirementSchedule
    ) -> Dict[str, Any]:
        """Extract and format requirement-specific data"""
        mandatory_flag = (
            "This is a mandatory requirement."
            if schedule.program_requirement.is_mandatory
            else "This is an optional requirement."
        )

        return {
            "schedule_id": str(schedule.id),
            "requirement_name": schedule.program_requirement.name,
            "program_name": schedule.program_requirement.program.program_name,
            "program_code": schedule.program_requirement.program.program_code,
            "academic_year": schedule.academic_year.year_code,
            "is_mandatory": schedule.program_requirement.is_mandatory,
            "mandatory_flag": mandatory_flag,
            "target_year": schedule.program_requirement.target_year,
        }

    async def get_notification_data(
        self, entity_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get program requirement schedule data for all notification types"""
        try:
            result = await self.db.execute(
                select(ProgramRequirementSchedule)
                .options(
                    selectinload(
                        ProgramRequirementSchedule.program_requirement
                    ).selectinload(ProgramRequirement.program),
                    selectinload(ProgramRequirementSchedule.academic_year),
                )
                .where(ProgramRequirementSchedule.id == entity_id)
            )
            schedule = result.scalar_one_or_none()

            if not schedule:
                raise ValueError(f"Program requirement schedule not found: {entity_id}")

            # Combine requirement data with deadline calculations
            requirement_data = self._format_requirement_data(schedule)
            deadline_data = self._format_deadline_data(schedule)

            return {**requirement_data, **deadline_data}

        except Exception as e:
            raise BusinessLogicError(
                f"Failed to get program requirement schedule data for {entity_id}: {e}"
            )


def create_schedule_service(
    db_session, notification_code: str
) -> ProgramRequirementScheduleNotificationService:
    """Create program requirement schedule notification service"""
    return ProgramRequirementScheduleNotificationService(db_session, notification_code)
