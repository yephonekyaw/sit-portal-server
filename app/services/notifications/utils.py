from typing import Dict, Any, Optional, List
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from .registry import NotificationServiceRegistry
from app.utils.logging import get_logger

logger = get_logger()


async def get_notification_message(
    notification_id: uuid.UUID,
    notification_code: str,
    entity_id: uuid.UUID,
    db_session: AsyncSession,
    channel_type: str = "in_app",
) -> Optional[Dict[str, str]]:
    """Get formatted notification message"""
    try:
        service = NotificationServiceRegistry.create_service(
            notification_code, db_session
        )
        if not service:
            return None

        notification_data = await service.get_notification_data(
            entity_id, notification_id
        )
        message = await service.construct_message(channel_type, notification_data)

        logger.info(f"Generated message for {notification_code}, entity {entity_id}")
        return message

    except Exception as e:
        logger.error(f"Failed to get notification message: {e}")
        return None


async def create_notification(
    notification_code: str,
    entity_id: uuid.UUID,
    actor_type: str,
    recipient_ids: List[uuid.UUID],
    db_session: AsyncSession,
    actor_id: Optional[uuid.UUID] = None,
    **kwargs,
) -> Optional[uuid.UUID]:
    """Create notification - simplified one-line function"""
    try:
        service = NotificationServiceRegistry.create_service(
            notification_code, db_session
        )
        if not service:
            logger.warning(
                f"No service found for notification code: {notification_code}"
            )
            return None

        notification_id = await service.create(
            entity_id=entity_id,
            actor_type=actor_type,
            recipient_ids=recipient_ids,
            actor_id=actor_id,
            **kwargs,
        )

        logger.info(f"Created notification {notification_id} for {notification_code}")
        return notification_id

    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return None


async def get_user_notifications_summary(
    user_id: uuid.UUID, db_session: AsyncSession, limit: int = 10
) -> Dict[str, Any]:
    """Get user notifications summary for dashboard"""
    from .user_notifications import UserNotificationService

    try:
        service = UserNotificationService(db_session)
        unread_count = await service.get_unread_count(user_id)
        recent_notifications = await service.get_user_notifications(
            user_id=user_id, limit=limit, unread_only=False
        )

        return {
            "unread_count": unread_count,
            "recent_notifications": recent_notifications[:limit],
            "has_more": len(recent_notifications) == limit,
        }

    except Exception as e:
        logger.error(f"Failed to get user notifications summary: {e}")
        return {
            "unread_count": 0,
            "recent_notifications": [],
            "has_more": False,
            "error": "Failed to load notifications",
        }
