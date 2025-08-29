from datetime import datetime, timezone
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.celery import celery
from app.db.session import get_async_session
from app.db.models import Notification, NotificationStatus
from app.utils.logging import get_logger


@celery.task(bind=True, max_retries=3, default_retry_delay=30)
async def process_notification_task(self, request_id: str, notification_id: str):
    """
    Celery task to process a notification and dispatch to channel-specific sending tasks.

    This task retrieves the notification, formats the content, and creates channel-specific
    sending tasks for each enabled recipient.

    Args:
        request_id: The request ID from the original HTTP request
        notification_id: UUID of the notification to process (as string)
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

        # Get notification with all recipients
        result = await db_session.execute(
            select(Notification)
            .options(
                selectinload(Notification.recipients),
                selectinload(Notification.notification_type),
            )
            .where(Notification.id == uuid.UUID(notification_id))
        )
        notification = result.scalar_one_or_none()

        if not notification:
            logger.error(f"Notification not found: {notification_id}")
            return {
                "success": False,
                "error": "Notification not found",
                "notification_id": notification_id,
                "request_id": request_id,
            }

        # Check if notification has expired
        if notification.expires_at and notification.expires_at <= datetime.now(
            timezone.utc
        ):

            # Mark all pending recipients as expired
            for recipient in notification.recipients:
                if recipient.status == NotificationStatus.PENDING:
                    recipient.status = NotificationStatus.EXPIRED

            await db_session.commit()
            return {
                "success": True,
                "status": "expired",
                "notification_id": notification_id,
                "request_id": request_id,
            }

        # Process each recipient
        tasks_created = 0
        for recipient in notification.recipients:
            if recipient.status != NotificationStatus.PENDING:
                continue

            # Create channel-specific sending tasks
            if recipient.in_app_enabled:
                # For now, in-app notifications are immediately marked as delivered
                # since they're just stored in the database
                recipient.status = NotificationStatus.DELIVERED
                recipient.delivered_at = datetime.now()
                tasks_created += 1

            if recipient.line_app_enabled:
                # Create LINE sending task
                from app.tasks.line_notification_sender import (
                    send_line_notification_task,
                )

                send_line_notification_task.delay(
                    request_id=request_id,
                    notification_id=notification_id,
                    recipient_id=str(recipient.recipient_id),
                )
                tasks_created += 1

        await db_session.commit()

        return {
            "success": True,
            "tasks_created": tasks_created,
            "notification_id": notification_id,
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(
            f"Notification processing task exception for {notification_id}: {str(e)}"
        )

        if db_session:
            await db_session.rollback()

        # Retry with exponential backoff for transient errors
        if self.request.retries < self.max_retries:
            # Cap retry delay at 5 minutes
            retry_delay = min(2**self.request.retries * 30, 300)
            raise self.retry(countdown=retry_delay)

        return {
            "success": False,
            "error": str(e),
            "notification_id": notification_id,
            "request_id": request_id,
        }
    finally:
        if db_session:
            await db_session.close()
