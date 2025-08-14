from typing import Dict, Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .base import BaseNotificationService
from .registry import notification_service
from app.db.models import (
    CertificateSubmission,
    Student,
    ProgramRequirementSchedule,
    ProgramRequirement,
)
from app.utils.logging import get_logger

logger = get_logger()


@notification_service(notification_code="certificate_submission_submit")
class CertificateSubmissionSubmitNotificationService(BaseNotificationService):
    """Certificate Submitted notification service"""

    @property
    def notification_code(self) -> str:
        return "certificate_submission_submit"

    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve certificate submission data for notification templates"""
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
                raise ValueError(
                    f"Certificate submission not found with ID: {entity_id}"
                )

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
                    submission.created_at.isoformat() if submission.created_at else None
                ),
                "status": submission.submission_status.value,
            }

        except Exception as e:
            logger.error(
                f"Failed to get certificate submission data for ID {entity_id}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("CERTIFICATE_SUBMISSION_DATA_RETRIEVAL_FAILED")



@notification_service(notification_code="certificate_submission_update")
class CertificateSubmissionUpdateNotificationService(BaseNotificationService):
    """Certificate Updated notification service"""

    @property
    def notification_code(self) -> str:
        return "certificate_submission_update"

    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve certificate submission data for notification templates"""
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
                raise ValueError(
                    f"Certificate submission not found with ID: {entity_id}"
                )

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
                "updated_date": (
                    submission.updated_at.isoformat() if submission.updated_at else None
                ),
                "status": submission.submission_status.value,
            }

        except Exception as e:
            logger.error(
                f"Failed to get certificate submission data for ID {entity_id}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("CERTIFICATE_SUBMISSION_DATA_RETRIEVAL_FAILED")



@notification_service(notification_code="certificate_submission_delete")
class CertificateSubmissionDeleteNotificationService(BaseNotificationService):
    """Certificate Deleted notification service"""

    @property
    def notification_code(self) -> str:
        return "certificate_submission_delete"

    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve certificate submission data for notification templates"""
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
                raise ValueError(
                    f"Certificate submission not found with ID: {entity_id}"
                )

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
                "status": submission.submission_status.value,
            }

        except Exception as e:
            logger.error(
                f"Failed to get certificate submission data for ID {entity_id}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("CERTIFICATE_SUBMISSION_DATA_RETRIEVAL_FAILED")



@notification_service(notification_code="certificate_submission_verify")
class CertificateSubmissionVerifyNotificationService(BaseNotificationService):
    """Certificate Verified notification service"""

    @property
    def notification_code(self) -> str:
        return "certificate_submission_verify"

    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve certificate submission data for notification templates"""
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
                raise ValueError(
                    f"Certificate submission not found with ID: {entity_id}"
                )

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
                "verifier_name": "System",  # Verifier info comes from verification_history
                "verified_date": (
                    submission.updated_at.isoformat() if submission.updated_at else None
                ),
                "status": submission.submission_status.value,
            }

        except Exception as e:
            logger.error(
                f"Failed to get certificate submission data for ID {entity_id}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("CERTIFICATE_SUBMISSION_DATA_RETRIEVAL_FAILED")



@notification_service(notification_code="certificate_submission_reject")
class CertificateSubmissionRejectNotificationService(BaseNotificationService):
    """Certificate Rejected notification service"""

    @property
    def notification_code(self) -> str:
        return "certificate_submission_reject"

    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve certificate submission data for notification templates"""
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
                raise ValueError(
                    f"Certificate submission not found with ID: {entity_id}"
                )

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
                "verifier_name": "System",  # Verifier info comes from verification_history
                "rejected_date": (
                    submission.updated_at.isoformat() if submission.updated_at else None
                ),
                "status": submission.submission_status.value,
            }

        except Exception as e:
            logger.error(
                f"Failed to get certificate submission data for ID {entity_id}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("CERTIFICATE_SUBMISSION_DATA_RETRIEVAL_FAILED")



@notification_service(notification_code="certificate_submission_request")
class CertificateSubmissionRequestNotificationService(BaseNotificationService):
    """Certificate Review Requested notification service"""

    @property
    def notification_code(self) -> str:
        return "certificate_submission_request"

    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve certificate submission data for notification templates"""
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
                raise ValueError(
                    f"Certificate submission not found with ID: {entity_id}"
                )

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
                "status": submission.submission_status.value,
            }

        except Exception as e:
            logger.error(
                f"Failed to get certificate submission data for ID {entity_id}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("CERTIFICATE_SUBMISSION_DATA_RETRIEVAL_FAILED")

