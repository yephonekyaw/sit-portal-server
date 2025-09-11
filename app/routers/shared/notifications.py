import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db.session import get_sync_session
from app.services.notifications.user_notification_service import UserNotificationService
from app.middlewares.auth_middleware import get_current_user, AuthState
from app.utils.responses import ResponseBuilder
from app.utils.errors import NotFoundError
from app.utils.logging import get_logger

notifications_router = APIRouter()
logger = get_logger()


@notifications_router.get("/unread")
async def get_unread_notifications(
    request: Request,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_sync_session)],
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of notifications to return",
    ),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
):
    """
    Get all unread notifications for the current user.

    Returns only delivered notifications that have not been read yet.
    Excludes failed, expired, pending, and already read notifications.
    """
    try:
        # Convert user_id from string to UUID
        try:
            user_uuid = uuid.UUID(current_user.user_id)
        except ValueError:
            raise ValidationError(
                [
                    {
                        "type": "value_error",
                        "msg": "Invalid user ID format",
                        "input": current_user.user_id,
                    }
                ]
            )

        service = UserNotificationService(db)
        notifications = await service.get_unread_notifications(
            user_id=user_uuid, limit=limit, offset=offset
        )

        # Get total unread count for pagination info
        unread_count = await service.get_unread_count(user_uuid)

        dumped_data = {
            "notifications": notifications,
            "unreadCount": unread_count,
            "limit": limit,
            "offset": offset,
            "hasMore": len(notifications) == limit,
        }

        return ResponseBuilder.success(
            request=request,
            data=dumped_data,
            message=f"Retrieved {len(notifications)} unread notifications",
        )

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.error(
            f"Failed to get unread notifications for user {current_user.user_id}: {str(e)}",
            exc_info=True,
        )
        raise ValidationError(
            [{"type": "internal_error", "msg": "Failed to retrieve notifications"}]
        )


@notifications_router.patch("/{notification_id}/read")
async def mark_notification_as_read(
    request: Request,
    notification_id: str,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_sync_session)],
):
    """
    Mark a specific notification as read.

    Args:
        notification_id: UUID of the notification recipient record to mark as read
    """
    try:
        # Validate UUID formats
        try:
            notification_uuid = uuid.UUID(notification_id)
        except ValueError:
            raise ValidationError(
                [
                    {
                        "type": "value_error",
                        "msg": "Invalid notification ID format",
                        "input": notification_id,
                    }
                ]
            )

        try:
            user_uuid = uuid.UUID(current_user.user_id)
        except ValueError:
            raise ValidationError(
                [
                    {
                        "type": "value_error",
                        "msg": "Invalid user ID format",
                        "input": current_user.user_id,
                    }
                ]
            )

        service = UserNotificationService(db)
        success = await service.mark_notification_as_read(
            user_id=user_uuid, notification_recipient_id=notification_uuid
        )

        if not success:
            raise NotFoundError("Notification not found or already read")

        # Get updated unread count
        unread_count = await service.get_unread_count(user_uuid)

        return ResponseBuilder.success(
            request=request,
            data={"unreadCount": unread_count},
            message="Notification marked as read",
        )

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.error(
            f"Failed to mark notification {notification_id} as read for user {current_user.user_id}: {str(e)}",
            exc_info=True,
        )
        raise ValidationError(
            [{"type": "internal_error", "msg": "Failed to mark notification as read"}]
        )


@notifications_router.patch("/read-all")
async def mark_all_notifications_as_read(
    request: Request,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_sync_session)],
):
    """
    Mark all unread notifications as read for the current user.

    This is a bulk operation that marks all unread notifications as read.
    """
    try:
        # Convert user_id from string to UUID
        try:
            user_uuid = uuid.UUID(current_user.user_id)
        except ValueError:
            raise ValidationError(
                [
                    {
                        "type": "value_error",
                        "msg": "Invalid user ID format",
                        "input": current_user.user_id,
                    }
                ]
            )

        service = UserNotificationService(db)
        updated_count = await service.mark_all_as_read(user_uuid)

        return ResponseBuilder.success(
            request=request,
            data={"allAsReadCount": updated_count},
            message=f"Marked {updated_count} notifications as read",
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            f"Failed to mark all notifications as read for user {current_user.user_id}: {str(e)}",
            exc_info=True,
        )
        raise ValidationError(
            [
                {
                    "type": "internal_error",
                    "msg": "Failed to mark all notifications as read",
                }
            ]
        )


@notifications_router.delete("/clear-all")
async def clear_all_notifications(
    request: Request,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_sync_session)],
):
    """
    Clear all notifications for the current user.

    This marks all notifications as expired, which means they will no longer
    appear in the client. The notifications are not deleted from the database
    for audit purposes.
    """
    try:
        # Convert user_id from string to UUID
        try:
            user_uuid = uuid.UUID(current_user.user_id)
        except ValueError:
            raise ValidationError(
                [
                    {
                        "type": "value_error",
                        "msg": "Invalid user ID format",
                        "input": current_user.user_id,
                    }
                ]
            )

        service = UserNotificationService(db)
        cleared_count = await service.clear_all_notifications(user_uuid)

        return ResponseBuilder.success(
            request=request,
            data={"clearedCount": cleared_count},
            message=f"Cleared {cleared_count} notifications",
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            f"Failed to clear notifications for user {current_user.user_id}: {str(e)}",
            exc_info=True,
        )
        raise ValidationError(
            [{"type": "internal_error", "msg": "Failed to clear notifications"}]
        )


@notifications_router.get("/count")
async def get_unread_count(
    request: Request,
    current_user: Annotated[AuthState, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_sync_session)],
):
    """
    Get the count of unread notifications for the current user.

    This is useful for displaying notification badges in the UI.
    """
    try:
        # Convert user_id from string to UUID
        try:
            user_uuid = uuid.UUID(current_user.user_id)
        except ValueError:
            raise ValidationError(
                [
                    {
                        "type": "value_error",
                        "msg": "Invalid user ID format",
                        "input": current_user.user_id,
                    }
                ]
            )

        service = UserNotificationService(db)
        unread_count = await service.get_unread_count(user_uuid)

        return ResponseBuilder.success(
            request=request,
            data={"unreadCount": unread_count},
            message="Unread count retrieved",
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get unread count for user {current_user.user_id}: {str(e)}",
            exc_info=True,
        )
        raise ValidationError(
            [{"type": "internal_error", "msg": "Failed to get unread count"}]
        )
