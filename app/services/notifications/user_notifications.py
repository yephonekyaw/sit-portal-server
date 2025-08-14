from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    NotificationRecipient,
    Notification,
    NotificationType,
    User,
    NotificationStatus
)
from app.utils.logging import get_logger
from .registry import NotificationServiceRegistry

logger = get_logger()


class UserNotificationService:
    """Service for retrieving and managing user notifications"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        status_filter: Optional[NotificationStatus] = None,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False
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
                    selectinload(NotificationRecipient.notification)
                    .selectinload(Notification.notification_type)
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
                query = query.where(NotificationRecipient.read_at.is_(None))
            
            # Execute query
            result = await self.db.execute(query)
            notification_recipients = result.scalars().all()
            
            # Format notifications with content
            formatted_notifications = []
            for recipient in notification_recipients:
                notification = recipient.notification
                
                try:
                    # Get formatted message content using our notification service
                    message = await self._get_notification_content(
                        notification.notification_type.code,
                        notification.entity_id,
                        channel_type="in_app"  # Use lowercase to match ChannelType enum
                    )
                    
                    formatted_notification = {
                        "id": str(recipient.id),
                        "notification_id": str(notification.id),
                        "subject": message.get("subject", "Notification") if message else "Notification",
                        "body": message.get("body", "You have a new notification") if message else "You have a new notification",
                        "notification_type": {
                            "code": notification.notification_type.code,
                            "name": notification.notification_type.name,
                            "entity_type": notification.notification_type.entity_type
                        },
                        "priority": notification.priority.value,
                        "status": recipient.status.value,
                        "in_app_enabled": recipient.in_app_enabled,
                        "line_app_enabled": recipient.line_app_enabled,
                        "created_at": recipient.created_at.isoformat(),
                        "delivered_at": recipient.delivered_at.isoformat() if recipient.delivered_at else None,
                        "read_at": recipient.read_at.isoformat() if recipient.read_at else None,
                        "is_read": recipient.read_at is not None,
                        "entity_id": str(notification.entity_id),
                        "actor_type": notification.actor_type.value,
                        "scheduled_for": notification.scheduled_for.isoformat() if notification.scheduled_for else None,
                        "expires_at": notification.expires_at.isoformat() if notification.expires_at else None
                    }
                    
                    formatted_notifications.append(formatted_notification)
                    
                except Exception as e:
                    logger.warning(
                        f"Failed to format notification {notification.id} for user {user_id}: {str(e)}"
                    )
                    # Add basic notification without formatted content
                    formatted_notifications.append({
                        "id": str(recipient.id),
                        "notification_id": str(notification.id),
                        "subject": f"Notification - {notification.notification_type.name}",
                        "body": "Unable to load notification content",
                        "notification_type": {
                            "code": notification.notification_type.code,
                            "name": notification.notification_type.name,
                            "entity_type": notification.notification_type.entity_type
                        },
                        "priority": notification.priority.value,
                        "status": recipient.status.value,
                        "created_at": recipient.created_at.isoformat(),
                        "is_read": recipient.read_at is not None,
                        "error": "Content unavailable"
                    })
            
            logger.info(f"Retrieved {len(formatted_notifications)} notifications for user {user_id}")
            return formatted_notifications
            
        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {str(e)}", exc_info=True)
            raise RuntimeError("USER_NOTIFICATIONS_RETRIEVAL_FAILED")
    
    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get count of unread notifications for a user"""
        try:
            from sqlalchemy import func
            
            result = await self.db.execute(
                select(func.count(NotificationRecipient.id))
                .where(
                    and_(
                        NotificationRecipient.recipient_id == user_id,
                        NotificationRecipient.read_at.is_(None),
                        NotificationRecipient.in_app_enabled.is_(True)
                    )
                )
            )
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Failed to get unread count for user {user_id}: {str(e)}", exc_info=True)
            return 0
    
    async def mark_notification_as_read(
        self, 
        user_id: uuid.UUID, 
        notification_recipient_id: uuid.UUID
    ) -> bool:
        """Mark a specific notification as read for a user"""
        try:
            # Find the notification recipient
            result = await self.db.execute(
                select(NotificationRecipient)
                .where(
                    and_(
                        NotificationRecipient.id == notification_recipient_id,
                        NotificationRecipient.recipient_id == user_id
                    )
                )
            )
            recipient = result.scalar_one_or_none()
            
            if not recipient:
                logger.warning(f"Notification recipient {notification_recipient_id} not found for user {user_id}")
                return False
            
            # Mark as read if not already read
            if recipient.read_at is None:
                recipient.read_at = datetime.utcnow()
                recipient.status = NotificationStatus.READ
                await self.db.commit()
                
                logger.info(f"Marked notification {notification_recipient_id} as read for user {user_id}")
                return True
            
            return True  # Already read
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to mark notification as read: {str(e)}", exc_info=True)
            return False
    
    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all unread notifications as read for a user"""
        try:
            from sqlalchemy import update
            
            # Update all unread notifications for the user
            result = await self.db.execute(
                update(NotificationRecipient)
                .where(
                    and_(
                        NotificationRecipient.recipient_id == user_id,
                        NotificationRecipient.read_at.is_(None)
                    )
                )
                .values(
                    read_at=datetime.utcnow(),
                    status=NotificationStatus.READ
                )
                .execution_options(synchronize_session=False)
            )
            
            await self.db.commit()
            updated_count = result.rowcount
            
            logger.info(f"Marked {updated_count} notifications as read for user {user_id}")
            return updated_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to mark all notifications as read for user {user_id}: {str(e)}", exc_info=True)
            return 0
    
    async def _get_notification_content(
        self, 
        notification_code: str, 
        entity_id: uuid.UUID, 
        channel_type: str
    ) -> Optional[Dict[str, str]]:
        """Get formatted notification content using our notification service"""
        try:
            # Use the registry to get the appropriate service
            service = NotificationServiceRegistry.create_service_by_code(notification_code, self.db)
            
            if not service:
                logger.warning(f"No service found for notification code: {notification_code}")
                return None
            
            # Get formatted message using template-based approach
            notification_data = await service.get_notification_data(entity_id)
            message = await service.construct_message(channel_type, notification_data)
            
            return message
            
        except Exception as e:
            logger.warning(f"Failed to get notification content for {notification_code}: {str(e)}")
            return None


# Dependency injection function
def get_user_notification_service(db_session: AsyncSession) -> UserNotificationService:
    """Dependency to provide UserNotificationService instance"""
    return UserNotificationService(db_session)