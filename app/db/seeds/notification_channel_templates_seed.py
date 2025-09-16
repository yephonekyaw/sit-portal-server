import uuid
from sqlalchemy.orm import Session
from sqlalchemy import delete, select

from app.db.models import (
    ChannelType,
    NotificationChannelTemplate,
    NotificationType,
    TemplateFormat,
)
from app.utils.logging import get_logger

logger = get_logger()


def seed_notification_channel_templates(db_session: Session):
    """Sync version: Seed notification channel templates data - clear existing and add new"""

    # Clear existing templates
    db_session.execute(delete(NotificationChannelTemplate))
    db_session.commit()

    # Get all notification types
    result = db_session.execute(select(NotificationType))
    notification_types = {nt.code: nt for nt in result.scalars().all()}

    templates = []

    # Certificate Submission Submit
    if "certificate_submission_submit" in notification_types:
        nt_id = notification_types["certificate_submission_submit"].id
        templates.extend(
            [
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.IN_APP,
                    template_subject="Certificate Submitted: {certificate_name}",
                    template_body="**New Submission**\n{student_name} ({student_roll_number}) from {program_name}\nSubmitted: {certificate_name}\nStatus: Under Review",
                    template_format=TemplateFormat.MARKDOWN,
                    is_active=True,
                ),
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.LINE_APP,
                    template_subject="Certificate Submitted",
                    template_body="{certificate_name} submitted!\n{student_name} ({student_roll_number})\n{program_name}\nStatus: Under Review",
                    template_format=TemplateFormat.TEXT,
                    is_active=True,
                ),
            ]
        )

    # Certificate Submission Update
    if "certificate_submission_update" in notification_types:
        nt_id = notification_types["certificate_submission_update"].id
        templates.extend(
            [
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.IN_APP,
                    template_subject="Certificate Updated: {certificate_name}",
                    template_body="**Submission Updated**\n{student_name} ({student_roll_number}) from {program_name}\nUpdated: {certificate_name}\nStatus: Under Review",
                    template_format=TemplateFormat.MARKDOWN,
                    is_active=True,
                ),
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.LINE_APP,
                    template_subject="Certificate Updated",
                    template_body="{certificate_name} updated!\n{student_name} ({student_roll_number})\n{program_name}\nStatus: Under Review",
                    template_format=TemplateFormat.TEXT,
                    is_active=True,
                ),
            ]
        )

    # Certificate Submission Delete
    if "certificate_submission_delete" in notification_types:
        nt_id = notification_types["certificate_submission_delete"].id
        templates.extend(
            [
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.IN_APP,
                    template_subject="Certificate Deleted: {certificate_name}",
                    template_body="**Submission Deleted**\n{student_name} ({student_roll_number}) from {program_name}\nDeleted: {certificate_name}",
                    template_format=TemplateFormat.MARKDOWN,
                    is_active=True,
                ),
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.LINE_APP,
                    template_subject="Certificate Deleted",
                    template_body="{certificate_name} deleted\n{student_name} ({student_roll_number})\n{program_name}",
                    template_format=TemplateFormat.TEXT,
                    is_active=True,
                ),
            ]
        )

    # Certificate Submission Verify
    if "certificate_submission_verify" in notification_types:
        nt_id = notification_types["certificate_submission_verify"].id
        templates.extend(
            [
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.IN_APP,
                    template_subject="Certificate Approved: {certificate_name}",
                    template_body="**Approved**\nYour certificate submission has been approved!\n**Certificate:** {certificate_name}\n**Program:** {program_name}\n**Status:** Approved",
                    template_format=TemplateFormat.MARKDOWN,
                    is_active=True,
                ),
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.LINE_APP,
                    template_subject="Certificate Approved",
                    template_body="Great news! Your certificate has been approved.\n{certificate_name}\n{program_name}\nStatus: Approved",
                    template_format=TemplateFormat.TEXT,
                    is_active=True,
                ),
            ]
        )

    # Certificate Submission Reject
    if "certificate_submission_reject" in notification_types:
        nt_id = notification_types["certificate_submission_reject"].id
        templates.extend(
            [
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.IN_APP,
                    template_subject="Certificate Rejected: {certificate_name}",
                    template_body="**Rejected**\nYour certificate submission requires revision.\n**Certificate:** {certificate_name}\n**Program:** {program_name}\n**Status:** Rejected\n**Reason:** {rejection_reason}",
                    template_format=TemplateFormat.MARKDOWN,
                    is_active=True,
                ),
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.LINE_APP,
                    template_subject="Certificate Rejected",
                    template_body="Your certificate needs revision.\n{certificate_name}\n{program_name}\nReason: {rejection_reason}",
                    template_format=TemplateFormat.TEXT,
                    is_active=True,
                ),
            ]
        )

    # Certificate Submission Request (Manual Review)
    if "certificate_submission_request" in notification_types:
        nt_id = notification_types["certificate_submission_request"].id
        templates.extend(
            [
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.IN_APP,
                    template_subject="Manual Review Required: {certificate_name}",
                    template_body="**Manual Review Required**\nA certificate submission needs your attention.\n**Student:** {student_name} ({student_roll_number})\n**Certificate:** {certificate_name}\n**Program:** {program_name}\n**Status:** Awaiting Manual Review",
                    template_format=TemplateFormat.MARKDOWN,
                    is_active=True,
                ),
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.LINE_APP,
                    template_subject="Manual Review Required",
                    template_body="Certificate needs manual review:\n{student_name} ({student_roll_number})\n{certificate_name}\n{program_name}",
                    template_format=TemplateFormat.TEXT,
                    is_active=True,
                ),
            ]
        )

    # Program Requirement Schedule Remind
    if "program_requirement_schedule_remind" in notification_types:
        nt_id = notification_types["program_requirement_schedule_remind"].id
        templates.extend(
            [
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.IN_APP,
                    template_subject="Reminder: {requirement_name} Due Soon",
                    template_body="**Reminder**\nDon't forget to submit your certificate!\n**Requirement:** {requirement_name}\n**Program:** {program_name}\n**Due Date:** {due_date}\n**Days Remaining:** {days_remaining}",
                    template_format=TemplateFormat.MARKDOWN,
                    is_active=True,
                ),
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.LINE_APP,
                    template_subject="Reminder: Certificate Due Soon",
                    template_body="Don't forget to submit:\n{requirement_name}\n{program_name}\nDue: {due_date}\n{days_remaining} days left",
                    template_format=TemplateFormat.TEXT,
                    is_active=True,
                ),
            ]
        )

    # Program Requirement Schedule Warn
    if "program_requirement_schedule_warn" in notification_types:
        nt_id = notification_types["program_requirement_schedule_warn"].id
        templates.extend(
            [
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.IN_APP,
                    template_subject="Warning: {requirement_name} Due Soon",
                    template_body="**Warning**\nUrgent: Certificate submission deadline approaching!\n**Requirement:** {requirement_name}\n**Program:** {program_name}\n**Due Date:** {due_date}\n**Days Remaining:** {days_remaining}",
                    template_format=TemplateFormat.MARKDOWN,
                    is_active=True,
                ),
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.LINE_APP,
                    template_subject="Warning: Deadline Approaching",
                    template_body="Urgent! Submit soon:\n{requirement_name}\n{program_name}\nDue: {due_date}\nOnly {days_remaining} days left!",
                    template_format=TemplateFormat.TEXT,
                    is_active=True,
                ),
            ]
        )

    # Program Requirement Schedule Late
    if "program_requirement_schedule_late" in notification_types:
        nt_id = notification_types["program_requirement_schedule_late"].id
        templates.extend(
            [
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.IN_APP,
                    template_subject="Late: {requirement_name} Past Due",
                    template_body="**Late Submission**\nYour certificate submission is past due.\n**Requirement:** {requirement_name}\n**Program:** {program_name}\n**Was Due:** {due_date}\n**Days Late:** {days_late}",
                    template_format=TemplateFormat.MARKDOWN,
                    is_active=True,
                ),
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.LINE_APP,
                    template_subject="Late Submission",
                    template_body="Past due! Please submit:\n{requirement_name}\n{program_name}\nWas due: {due_date}\n{days_overdue} days overdue",
                    template_format=TemplateFormat.TEXT,
                    is_active=True,
                ),
            ]
        )

    # Program Requirement Schedule Overdue
    if "program_requirement_schedule_overdue" in notification_types:
        nt_id = notification_types["program_requirement_schedule_overdue"].id
        templates.extend(
            [
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.IN_APP,
                    template_subject="Overdue: {requirement_name} Critical",
                    template_body="**Overdue - Critical**\nImmediate action required for your certificate submission.\n**Requirement:** {requirement_name}\n**Program:** {program_name}\n**Was Due:** {due_date}\n**Days Overdue:** {days_late}\nPlease contact your program coordinator immediately.",
                    template_format=TemplateFormat.MARKDOWN,
                    is_active=True,
                ),
                NotificationChannelTemplate(
                    id=str(uuid.uuid4()),
                    notification_type_id=nt_id,
                    channel_type=ChannelType.LINE_APP,
                    template_subject="OVERDUE - Critical",
                    template_body="CRITICAL: Submit immediately!\n{requirement_name}\n{program_name}\nWas due: {due_date}\n{days_late} days overdue\nContact coordinator now!",
                    template_format=TemplateFormat.TEXT,
                    is_active=True,
                ),
            ]
        )

    if templates:
        db_session.add_all(templates)
        db_session.commit()
        logger.info(f"Seeded {len(templates)} notification channel templates")
    else:
        logger.info("No templates to seed - notification types may be missing")
