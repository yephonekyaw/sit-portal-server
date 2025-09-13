from typing import Dict, Any, Optional, List

from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.db.models import NotificationRecipient, Notification, NotificationStatus
from app.utils.logging import get_logger
from app.schemas.notification_schemas import (
    GetUserNotificationItem,
)
from app.utils.datetime_utils import naive_utc_now

from .registry import NotificationServiceRegistry

logger = get_logger()


class UserNotificationService:
    """Service for retrieving and managing user notifications"""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def get_user_notifications(
        self,
        user_id: str,
        status_filter: Optional[NotificationStatus] = None,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all notifications for a specific user with formatted content

        Args:
            user_id: The user's UUID
            status_filter: Optional status filter (PENDING, DELIVERED, READ, etc.)
            limit: Maximum number of notifications to return
            offset: Offset for pagination
            unread_only: If True, only return unread notifications

        Returns:
            List of formatted notifications with subject and body
        """
        try:
            # Build the query
            query = (
                select(NotificationRecipient)
                .options(
                    selectinload(NotificationRecipient.notification).selectinload(
                        Notification.notification_type
                    )
                )
                .where(NotificationRecipient.recipient_id == user_id)
                .order_by(desc(NotificationRecipient.created_at))
                .limit(limit)
                .offset(offset)
            )

            # Apply filters
            if status_filter:
                query = query.where(NotificationRecipient.status == status_filter)

            if unread_only:
                query = query.where(NotificationRecipient.read_at == None)

            # Execute query
            result = self.db.execute(query)
            notification_recipients = result.scalars().all()

            # Format notifications with content
            formatted_notifications = []
            for recipient in notification_recipients:
                notification = recipient.notification

                try:
                    # Get formatted message content using our notification service
                    message = await self._get_notification_content(
                        notification.notification_type.code,
                        notification.entity_id,  # type: ignore
                        channel_type="in_app",  # Use lowercase to match ChannelType enum
                        notification_id=notification.id,  # type: ignore
                    )

                    formatted_notification = await self._construct_notification_item(
                        recipient, notification, message
                    )
                    formatted_notifications.append(
                        formatted_notification.model_dump(by_alias=True)
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to format notification {notification.id} for user {user_id}: {str(e)}"
                    )
                    # Add basic notification without formatted content
                    formatted_notification = await self._construct_notification_item(
                        recipient, notification, error_msg="Content unavailable"
                    )
                    formatted_notifications.append(
                        formatted_notification.model_dump(by_alias=True)
                    )

            logger.info(
                f"Retrieved {len(formatted_notifications)} notifications for user {user_id}"
            )
            return formatted_notifications

        except Exception as e:
            logger.error(
                f"Failed to get notifications for user {user_id}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError("USER_NOTIFICATIONS_RETRIEVAL_FAILED")

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread delivered notifications for a user"""
        try:
            from sqlalchemy import func

            result = self.db.execute(
                select(func.count(NotificationRecipient.id)).where(
                    and_(
                        NotificationRecipient.recipient_id == user_id,
                        NotificationRecipient.status == NotificationStatus.DELIVERED,
                        NotificationRecipient.read_at == None,
                        NotificationRecipient.in_app_enabled == True,
                    )
                )
            )
            return result.scalar() or 0

        except Exception as e:
            logger.error(
                f"Failed to get unread count for user {user_id}: {str(e)}",
                exc_info=True,
            )
            return 0

    async def mark_notification_as_read(
        self, user_id: str, notification_recipient_id: str
    ) -> bool:
        """Mark a specific notification as read for a user"""
        try:
            # Find the notification recipient
            result = self.db.execute(
                select(NotificationRecipient).where(
                    and_(
                        NotificationRecipient.id == notification_recipient_id,
                        NotificationRecipient.recipient_id == user_id,
                    )
                )
            )
            recipient = result.scalar_one_or_none()

            if not recipient:
                logger.warning(
                    f"Notification recipient {notification_recipient_id} not found for user {user_id}"
                )
                return False

            # Mark as read if not already read
            if recipient.read_at is None:
                recipient.read_at = naive_utc_now()
                recipient.status = NotificationStatus.READ
                self.db.commit()

                logger.info(
                    f"Marked notification {notification_recipient_id} as read for user {user_id}"
                )
                return True

            return True  # Already read

        except Exception as e:
            logger.error(
                f"Failed to mark notification as read: {str(e)}", exc_info=True
            )
            return False

    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all unread notifications as read for a user"""
        try:
            from sqlalchemy import update

            # Update all unread notifications for the user
            result = self.db.execute(
                update(NotificationRecipient)
                .where(
                    and_(
                        NotificationRecipient.recipient_id == user_id,
                        NotificationRecipient.read_at == None,
                    )
                )
                .values(read_at=naive_utc_now(), status=NotificationStatus.READ)
                .execution_options(synchronize_session=False)
            )

            self.db.commit()
            updated_count = result.rowcount

            logger.info(
                f"Marked {updated_count} notifications as read for user {user_id}"
            )
            return updated_count

        except Exception as e:
            logger.error(
                f"Failed to mark all notifications as read for user {user_id}: {str(e)}",
                exc_info=True,
            )
            return 0

    async def get_unread_notifications(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get only delivered but unread notifications for a user"""
        return await self.get_user_notifications(
            user_id=user_id,
            status_filter=NotificationStatus.DELIVERED,
            limit=limit,
            offset=offset,
            unread_only=True,
        )

    async def clear_all_notifications(self, user_id: str) -> int:
        """Clear all notifications by marking them as expired (they won't show up in client)"""
        try:
            from sqlalchemy import update

            # Update all non-expired notifications for the user to expired status
            result = self.db.execute(
                update(NotificationRecipient)
                .where(
                    and_(
                        NotificationRecipient.recipient_id == user_id,
                        NotificationRecipient.status != NotificationStatus.EXPIRED,
                    )
                )
                .values(status=NotificationStatus.EXPIRED)
                .execution_options(synchronize_session=False)
            )

            self.db.commit()
            updated_count = result.rowcount

            logger.info(f"Cleared {updated_count} notifications for user {user_id}")
            return updated_count

        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Failed to clear notifications for user {user_id}: {str(e)}",
                exc_info=True,
            )
            return 0

    async def _construct_notification_item(
        self,
        recipient: NotificationRecipient,
        notification: Notification,
        message: Optional[Dict[str, str]] = None,
        error_msg: Optional[str] = None,
    ) -> GetUserNotificationItem:
        """Construct a GetUserNotificationItem from database objects"""
        notification_item = GetUserNotificationItem(
            id=str(recipient.id),
            notification_id=str(notification.id),
            notification_code=notification.notification_type.code,
            notification_name=notification.notification_type.name,
            entity_id=str(notification.entity_id),
            entity_type=notification.notification_type.entity_type,
            subject=(
                message.get("subject", "Notification")
                if message
                else f"Notification - {notification.notification_type.name}"
            ),
            body=(
                message.get("body", "You have a new notification")
                if message
                else (
                    "Unable to load notification content"
                    if error_msg
                    else "You have a new notification"
                )
            ),
            priority=notification.priority.value,
            status=recipient.status.value,
            in_app_enabled=recipient.in_app_enabled,
            line_app_enabled=recipient.line_app_enabled,
            created_at=recipient.created_at.isoformat(),
            delivered_at=(
                recipient.delivered_at.isoformat() if recipient.delivered_at else None
            ),
            read_at=(recipient.read_at.isoformat() if recipient.read_at else None),
            is_read=recipient.read_at is not None,
            actor_type=notification.actor_type.value,
            scheduled_for=(
                notification.scheduled_for.isoformat()
                if notification.scheduled_for
                else None
            ),
            expires_at=(
                notification.expires_at.isoformat() if notification.expires_at else None
            ),
            error=error_msg,
        )

        return notification_item

    async def _get_notification_content(
        self,
        notification_code: str,
        entity_id: str,
        channel_type: str,
        notification_id: str,
    ) -> Optional[Dict[str, str]]:
        """Get formatted notification content using notification service"""
        try:
            service = NotificationServiceRegistry.create_service(
                notification_code, self.db
            )
            if not service:
                logger.warning(
                    f"No service found for notification code: {notification_code}"
                )
                return None

            notification_data = await service.get_notification_data(
                entity_id, notification_id
            )
            message = await service.construct_message(channel_type, notification_data)
            return message

        except Exception as e:
            logger.warning(
                f"Failed to get notification content for {notification_code}: {e}"
            )
            return None


# Dependency injection function
def get_user_notification_service(db_session: Session) -> UserNotificationService:
    """Dependency to provide UserNotificationService instance"""
    return UserNotificationService(db_session)
