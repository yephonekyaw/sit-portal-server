from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import NotificationType, Priority

from app.utils.logging import get_logger

logger = get_logger()


async def seed_notification_types(db_session: AsyncSession):
    notification_types = [
        # CertificateSubmission actions
        {
            "entity_type": "CertificateSubmission",
            "code": "certificate_submission_submit",
            "name": "Certificate Submitted",
            "description": "A student has submitted a new certificate.",
            "default_priority": Priority.MEDIUM,
        },
        {
            "entity_type": "CertificateSubmission",
            "code": "certificate_submission_update",
            "name": "Certificate Updated",
            "description": "A student has updated a certificate submission.",
            "default_priority": Priority.MEDIUM,
        },
        {
            "entity_type": "CertificateSubmission",
            "code": "certificate_submission_delete",
            "name": "Certificate Deleted",
            "description": "A student has deleted a certificate submission.",
            "default_priority": Priority.MEDIUM,
        },
        {
            "entity_type": "CertificateSubmission",
            "code": "certificate_submission_verify",
            "name": "Certificate Verified",
            "description": "A certificate submission has been verified.",
            "default_priority": Priority.MEDIUM,
        },
        {
            "entity_type": "CertificateSubmission",
            "code": "certificate_submission_reject",
            "name": "Certificate Rejected",
            "description": "A certificate submission has been rejected.",
            "default_priority": Priority.HIGH,
        },
        {
            "entity_type": "CertificateSubmission",
            "code": "certificate_submission_request",
            "name": "Certificate Action Requested",
            "description": "A student has requested an action on a certificate.",
            "default_priority": Priority.MEDIUM,
        },
        # ProgramRequirement actions
        {
            "entity_type": "ProgramRequirementSchedule",
            "code": "program_requirement_overdue",
            "name": "Requirement Overdue",
            "description": "A program requirement is overdue.",
            "default_priority": Priority.HIGH,
        },
        {
            "entity_type": "ProgramRequirementSchedule",
            "code": "program_requirement_warn",
            "name": "Requirement Warning",
            "description": "A warning for an upcoming program requirement deadline.",
            "default_priority": Priority.MEDIUM,
        },
        {
            "entity_type": "ProgramRequirementSchedule",
            "code": "program_requirement_remind",
            "name": "Requirement Reminder",
            "description": "A reminder for a program requirement.",
            "default_priority": Priority.LOW,
        },
    ]

    # Check existing notification types to avoid duplicates
    existing_codes_stmt = select(NotificationType.code)
    existing_codes_result = await db_session.execute(existing_codes_stmt)
    existing_codes = {code for code, in existing_codes_result.fetchall()}

    notification_types_to_add = []
    for nt_data in notification_types:
        if nt_data["code"] not in existing_codes:
            notification_type = NotificationType(**nt_data)
            notification_types_to_add.append(notification_type)

    if notification_types_to_add:
        db_session.add_all(notification_types_to_add)
        logger.info(
            f"Successfully seeded {len(notification_types_to_add)} notification types"
        )
    else:
        logger.info("No new notification types to seed")
