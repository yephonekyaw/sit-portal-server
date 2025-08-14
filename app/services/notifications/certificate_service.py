from typing import Dict, Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .base import BaseNotificationService
from app.db.models import (
    CertificateSubmission,
    Student,
    ProgramRequirementSchedule,
    ProgramRequirement,
)
from app.utils.logging import get_logger
from app.utils.errors import BusinessLogicError

logger = get_logger()


class CertificateSubmissionNotificationService(BaseNotificationService):
    """Unified certificate submission notification service"""

    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Get certificate submission data for all notification types"""
        try:
            result = await self.db.execute(
                select(CertificateSubmission)
                .options(
                    selectinload(CertificateSubmission.student).selectinload(
                        Student.user
                    ),
                    selectinload(CertificateSubmission.certificate_type),
                    selectinload(CertificateSubmission.requirement_schedule)
                    .selectinload(ProgramRequirementSchedule.program_requirement)
                    .selectinload(ProgramRequirement.program),
                )
                .where(CertificateSubmission.id == entity_id)
            )
            submission = result.scalar_one_or_none()

            if not submission:
                raise ValueError(f"Certificate submission not found: {entity_id}")

            return {
                "submission_id": str(submission.id),
                "certificate_name": submission.certificate_type.name,
                "student_name": f"{submission.student.user.first_name} {submission.student.user.last_name}",
                "student_roll_number": submission.student.roll_number,
                "program_name": (
                    submission.requirement_schedule.program_requirement.program.program_name
                    if submission.requirement_schedule
                    else "N/A"
                ),
                "submission_date": (
                    submission.created_at.strftime("%Y-%m-%d")
                    if submission.created_at
                    else "N/A"
                ),
                "updated_date": (
                    submission.updated_at.strftime("%Y-%m-%d")
                    if submission.updated_at
                    else "N/A"
                ),
                "status": submission.submission_status.value,
                "verifier_name": "System",  # Can be enhanced later
                "filename": submission.filename,
                "file_size": submission.file_size,
            }

        except Exception as e:
            raise BusinessLogicError(
                f"Failed to get certificate submission data for {entity_id}: {e}"
            )


def create_certificate_service(
    db_session, notification_code: str
) -> CertificateSubmissionNotificationService:
    """Create certificate submission notification service"""
    return CertificateSubmissionNotificationService(db_session, notification_code)