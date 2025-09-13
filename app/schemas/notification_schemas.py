from uuid import UUID
from typing import Any, Dict, List, Optional
from pydantic import Field

from app.schemas.camel_base_model import CamelCaseBaseModel as BaseModel


class GetUserNotificationItem(BaseModel):
    id: str | UUID = Field(..., description="Notification recipient ID")
    notification_id: str | UUID = Field(..., description="Notification ID")
    notification_code: str = Field(..., description="Notification code")
    notification_name: str = Field(..., description="Notification name")
    entity_id: str | UUID = Field(..., description="Related entity ID")
    entity_type: str = Field(..., description="Notification entity type")

    subject: str = Field(..., description="Notification subject")
    body: str = Field(..., description="Notification body content")
    priority: str = Field(..., description="Notification priority")
    status: str = Field(..., description="Notification status")
    in_app_enabled: bool = Field(
        ..., description="Whether in-app notification is enabled"
    )
    line_app_enabled: bool = Field(
        ..., description="Whether LINE app notification is enabled"
    )

    is_read: bool = Field(..., description="Whether notification has been read")
    actor_type: str = Field(..., description="Actor type who triggered notification")

    created_at: str = Field(..., description="Creation timestamp in ISO format")
    delivered_at: Optional[str] = Field(
        ..., description="Delivery timestamp in ISO format"
    )
    read_at: Optional[str] = Field(..., description="Read timestamp in ISO format")
    scheduled_for: Optional[str] = Field(
        ..., description="Scheduled timestamp in ISO format"
    )
    expires_at: Optional[str] = Field(
        ..., description="Expiration timestamp in ISO format"
    )
    error: Optional[str] = Field(
        ..., description="Error message if content unavailable"
    )


class GetUnreadNotificationsResponse(BaseModel):
    notifications: List[Dict[str, Any]] = Field(
        ..., description="List of unread notifications"
    )
    unread_count: int = Field(..., description="Count of unread notifications")
    limit: int = Field(..., description="Pagination limit")
    offset: int = Field(..., description="Pagination offset")
    has_more: bool = Field(..., description="Whether more notifications are available")


class NotificationStats(BaseModel):
    unread_count: Optional[int] = Field(0, description="Count of unread notifications")
    all_as_read_count: Optional[int] = Field(
        0, description="Count of notifications marked as read at the same time"
    )
    cleared_count: Optional[int] = Field(
        0, description="Count of notifications cleared at the same time"
    )
