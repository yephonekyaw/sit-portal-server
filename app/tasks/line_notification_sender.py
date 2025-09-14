import random
import uuid
import asyncio
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload, Session

from app.celery import celery
from app.db.session import get_sync_session
from app.db.models import (
    NotificationRecipient,
    NotificationStatus,
    Notification,
    Student,
    User,
)
from app.services.notifications.registry import NotificationServiceRegistry
from app.utils.logging import get_logger
from app.utils.datetime_utils import naive_utc_now


@celery.task(bind=True, max_retries=5, default_retry_delay=120)
def send_line_notification_task(
    self, request_id: str, notification_id: str, recipient_id: str
):
    """
    Celery task to send a LINE notification to a specific recipient.

    This is a mock implementation for now. In the future, this will integrate
    with the actual LINE messaging API.

    Args:
        request_id: The request ID from the original HTTP request
        notification_id: UUID of the notification (as string)
        recipient_id: UUID of the recipient (as string)
    """
    return asyncio.run(
        _async_send_line_notification(request_id, notification_id, recipient_id)
    )


async def _async_send_line_notification(
    request_id: str, notification_id: str, recipient_id: str
):
    logger = get_logger().bind(request_id=request_id)

    for db_session in get_sync_session():
        try:

            # Get notification and recipient in a single query
            notification_result = db_session.execute(
                select(Notification, NotificationRecipient)
                .join(
                    NotificationRecipient,
                    Notification.id == NotificationRecipient.notification_id,
                )
                .options(selectinload(Notification.notification_type))
                .where(
                    and_(
                        Notification.id == notification_id,
                        NotificationRecipient.recipient_id == recipient_id,
                    )
                )
            )
            result_row = notification_result.first()
            if not result_row:
                logger.error(
                    f"Notification or recipient not found: {notification_id}, {recipient_id}"
                )
                return {
                    "success": False,
                    "error": "Notification or recipient not found",
                    "request_id": request_id,
                }

            notification, recipient = result_row

            # Get formatted message content using NotificationServiceRegistry directly
            service = NotificationServiceRegistry.create_service(
                notification.notification_type.code, db_session
            )

            if not service:
                logger.error(
                    f"No service found for notification code: {notification.notification_type.code}"
                )
                recipient.status = NotificationStatus.FAILED
                db_session.commit()
                return {
                    "success": False,
                    "error": f"No service found for notification code: {notification.notification_type.code}",
                    "request_id": request_id,
                }

            try:
                notification_data = await service.get_notification_data(
                    notification.entity_id, notification_id
                )
                message = await service.construct_message("line_app", notification_data)
            except Exception as e:
                logger.error(
                    f"Failed to get notification data or construct message for {notification_id}: {str(e)}"
                )
                message = None

            if not message:
                logger.error(
                    f"Failed to get notification message content for {notification_id}"
                )
                recipient.status = NotificationStatus.FAILED
                db_session.commit()
                return {
                    "success": False,
                    "error": "Failed to get message content",
                    "request_id": request_id,
                }

            # Validate recipient can receive LINE notifications
            if not await _validate_line_recipient(db_session, recipient_id):
                logger.warning(
                    f"Recipient not configured for LINE notifications: {recipient_id}"
                )
                recipient.status = NotificationStatus.FAILED
                db_session.commit()
                return {
                    "success": False,
                    "error": "Recipient not configured for LINE notifications",
                    "request_id": request_id,
                }

            # Get recipient's LINE user ID
            line_user_id = await _get_line_user_id(db_session, recipient_id)
            if not line_user_id:
                logger.error(f"Recipient LINE user ID not found: {recipient_id}")
                recipient.status = NotificationStatus.FAILED
                db_session.commit()
                return {
                    "success": False,
                    "error": "Recipient LINE user ID not found",
                    "request_id": request_id,
                }

            # MOCK: Simulate LINE API call
            mock_line_success = await _mock_send_line_message(
                line_user_id=line_user_id,
                subject=message.get("subject", "Notification"),
                body=message.get("body", "You have a notification"),
                logger=logger,
            )

            if mock_line_success:
                # Update recipient status
                recipient.status = NotificationStatus.DELIVERED
                recipient.line_app_sent_at = naive_utc_now()
                recipient.delivered_at = naive_utc_now()
                db_session.commit()

                return {
                    "success": True,
                    "channel": "line_app",
                    "notification_id": notification_id,
                    "recipient_id": recipient_id,
                    "request_id": request_id,
                }
            else:
                # Mark as failed and retry
                recipient.status = NotificationStatus.FAILED
                db_session.commit()

                return {
                    "success": False,
                    "error": "Failed to send LINE notification after all retries",
                    "request_id": request_id,
                }

        except Exception as e:
            logger.error(
                f"LINE notification sending task exception for {notification_id}/{recipient_id}: {str(e)}"
            )

            return {
                "success": False,
                "error": str(e),
                "notification_id": notification_id,
                "recipient_id": recipient_id,
                "request_id": request_id,
            }


async def _validate_line_recipient(db_session: Session, recipient_id: str) -> bool:
    """
    Validate that recipient has LINE configured.

    Checks if the user is a student and has a line_application_id set.
    """
    try:
        result = db_session.execute(
            select(Student).join(User).where(User.id == recipient_id)
        )
        student = result.scalar_one_or_none()

        if not student:
            return False

        if not student.line_application_id:
            return False

        return True

    except Exception:
        return False


async def _get_line_user_id(db_session: Session, recipient_id: str) -> Optional[str]:
    """Get the recipient's LINE user ID"""
    try:
        result = db_session.execute(
            select(Student.line_application_id)
            .join(User)
            .where(User.id == recipient_id)
        )
        line_application_id = result.scalar_one_or_none()
        return line_application_id

    except Exception:
        return None


async def _mock_send_line_message(
    line_user_id: str, subject: str, body: str, logger
) -> bool:
    """
    Mock function to simulate sending a LINE message.

    TODO: Replace this with actual LINE messaging API integration.

    Production implementation would look like:

    import aiohttp
    from app.config.settings import settings

    async def _send_line_message(line_user_id: str, subject: str, body: str) -> bool:
        headers = {
            'Authorization': f'Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}',
            'Content-Type': 'application/json',
        }

        payload = {
            'to': line_user_id,
            'messages': [
                {
                    'type': 'text',
                    'text': f"{subject}\\n\\n{body}"
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.line.me/v2/bot/message/push',
                headers=headers,
                json=payload
            ) as response:
                return response.status == 200

    Returns:
        bool: True if successful, False if failed
    """

    # Simulate network delay (removed for performance)
    # await asyncio.sleep(1)

    # Simulate 95% success rate
    success = random.random() > 0.05

    if not success:
        logger.warning(f"MOCK: LINE message failed to send to {line_user_id}")

    return success
