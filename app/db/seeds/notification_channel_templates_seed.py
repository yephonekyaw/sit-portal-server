import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.db.models import (
    ChannelType,
    NotificationChannelTemplate,
    NotificationType,
    TemplateFormat,
)
from app.utils.logging import get_logger

logger = get_logger()


async def seed_notification_channel_templates(db_session: AsyncSession):
    """Seed notification channel templates data - clear existing and add new"""

    # Clear existing templates
    await db_session.execute(delete(NotificationChannelTemplate))
    await db_session.commit()

    # Get all notification types
    result = await db_session.execute(select(NotificationType))
    notification_types = {nt.code: nt for nt in result.scalars().all()}

    templates = []

    # CertificateSubmission actions
    if "certificate_submission_submit" in notification_types:
        nt_id = notification_types["certificate_submission_submit"].id
        templates.extend([
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.IN_APP,
                template_subject="Certificate Submitted: {certificate_name}",
                template_body="**New Submission**\n{student_name} ({student_roll_number}) from {program_name}\nSubmitted: {certificate_name}\nStatus: Under Review",
                template_format=TemplateFormat.MARKDOWN,
                is_active=True,
            ),
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.LINE_APP,
                template_subject="Certificate Submitted",
                template_body="{certificate_name} submitted!\n\n{student_name} ({student_roll_number})\n{program_name}\nStatus: Under Review",
                template_format=TemplateFormat.TEXT,
                is_active=True,
            ),
        ])

    if "certificate_submission_update" in notification_types:
        nt_id = notification_types["certificate_submission_update"].id
        templates.extend([
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.IN_APP,
                template_subject="Certificate Updated: {certificate_name}",
                template_body="**Submission Updated**\n{student_name} ({student_roll_number}) from {program_name}\nUpdated: {certificate_name}\nStatus: Pending Review",
                template_format=TemplateFormat.MARKDOWN,
                is_active=True,
            ),
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.LINE_APP,
                template_subject="Certificate Updated",
                template_body="{certificate_name} updated!\n\n{student_name} ({student_roll_number})\n{program_name}\nStatus: Pending Review",
                template_format=TemplateFormat.TEXT,
                is_active=True,
            ),
        ])

    if "certificate_submission_verify" in notification_types:
        nt_id = notification_types["certificate_submission_verify"].id
        templates.extend([
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.IN_APP,
                template_subject="Certificate Approved: {certificate_name}",
                template_body="**Congratulations!**\n{certificate_name} for {student_name} ({student_roll_number})\nApproved by: {verifier_name}\nProgram: {program_name}",
                template_format=TemplateFormat.MARKDOWN,
                is_active=True,
            ),
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.LINE_APP,
                template_subject="Certificate Approved!",
                template_body="APPROVED!\n\n{certificate_name}\n{student_name} ({student_roll_number})\nVerified by: {verifier_name}\n{program_name}",
                template_format=TemplateFormat.TEXT,
                is_active=True,
            ),
        ])

    if "certificate_submission_reject" in notification_types:
        nt_id = notification_types["certificate_submission_reject"].id
        templates.extend([
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.IN_APP,
                template_subject="Certificate Rejected: {certificate_name}",
                template_body="**Action Required**\n{certificate_name} for {student_name} ({student_roll_number})\nRejected by: {verifier_name}\nReason: Please check submission requirements",
                template_format=TemplateFormat.MARKDOWN,
                is_active=True,
            ),
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.LINE_APP,
                template_subject="Certificate Rejected",
                template_body="REJECTED\n\n{certificate_name}\n{student_name} ({student_roll_number})\nReviewed by: {verifier_name}\nPlease recheck requirements and resubmit",
                template_format=TemplateFormat.TEXT,
                is_active=True,
            ),
        ])

    if "certificate_submission_request" in notification_types:
        nt_id = notification_types["certificate_submission_request"].id
        templates.extend([
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.IN_APP,
                template_subject="Manual Review Required: {certificate_name}",
                template_body="**Review Needed**\n{certificate_name} for {student_name} ({student_roll_number})\nRequires manual verification\nProgram: {program_name}",
                template_format=TemplateFormat.MARKDOWN,
                is_active=True,
            ),
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.LINE_APP,
                template_subject="Manual Review Required",
                template_body="MANUAL REVIEW NEEDED\n\n{certificate_name}\n{student_name} ({student_roll_number})\n{program_name}\nReview in progress...",
                template_format=TemplateFormat.TEXT,
                is_active=True,
            ),
        ])

    if "certificate_submission_delete" in notification_types:
        nt_id = notification_types["certificate_submission_delete"].id
        templates.extend([
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.IN_APP,
                template_subject="Certificate Deleted: {certificate_name}",
                template_body="**Submission Deleted**\n{certificate_name} for {student_name} ({student_roll_number})\nDeleted from system\nProgram: {program_name}",
                template_format=TemplateFormat.MARKDOWN,
                is_active=True,
            ),
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.LINE_APP,
                template_subject="Certificate Deleted",
                template_body="DELETED\n\n{certificate_name}\n{student_name} ({student_roll_number})\n{program_name}\nRemoved from system",
                template_format=TemplateFormat.TEXT,
                is_active=True,
            ),
        ])

    # ProgramRequirementSchedule actions
    if "program_requirement_schedule_remind" in notification_types:
        nt_id = notification_types["program_requirement_schedule_remind"].id
        templates.extend([
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.IN_APP,
                template_subject="Reminder: {requirement_name}",
                template_body="**Upcoming Requirement**\n{requirement_name} for {program_name}\nDue: {deadline_date}\n{mandatory_flag}\nDon't forget to submit!",
                template_format=TemplateFormat.MARKDOWN,
                is_active=True,
            ),
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.LINE_APP,
                template_subject="Requirement Reminder",
                template_body="REMINDER\n\n{requirement_name}\n{program_name}\nDue: {deadline_date}\n{mandatory_flag}\nStart preparing your submission!",
                template_format=TemplateFormat.TEXT,
                is_active=True,
            ),
        ])

    if "program_requirement_schedule_warn" in notification_types:
        nt_id = notification_types["program_requirement_schedule_warn"].id
        templates.extend([
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.IN_APP,
                template_subject="Deadline Approaching: {requirement_name}",
                template_body="**Urgent: {days_remaining} Days Left**\n{requirement_name} for {program_name}\nDeadline: {deadline_date}\nSubmit soon to avoid late penalties!",
                template_format=TemplateFormat.MARKDOWN,
                is_active=True,
            ),
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.LINE_APP,
                template_subject="Deadline Approaching!",
                template_body="URGENT: {days_remaining} DAYS LEFT!\n\n{requirement_name}\n{program_name}\nDeadline: {deadline_date}\nSubmit now to avoid penalties!",
                template_format=TemplateFormat.TEXT,
                is_active=True,
            ),
        ])

    if "program_requirement_schedule_late" in notification_types:
        nt_id = notification_types["program_requirement_schedule_late"].id
        templates.extend([
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.IN_APP,
                template_subject="Late Submission: {requirement_name}",
                template_body="**Action Required**\n{requirement_name} for {program_name}\nWas due: {deadline_date}\nYou are {days_late} days late\nSubmit immediately to minimize penalties!",
                template_format=TemplateFormat.MARKDOWN,
                is_active=True,
            ),
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.LINE_APP,
                template_subject="Late Submission",
                template_body="LATE SUBMISSION!\n\n{requirement_name}\n{program_name}\n{days_late} days overdue\nWas due: {deadline_date}\nSubmit NOW to avoid penalties!",
                template_format=TemplateFormat.TEXT,
                is_active=True,
            ),
        ])

    if "program_requirement_schedule_overdue" in notification_types:
        nt_id = notification_types["program_requirement_schedule_overdue"].id
        templates.extend([
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.IN_APP,
                template_subject="Overdue: {requirement_name}",
                template_body="**Critical: {days_overdue} Days Overdue**\n{requirement_name} for {program_name}\nDeadline was: {deadline_date}\nContact your advisor immediately!",
                template_format=TemplateFormat.MARKDOWN,
                is_active=True,
            ),
            NotificationChannelTemplate(
                id=uuid.uuid4(),
                notification_type_id=nt_id,
                channel_type=ChannelType.LINE_APP,
                template_subject="CRITICAL: Overdue!",
                template_body="CRITICAL: {days_overdue} DAYS OVERDUE!\n\n{requirement_name}\n{program_name}\nWas due: {deadline_date}\nContact your advisor IMMEDIATELY!",
                template_format=TemplateFormat.TEXT,
                is_active=True,
            ),
        ])

    if templates:
        db_session.add_all(templates)
        await db_session.commit()
        logger.info(f"Seeded {len(templates)} notification channel templates")
    else:
        logger.info("No templates to seed - notification types may be missing")