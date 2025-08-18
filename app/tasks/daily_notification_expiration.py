from datetime import datetime, timezone
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.celery import celery
from app.db.session import get_async_session
from app.db.models import Notification, NotificationStatus
from app.utils.logging import get_logger
from app.utils.errors import DatabaseError


@celery.task(bind=True, max_retries=3, default_retry_delay=30)
async def daily_notification_expiration_task(self, request_id: str):
    """
    Daily task to scan the database and mark notifications as expired that expire on the current day.
    Runs at 00:05 AM daily to find notifications with expires_at on the current date,
    then marks all pending recipients as expired by updating the database directly.

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
        current_datetime = datetime.now(timezone.utc)
        
        # Query notifications that expire today and have pending recipients
        notifications_result = await db_session.execute(
            select(Notification)
            .options(selectinload(Notification.recipients))
            .where(
                and_(
                    # Expires today or earlier
                    Notification.expires_at.is_not(None),
                    Notification.expires_at <= current_datetime
                )
            )
        )

        expiring_notifications = notifications_result.scalars().all()

        if not expiring_notifications:
            return {
                "success": True,
                "expired_notifications": 0,
                "expired_recipients": 0,
                "current_date": current_date.isoformat(),
                "request_id": request_id,
            }

        # Mark pending recipients as expired for each expiring notification
        total_expired_notifications = 0
        total_expired_recipients = 0
        
        for notification in expiring_notifications:
            expired_recipients_count = 0
            
            # Update pending recipients to expired status
            for recipient in notification.recipients:
                if recipient.status == NotificationStatus.PENDING:
                    recipient.status = NotificationStatus.EXPIRED
                    expired_recipients_count += 1

            if expired_recipients_count > 0:
                total_expired_notifications += 1
                total_expired_recipients += expired_recipients_count
                

        # Commit all changes
        await db_session.commit()

        logger.info(
            "Daily notification expiration task completed",
            expired_notifications=total_expired_notifications,
            expired_recipients=total_expired_recipients,
            total_checked=len(expiring_notifications),
            current_date=current_date.isoformat(),
            request_id=request_id,
        )

        return {
            "success": True,
            "expired_notifications": total_expired_notifications,
            "expired_recipients": total_expired_recipients,
            "total_checked": len(expiring_notifications),
            "current_date": current_date.isoformat(),
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(
            "Daily notification expiration task exception",
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