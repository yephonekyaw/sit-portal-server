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

    # Copy the same template logic but with str(uuid.uuid4()) instead of uuid.uuid4()
    # CertificateSubmission actions
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
                    template_body="{certificate_name} submitted!\n\n{student_name} ({student_roll_number})\n{program_name}\nStatus: Under Review",
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
