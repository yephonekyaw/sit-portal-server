from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import NotificationType, NotificationChannelTemplate, ChannelType
from app.utils.logging import get_logger

logger = get_logger()


class BaseNotificationService(ABC):
    """Base notification service with common functionality for all notification types"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self._notification_type_id: Optional[uuid.UUID] = None
        self._priority: Optional[str] = None

    async def _fetch_notification_type(self) -> NotificationType:
        """Fetch notification type from database using notification code"""
        if not hasattr(self, "_cached_notification_type"):
            result = await self.db.execute(
                select(NotificationType).where(
                    NotificationType.code == self.notification_code
                )
            )
            notification_type = result.scalar_one_or_none()
            if not notification_type:
                raise ValueError(
                    f"Notification type not found for code: {self.notification_code}"
                )
            self._cached_notification_type = notification_type
        return self._cached_notification_type

    @property
    @abstractmethod
    def notification_code(self) -> str:
        """Each sub class must define its notification code"""
        pass

    @abstractmethod
    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """
        Retrieve all data needed to create notification templates for this notification type
        Each sub class implements this with entity-specific logic
        """
        pass

    async def construct_message(
        self, channel_type: str, notification_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Construct the subject and body using templates from NotificationChannelTemplate table
        Returns dict with 'subject' and 'body' keys
        """
        try:
            # Get notification type to access templates
            notification_type = await self._fetch_notification_type()

            # Convert string channel_type to enum
            try:
                channel_enum = ChannelType(channel_type.lower())
            except ValueError:
                logger.warning(
                    f"Invalid channel type: {channel_type}, defaulting to IN_APP"
                )
                channel_enum = ChannelType.IN_APP

            # Fetch the template for this notification type and channel
            template_result = await self.db.execute(
                select(NotificationChannelTemplate).where(
                    NotificationChannelTemplate.notification_type_id
                    == notification_type.id,
                    NotificationChannelTemplate.channel_type == channel_enum,
                    NotificationChannelTemplate.is_active.is_(True),
                )
            )
            template = template_result.scalar_one_or_none()

            if not template:
                # Fallback if no template found
                logger.warning(
                    f"No template found for notification {self.notification_code} "
                    f"and channel {channel_type}"
                )
                return {
                    "subject": f"{notification_type.name}",
                    "body": f"You have a new {notification_type.name.lower()} notification.",
                }

            # Format the template with notification data
            try:
                formatted_subject = (
                    template.template_subject.format(**notification_data)
                    if template.template_subject
                    else notification_type.name
                )
                formatted_body = template.template_body.format(**notification_data)

                return {"subject": formatted_subject, "body": formatted_body}

            except KeyError as e:
                logger.error(
                    f"Template formatting error for {self.notification_code}: "
                    f"Missing placeholder {str(e)} in notification_data"
                )
                # Return template with unformatted placeholders as fallback
                return {
                    "subject": template.template_subject or notification_type.name,
                    "body": template.template_body,
                }

        except Exception as e:
            logger.error(
                f"Failed to construct message for {self.notification_code}: {str(e)}",
                exc_info=True,
            )
            # Final fallback
            return {"subject": "Notification", "body": "You have a new notification."}

    async def get_notification_type_id(self) -> uuid.UUID:
        """Get notification type ID from database"""
        if self._notification_type_id is None:
            notification_type = await self._fetch_notification_type()
            self._notification_type_id = notification_type.id
        return self._notification_type_id

    async def get_priority(self) -> str:
        """Get priority from database"""
        if self._priority is None:
            notification_type = await self._fetch_notification_type()
            self._priority = notification_type.default_priority.value
        return self._priority

    async def create(
        self,
        entity_id: uuid.UUID,
        actor_type: str,
        recipient_ids: List[uuid.UUID],
        actor_id: Optional[uuid.UUID] = None,
        scheduled_for: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        **metadata,
    ) -> Dict[str, Any]:
        """
        Create notification(s) for the specified recipients
        Common create logic that sub classes can use
        """
        try:
            # TODO: Implement notification creation logic
            # This will create records in the notifications table
            logger.info(
                f"Creating {self.__class__.__name__} notification for entity {entity_id} "
                f"with {len(recipient_ids)} recipients"
            )

            # Implementation will go here once we have the database model
            # For now, return placeholder response
            notification_type_id = await self.get_notification_type_id()
            priority = await self.get_priority()

            return {
                "notification_type_id": notification_type_id,
                "priority": priority,
                "entity_id": str(entity_id),
                "actor_type": actor_type,
                "actor_id": str(actor_id) if actor_id else None,
                "recipient_count": len(recipient_ids),
                "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(
                f"Failed to create {self.__class__.__name__} notification: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("NOTIFICATION_CREATION_FAILED")
