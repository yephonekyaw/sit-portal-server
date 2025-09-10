import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select, insert

from app.db.models import (
    NotificationType,
    NotificationChannelTemplate,
    ChannelType,
    Notification,
    NotificationRecipient,
    ActorType,
    NotificationStatus,
)
from app.utils.logging import get_logger

logger = get_logger()


class BaseNotificationService(ABC):
    """Simplified base notification service"""

    def __init__(self, db_session: Session, notification_code: str):
        self.db = db_session
        self.notification_code = notification_code
        self._notification_type: Optional[NotificationType] = None

    async def _get_notification_type(self) -> NotificationType:
        """Get notification type from database"""
        if self._notification_type is None:
            result = self.db.execute(
                select(NotificationType).where(
                    NotificationType.code == self.notification_code
                )
            )
            self._notification_type = result.scalar_one_or_none()
            if not self._notification_type:
                raise ValueError(
                    f"Notification type not found: {self.notification_code}"
                )
        return self._notification_type

    @abstractmethod
    async def get_notification_data(
        self, entity_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get data for notification templates - implemented by subclasses"""
        pass

    async def construct_message(
        self, channel_type: str, notification_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Build message from template and data"""
        try:
            notification_type = await self._get_notification_type()

            try:
                channel_enum = ChannelType(channel_type.lower())
            except ValueError:
                channel_enum = ChannelType.IN_APP

            template_result = self.db.execute(
                select(NotificationChannelTemplate).where(
                    NotificationChannelTemplate.notification_type_id
                    == notification_type.id,
                    NotificationChannelTemplate.channel_type == channel_enum,
                    NotificationChannelTemplate.is_active == True,
                )
            )
            template = template_result.scalar_one_or_none()

            if not template:
                return {
                    "subject": notification_type.name,
                    "body": f"New {notification_type.name.lower()} notification",
                }

            try:
                subject = (
                    template.template_subject.format(**notification_data)
                    if template.template_subject
                    else notification_type.name
                )
                body = template.template_body.format(**notification_data)
                return {"subject": subject, "body": body}

            except KeyError as e:
                logger.error(
                    f"Template error for {self.notification_code}: missing {e}"
                )
                return {
                    "subject": template.template_subject or notification_type.name,
                    "body": template.template_body,
                }

        except Exception as e:
            logger.error(f"Message construction failed: {e}")
            return {"subject": "Notification", "body": "You have a notification"}

    async def create(
        self,
        entity_id: uuid.UUID,
        actor_type: str,
        recipient_ids: List[uuid.UUID],
        actor_id: Optional[uuid.UUID] = None,
        scheduled_for: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        in_app_enabled: bool = True,
        line_app_enabled: bool = False,
        **metadata,
    ) -> uuid.UUID:
        """Create notification and recipients"""
        try:
            notification_type = await self._get_notification_type()

            # Create notification record
            notification_data = {
                "notification_type_id": notification_type.id,
                "entity_id": entity_id,
                "actor_type": ActorType(actor_type),
                "actor_id": actor_id,
                "priority": notification_type.default_priority,
                "notification_metadata": json.dumps(metadata) if metadata else "",
                "scheduled_for": scheduled_for,
                "expires_at": expires_at,
            }

            result = self.db.execute(
                insert(Notification)
                .values(**notification_data)
                .returning(Notification.id)
            )
            notification_id = result.scalar_one()

            # Create recipient records
            recipient_data = []
            for recipient_id in recipient_ids:
                recipient_data.append(
                    {
                        "notification_id": notification_id,
                        "recipient_id": recipient_id,
                        "in_app_enabled": in_app_enabled,
                        "line_app_enabled": line_app_enabled,
                        "status": NotificationStatus.PENDING,
                    }
                )

            if recipient_data:
                self.db.execute(insert(NotificationRecipient).values(recipient_data))

            self.db.commit()

            logger.info(
                f"Created notification {notification_id} for {len(recipient_ids)} recipients"
            )
            return notification_id  # type: ignore

        except Exception as e:
            logger.error(f"Failed to create notification: {e}", exc_info=True)
            raise
