from typing import Dict, Any, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from .registry import NotificationServiceRegistry
from app.utils.logging import get_logger

logger = get_logger()


async def get_notification_message(
    notification_type_id: uuid.UUID,
    entity_id: uuid.UUID,
    channel_type: str,
    db_session: AsyncSession
) -> Optional[Dict[str, str]]:
    """
    Utility function to get formatted notification message for GET requests
    
    This solves the problem of handling multiple notification service classes
    by using the registry pattern to dynamically select and use the right service
    """
    try:
        # Get the appropriate service from registry
        service = NotificationServiceRegistry.create_service(notification_type_id, db_session)
        
        if not service:
            logger.warning(f"No service found for notification type {notification_type_id}")
            return None
        
        # Get the notification data using entity_id
        notification_data = await service.get_notification_data(entity_id)
        
        # Construct and return the message using template-based approach
        message = await service.construct_message(channel_type, notification_data)
        
        logger.info(f"Generated message for notification type {notification_type_id}, entity {entity_id}")
        return message
        
    except Exception as e:
        logger.error(
            f"Failed to get notification message for type {notification_type_id}, "
            f"entity {entity_id}: {str(e)}", 
            exc_info=True
        )
        return None


async def get_notification_message_by_code(
    notification_code: str,
    entity_id: uuid.UUID,
    channel_type: str,
    db_session: AsyncSession
) -> Optional[Dict[str, str]]:
    """
    Utility function to get formatted notification message using notification code
    """
    try:
        # Get the appropriate service from registry using code
        service = NotificationServiceRegistry.create_service_by_code(notification_code, db_session)
        
        if not service:
            logger.warning(f"No service found for notification code {notification_code}")
            return None
        
        # Get the notification data using entity_id
        notification_data = await service.get_notification_data(entity_id)
        
        # Construct and return the message using template-based approach
        message = await service.construct_message(channel_type, notification_data)
        
        logger.info(f"Generated message for notification code {notification_code}, entity {entity_id}")
        return message
        
    except Exception as e:
        logger.error(
            f"Failed to get notification message for code {notification_code}, "
            f"entity {entity_id}: {str(e)}", 
            exc_info=True
        )
        return None


async def create_notification_simple(
    notification_type_id: uuid.UUID,
    entity_id: uuid.UUID,
    actor_type: str,
    recipient_ids: list,
    db_session: AsyncSession,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Simplified one-line notification creation function for client layer
    
    This is the 'one line of code' function you wanted for the client layer
    """
    try:
        service = NotificationServiceRegistry.create_service(notification_type_id, db_session)
        
        if not service:
            logger.warning(f"No service found for notification type {notification_type_id}")
            return None
        
        result = await service.create(
            entity_id=entity_id,
            actor_type=actor_type,
            recipient_ids=recipient_ids,
            **kwargs
        )
        
        logger.info(f"Created notification using {service.__class__.__name__}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to create notification: {str(e)}", exc_info=True)
        return None


async def create_notification_simple_by_code(
    notification_code: str,
    entity_id: uuid.UUID,
    actor_type: str,
    recipient_ids: list,
    db_session: AsyncSession,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Simplified notification creation function using notification code
    """
    try:
        service = NotificationServiceRegistry.create_service_by_code(notification_code, db_session)
        
        if not service:
            logger.warning(f"No service found for notification code {notification_code}")
            return None
        
        result = await service.create(
            entity_id=entity_id,
            actor_type=actor_type,
            recipient_ids=recipient_ids,
            **kwargs
        )
        
        logger.info(f"Created notification using {service.__class__.__name__}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to create notification: {str(e)}", exc_info=True)
        return None


async def get_user_notifications_summary(
    user_id: uuid.UUID,
    db_session: AsyncSession,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Quick utility to get user notifications summary for dashboard/header
    """
    from .user_notifications import UserNotificationService
    
    try:
        service = UserNotificationService(db_session)
        
        # Get unread count and recent notifications
        unread_count = await service.get_unread_count(user_id)
        recent_notifications = await service.get_user_notifications(
            user_id=user_id,
            limit=limit,
            unread_only=False
        )
        
        return {
            "unread_count": unread_count,
            "recent_notifications": recent_notifications[:limit],
            "has_more": len(recent_notifications) == limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get user notifications summary: {str(e)}", exc_info=True)
        return {
            "unread_count": 0,
            "recent_notifications": [],
            "has_more": False,
            "error": "Failed to load notifications"
        }