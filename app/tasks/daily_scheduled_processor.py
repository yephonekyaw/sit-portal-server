from datetime import datetime, timezone
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.celery import celery
from app.db.session import get_async_session
from app.db.models import Notification, NotificationRecipient, NotificationStatus
from app.utils.logging import get_logger
from app.utils.errors import DatabaseError


@celery.task(bind=True, max_retries=3, default_retry_delay=30)
async def daily_scheduled_notifications_processor_task(self, request_id: str):
    """
    Daily task to scan the database and process notifications scheduled for the current day.
    Runs at 9:00 AM daily to find notifications with scheduled_for on the current date,
    then triggers the existing notification processing tasks.

    Args:
        request_id: The request ID for tracking purposes (provided by Celery Beat configuration)
    """
    logger = get_logger().bind(request_id=request_id)
    db_session: AsyncSession | None = None

    try:

        # Get async database session
        async for db_session in get_async_session():
            break

        if not db_session:
            raise DatabaseError("Failed to get database session")

        # Get current date in UTC
        current_date = datetime.now(timezone.utc).date()

        # Query notifications scheduled for today that have pending recipients
        result = await db_session.execute(
            select(Notification)
            .options(selectinload(Notification.recipients))
            .join(NotificationRecipient)
            .where(
                and_(
                    # Scheduled for today
                    Notification.scheduled_for
                    >= datetime.combine(current_date, datetime.min.time()).replace(
                        tzinfo=timezone.utc
                    ),
                    Notification.scheduled_for
                    < datetime.combine(current_date, datetime.max.time()).replace(
                        tzinfo=timezone.utc
                    ),
                    # Has pending recipients
                    NotificationRecipient.status == NotificationStatus.PENDING,
                    # Not expired
                    (
                        Notification.expires_at.is_(None)
                        | (Notification.expires_at > datetime.now(timezone.utc))
                    ),
                )
            )
            .distinct()
        )

        scheduled_notifications = result.scalars().all()

        if not scheduled_notifications:
            return {
                "success": True,
                "processed_count": 0,
                "current_date": current_date.isoformat(),
                "request_id": request_id,
            }

        # Process each scheduled notification
        processed_count = 0
        for notification in scheduled_notifications:
            try:
                # Import here to avoid circular imports
                from app.tasks.notification_processing import process_notification_task

                # Trigger the existing notification processing task
                process_notification_task.delay(
                    request_id=request_id, notification_id=str(notification.id)
                )

                processed_count += 1

            except Exception as e:
                logger.error(
                    "Failed to trigger processing for scheduled notification",
                    notification_id=str(notification.id),
                    error=str(e),
                    request_id=request_id,
                )
                continue

        logger.info(
            "Daily scheduled notifications processing completed",
            processed_count=processed_count,
            total_found=len(scheduled_notifications),
            current_date=current_date.isoformat(),
            request_id=request_id,
        )

        return {
            "success": True,
            "processed_count": processed_count,
            "total_found": len(scheduled_notifications),
            "current_date": current_date.isoformat(),
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(
            "Daily scheduled notifications processor task exception",
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )

        if db_session:
            await db_session.rollback()

        # Retry with exponential backoff for transient errors
        if self.request.retries < self.max_retries:
            retry_delay = min(2**self.request.retries * 30, 300)  # Cap at 5 minutes
            raise self.retry(countdown=retry_delay)

        return {
            "success": False,
            "error": str(e),
            "request_id": request_id,
        }
    finally:
        if db_session:
            await db_session.close()
