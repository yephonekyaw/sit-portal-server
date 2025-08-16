from typing import List, Optional
from datetime import datetime
import uuid

from app.utils.logging import get_logger

logger = get_logger()


def create_notification_async(
    request_id: str,
    notification_code: str,
    entity_id: uuid.UUID,
    actor_type: str,
    recipient_ids: List[uuid.UUID],
    actor_id: Optional[uuid.UUID] = None,
    scheduled_for: Optional[datetime] = None,
    expires_at: Optional[datetime] = None,
    in_app_enabled: bool = True,
    line_app_enabled: bool = False,
    **metadata
) -> str:
    """
    Create notification asynchronously via Celery task.
    
    Simple helper function to trigger notification creation without complex logic.
    
    Args:
        request_id: Request ID for tracking
        notification_code: Code identifying the notification type
        entity_id: UUID of the entity the notification is about
        actor_type: Type of actor triggering the notification
        recipient_ids: List of recipient UUIDs
        actor_id: Optional UUID of the actor
        scheduled_for: Optional datetime for scheduling
        expires_at: Optional datetime for expiration
        in_app_enabled: Whether in-app notifications are enabled
        line_app_enabled: Whether LINE notifications are enabled
        **metadata: Additional metadata for the notification
        
    Returns:
        str: Celery task ID
    """
    try:
        from app.tasks.notification_creation import create_notification_task

        task_args = {
            "request_id": request_id,
            "notification_code": notification_code,
            "entity_id": str(entity_id),
            "actor_type": actor_type,
            "recipient_ids": [str(rid) for rid in recipient_ids],
            "actor_id": str(actor_id) if actor_id else None,
            "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "in_app_enabled": in_app_enabled,
            "line_app_enabled": line_app_enabled,
            **metadata,
        }

        # Use Celery task for async processing
        result = create_notification_task.delay(**task_args)
        
        logger.info(
            "Notification creation task triggered",
            task_id=result.id,
            notification_code=notification_code,
            entity_id=str(entity_id),
            recipient_count=len(recipient_ids),
        )
        
        return result.id

    except Exception as e:
        logger.error(
            "Failed to trigger notification creation",
            notification_code=notification_code,
            entity_id=str(entity_id),
            error=str(e),
            exc_info=True,
        )
        raise