from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
    templates = [
        # CertificateSubmission actions
        {
            "notification_type_code": "certificate_submission_submit",
            "channel_type": ChannelType.IN_APP,
            "template_subject": "New Certificate Submission: {certificate_name}",
            "template_body": "**{student_name}** `{student_roll_number}` submitted `{certificate_name}` for {program_name}. Status: `PENDING`",
            "template_format": TemplateFormat.MARKDOWN,
        },
        {
            "notification_type_code": "certificate_submission_update",
            "channel_type": ChannelType.IN_APP,
            "template_subject": "Certificate Submission Updated: {certificate_name}",
            "template_body": "**{student_name}** `{student_roll_number}` updated `{certificate_name}` submission for {program_name}. File: {filename}",
            "template_format": TemplateFormat.MARKDOWN,
        },
        {
            "notification_type_code": "certificate_submission_verify",
            "channel_type": ChannelType.IN_APP,
            "template_subject": "Certificate Verified: {certificate_name}",
            "template_body": "`{certificate_name}` for **{student_name}** `{student_roll_number}` approved by {verifier_name}.",
            "template_format": TemplateFormat.MARKDOWN,
        },
        {
            "notification_type_code": "certificate_submission_reject",
            "channel_type": ChannelType.IN_APP,
            "template_subject": "Certificate Rejected: {certificate_name}",
            "template_body": "`{certificate_name}` for **{student_name}** `{student_roll_number}` rejected by {verifier_name}. **Reason:** {rejection_reason}",
            "template_format": TemplateFormat.MARKDOWN,
        },
        {
            "notification_type_code": "certificate_submission_request",
            "channel_type": ChannelType.IN_APP,
            "template_subject": "Action Requested: {certificate_name}",
            "template_body": "**{student_name}** `{student_roll_number}` requested action on `{certificate_name}` - Priority: `{priority}`",
            "template_format": TemplateFormat.MARKDOWN,
        },
        # ProgramRequirement actions
        {
            "notification_type_code": "program_requirement_schedule_overdue",
            "channel_type": ChannelType.IN_APP,
            "template_subject": "Requirement Overdue: {requirement_name}",
            "template_body": "`{requirement_name}` for {program_name} is **{days_overdue} days overdue**. Deadline was {deadline_date}.",
            "template_format": TemplateFormat.MARKDOWN,
        },
        {
            "notification_type_code": "program_requirement_schedule_warn",
            "channel_type": ChannelType.IN_APP,
            "template_subject": "Deadline Approaching: {requirement_name}",
            "template_body": "`{requirement_name}` for {program_name} due in **{days_remaining} days** {deadline_date}. Submit soon!",
            "template_format": TemplateFormat.MARKDOWN,
        },
        {
            "notification_type_code": "program_requirement_schedule_remind",
            "channel_type": ChannelType.IN_APP,
            "template_subject": "Requirement Reminder: {requirement_name}",
            "template_body": "Reminder: `{requirement_name}` for {program_name} due {deadline_date}. {mandatory_flag}",
            "template_format": TemplateFormat.MARKDOWN,
        },
    ]

    notification_types = {}
    result = await db_session.execute(
        select(NotificationType).options(
            selectinload(NotificationType.channel_templates)
        )
    )
    for nt in result.scalars().all():
        notification_types[nt.code] = nt

    templates_to_add = []
    for temp_data in templates:
        nt = notification_types.get(temp_data["notification_type_code"])
        if nt:
            existing_template = next(
                (
                    ct
                    for ct in nt.channel_templates
                    if ct.channel_type == temp_data["channel_type"]
                ),
                None,
            )
            if not existing_template:
                template = NotificationChannelTemplate(
                    notification_type_id=nt.id,
                    channel_type=temp_data["channel_type"],
                    template_subject=temp_data["template_subject"],
                    template_body=temp_data["template_body"],
                    template_format=temp_data["template_format"],
                )
                templates_to_add.append(template)

    if templates_to_add:
        db_session.add_all(templates_to_add)
        logger.info(
            f"Successfully seeded {len(templates_to_add)} notification channel templates"
        )
    else:
        logger.info("No new notification channel templates to seed")
