import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ChannelType,
    Notification,
    NotificationRecipient,
    NotificationType,
    User,
    UserType,
    ActorType,
    NotificationStatus,
    Priority,
)


class NotificationService:
    """Service for managing notifications and recipients"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def _get_notification_type_by_code(self, code: str) -> NotificationType:
        """Get notification type by code or raise ValueError if not found."""
        result = await self.db.execute(
            select(NotificationType).where(NotificationType.code == code)
        )
        notification_type = result.scalar_one_or_none()
        if not notification_type:
            raise ValueError(f"Notification type '{code}' not found.")
        return notification_type

    async def _get_recipient_by_ids(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[NotificationRecipient]:
        """Get notification recipient by notification and user IDs."""
        result = await self.db.execute(
            select(NotificationRecipient).where(
                NotificationRecipient.notification_id == notification_id,
                NotificationRecipient.recipient_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _create_notification_recipients(
        self, notification_id: uuid.UUID, recipient_ids: List[uuid.UUID]
    ) -> None:
        """Create notification recipients for given user IDs."""
        # Get all valid users in one query
        users_result = await self.db.execute(select(User).where(User.id.in_(recipient_ids)))
        users = {user.id: user for user in users_result.scalars().all()}

        # Create recipients
        recipients = []
        for recipient_id in recipient_ids:
            user = users.get(recipient_id)
            if user:
                recipients.append(
                    NotificationRecipient(
                        notification_id=notification_id,
                        recipient_id=user.id,
                        status=NotificationStatus.PENDING,
                        in_app_enabled=True,
                        microsoft_teams_enabled=(user.user_type == UserType.STUDENT),
                    )
                )

        self.db.add_all(recipients)

    async def create_notification(
        self,
        notification_type_code: str,
        entity_id: uuid.UUID,
        actor_type: ActorType,
        subject: str,
        body: str,
        recipient_ids: List[uuid.UUID],
        actor_id: Optional[uuid.UUID] = None,
        priority: Optional[Priority] = None,
        notification_metadata: Optional[dict] = None,
        scheduled_for: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> Notification:
        """Create a new notification and link it to recipients."""
        notification_type = await self._get_notification_type_by_code(
            notification_type_code
        )

        notification = Notification(
            notification_type_id=notification_type.id,
            entity_id=entity_id,
            actor_type=actor_type,
            actor_id=actor_id,
            subject=subject,
            body=body,
            priority=priority or notification_type.default_priority,
            notification_metadata=notification_metadata,
            scheduled_for=scheduled_for,
            expires_at=expires_at,
        )

        self.db.add(notification)
        await self.db.flush()  # Get notification ID

        await self._create_notification_recipients(notification.id, recipient_ids)
        await self.db.commit()

        return notification

    async def mark_notification_as_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Mark a notification as read for a specific user."""
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                NotificationRecipient.notification_id == notification_id,
                NotificationRecipient.recipient_id == user_id,
            )
            .values(
                status=NotificationStatus.READ, read_at=datetime.now(timezone.utc)
            )
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_notification_as_delivered(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
        channel_type: Optional[ChannelType] = None,
    ) -> bool:
        """Mark a notification as delivered for a specific user."""
        update_values = {
            "status": NotificationStatus.DELIVERED,
            "delivered_at": datetime.now(timezone.utc),
        }

        if channel_type == ChannelType.MICROSOFT_TEAMS:
            update_values["microsoft_teams_sent_at"] = datetime.now(timezone.utc)

        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                NotificationRecipient.notification_id == notification_id,
                NotificationRecipient.recipient_id == user_id,
            )
            .values(**update_values)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_notification_as_failed(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Mark a notification as failed for a specific user."""
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                NotificationRecipient.notification_id == notification_id,
                NotificationRecipient.recipient_id == user_id,
            )
            .values(status=NotificationStatus.FAILED)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_notifications_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all unread notifications as read for a user."""
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                NotificationRecipient.recipient_id == user_id,
                NotificationRecipient.status == NotificationStatus.DELIVERED,
            )
            .values(
                status=NotificationStatus.READ, read_at=datetime.now(timezone.utc)
            )
        )
        await self.db.commit()
        return result.rowcount