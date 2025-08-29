from typing import Optional, List
from datetime import datetime, timezone
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.celery import celery
from app.db.session import get_async_session
from app.services.notifications.registry import NotificationServiceRegistry
from app.utils.logging import get_logger


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
async def create_notification_task(
    self,
    request_id: str,
    notification_code: str,
    entity_id: str,
    actor_type: str,
    recipient_ids: List[str],
    actor_id: Optional[str] = None,
    scheduled_for: Optional[str] = None,
    expires_at: Optional[str] = None,
    in_app_enabled: bool = True,
    line_app_enabled: bool = False,
    **metadata,
):
    """
    Celery task to create notifications asynchronously.

    This task is particularly useful when creating notifications for many recipients
    which could be time-consuming.

    Args:
        request_id: The request ID from the original HTTP request
        notification_code: Code identifying the notification type
        entity_id: UUID of the entity the notification is about
        actor_type: Type of actor triggering the notification
        recipient_ids: List of recipient UUIDs (as strings)
        actor_id: Optional UUID of the actor (as string)
        scheduled_for: Optional ISO datetime string for scheduling
        expires_at: Optional ISO datetime string for expiration
        in_app_enabled: Whether in-app notifications are enabled
        line_app_enabled: Whether LINE notifications are enabled
        **metadata: Additional metadata for the notification
    """
    logger = get_logger().bind(request_id=request_id)
    db_session: AsyncSession | None = None

    try:

        # Get async database session using context manager
        async for db_session in get_async_session():
            break

        if not db_session:
            logger.error("Failed to get database session")
            return {
                "success": False,
                "error": "Failed to get database session",
                "request_id": request_id,
            }

        # Convert string UUIDs back to UUID objects
        entity_uuid = uuid.UUID(entity_id)
        recipient_uuids = [uuid.UUID(rid) for rid in recipient_ids]
        actor_uuid = uuid.UUID(actor_id) if actor_id else None

        # Parse datetime strings if provided
        scheduled_for_dt = (
            datetime.fromisoformat(scheduled_for.replace("Z", "+00:00"))
            if scheduled_for
            else None
        )
        expires_at_dt = (
            datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at
            else None
        )

        # Create the notification using NotificationServiceRegistry directly
        service = NotificationServiceRegistry.create_service(
            notification_code, db_session
        )

        if not service:
            logger.error(f"No service found for notification code: {notification_code}")
            return {
                "success": False,
                "error": f"No service found for notification code: {notification_code}",
                "request_id": request_id,
            }

        notification_id = await service.create(
            entity_id=entity_uuid,
            actor_type=actor_type,
            recipient_ids=recipient_uuids,
            actor_id=actor_uuid,
            scheduled_for=scheduled_for_dt,
            expires_at=expires_at_dt,
            in_app_enabled=in_app_enabled,
            line_app_enabled=line_app_enabled,
            **metadata,
        )

        if notification_id:

            # If notification is scheduled for future, don't process immediately
            if scheduled_for_dt and scheduled_for_dt > datetime.now():
                pass
            else:
                # Trigger immediate processing for non-scheduled notifications
                from app.tasks.notification_processing import process_notification_task

                process_notification_task.delay(
                    request_id=request_id,
                    notification_id=str(notification_id),
                )

            return {
                "success": True,
                "notification_id": str(notification_id),
                "recipient_count": len(recipient_ids),
                "request_id": request_id,
            }
        else:
            logger.error(
                f"Failed to create notification {notification_code} for entity {entity_id}"
            )
            return {
                "success": False,
                "error": "Failed to create notification",
                "request_id": request_id,
            }

    except Exception as e:
        logger.error(
            f"Notification creation task exception {notification_code}/{entity_id}: {str(e)}"
        )

        if db_session:
            await db_session.rollback()

        # Retry with exponential backoff for transient errors
        if self.request.retries < self.max_retries:
            # Cap retry delay at 5 minutes
            retry_delay = min(2**self.request.retries * 60, 300)
            raise self.retry(countdown=retry_delay)

        return {
            "success": False,
            "error": str(e),
            "notification_code": notification_code,
            "entity_id": entity_id,
            "request_id": request_id,
        }
    finally:
        if db_session:
            await db_session.close()
