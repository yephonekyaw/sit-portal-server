from typing import Dict, Any
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .base import BaseNotificationService
from .registry import notification_service
from app.db.models import (
    ProgramRequirementSchedule,
    ProgramRequirement,
)
from app.utils.logging import get_logger

logger = get_logger()


@notification_service(notification_code="program_requirement_overdue")
class ProgramRequirementScheduleOverdueNotificationService(BaseNotificationService):
    """Program Requirement Overdue notification service"""

    @property
    def notification_code(self) -> str:
        return "program_requirement_overdue"

    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve program requirement schedule data for notification templates"""
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
                raise ValueError(
                    f"Program requirement schedule not found with ID: {entity_id}"
                )

            # Calculate days overdue
            days_overdue = 0
            if schedule.submission_deadline:
                days_overdue = (
                    datetime.now().date() - schedule.submission_deadline.date()
                ).days
                days_overdue = max(0, days_overdue)  # Ensure non-negative

            return {
                "schedule_id": str(schedule.id),
                "requirement_name": schedule.program_requirement.name,
                "program_name": schedule.program_requirement.program.program_name,
                "program_code": schedule.program_requirement.program.program_code,
                "academic_year": schedule.academic_year.year_code,
                "deadline_date": (
                    schedule.submission_deadline.strftime("%Y-%m-%d")
                    if schedule.submission_deadline
                    else "N/A"
                ),
                "days_overdue": days_overdue,
                "is_mandatory": schedule.program_requirement.is_mandatory,
                "target_year": schedule.program_requirement.target_year,
            }

        except Exception as e:
            logger.error(
                f"Failed to get program requirement schedule data for ID {entity_id}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("PROGRAM_REQUIREMENT_SCHEDULE_DATA_RETRIEVAL_FAILED")



@notification_service(notification_code="program_requirement_warn")
class ProgramRequirementScheduleWarnNotificationService(BaseNotificationService):
    """Program Requirement Warning notification service"""

    @property
    def notification_code(self) -> str:
        return "program_requirement_warn"

    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve program requirement schedule data for notification templates"""
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
                raise ValueError(
                    f"Program requirement schedule not found with ID: {entity_id}"
                )

            # Calculate days remaining
            days_remaining = 0
            if schedule.submission_deadline:
                days_remaining = (
                    schedule.submission_deadline.date() - datetime.now().date()
                ).days
                days_remaining = max(0, days_remaining)  # Ensure non-negative

            return {
                "schedule_id": str(schedule.id),
                "requirement_name": schedule.program_requirement.name,
                "program_name": schedule.program_requirement.program.program_name,
                "program_code": schedule.program_requirement.program.program_code,
                "academic_year": schedule.academic_year.year_code,
                "deadline_date": (
                    schedule.submission_deadline.strftime("%Y-%m-%d")
                    if schedule.submission_deadline
                    else "N/A"
                ),
                "days_remaining": days_remaining,
                "is_mandatory": schedule.program_requirement.is_mandatory,
                "target_year": schedule.program_requirement.target_year,
            }

        except Exception as e:
            logger.error(
                f"Failed to get program requirement schedule data for ID {entity_id}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("PROGRAM_REQUIREMENT_SCHEDULE_DATA_RETRIEVAL_FAILED")



@notification_service(notification_code="program_requirement_remind")
class ProgramRequirementScheduleRemindNotificationService(BaseNotificationService):
    """Program Requirement Reminder notification service"""

    @property
    def notification_code(self) -> str:
        return "program_requirement_remind"

    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve program requirement schedule data for notification templates"""
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
                raise ValueError(
                    f"Program requirement schedule not found with ID: {entity_id}"
                )

            # Set mandatory flag text
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
                "deadline_date": (
                    schedule.submission_deadline.strftime("%Y-%m-%d")
                    if schedule.submission_deadline
                    else "N/A"
                ),
                "mandatory_flag": mandatory_flag,
                "is_mandatory": schedule.program_requirement.is_mandatory,
                "target_year": schedule.program_requirement.target_year,
            }

        except Exception as e:
            logger.error(
                f"Failed to get program requirement schedule data for ID {entity_id}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("PROGRAM_REQUIREMENT_SCHEDULE_DATA_RETRIEVAL_FAILED")

