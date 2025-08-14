"""
Simplified notification service package

Usage:
    from app.services.notifications import create_notification, get_notification_message
    
    # Create a notification
    notification_id = await create_notification(
        notification_code="certificate_submission_submit",
        entity_id=submission_id,
        actor_type="user",
        recipient_ids=[user_id],
        db_session=db
    )
    
    # Get formatted message
    message = await get_notification_message(
        notification_code="certificate_submission_submit",
        entity_id=submission_id,
        channel_type="in_app",
        db_session=db
    )
"""

from .utils import (
    create_notification,
    get_notification_message, 
    get_user_notifications_summary
)
from .user_notifications import UserNotificationService
from .registry import NotificationServiceRegistry
from .base import BaseNotificationService
from .deadline_utils import DeadlineCalculator

__all__ = [
    "create_notification",
    "get_notification_message", 
    "get_user_notifications_summary",
    "UserNotificationService",
    "NotificationServiceRegistry",
    "BaseNotificationService",
    "DeadlineCalculator"
]