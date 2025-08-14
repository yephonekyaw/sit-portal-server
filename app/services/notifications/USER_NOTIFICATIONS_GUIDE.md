# User Notifications Guide

## ✅ Yes, the Architecture Works for User Notifications!

The current notification architecture has been **extended** to fully support getting all notifications for a specific user when they log into the application.

## How It Works

### Database Relationship Flow:
```
User ──→ NotificationRecipient ──→ Notification ──→ NotificationType
                                       ↓
                                   entity_id ──→ CertificateSubmission/ProgramRequirementSchedule
```

### Architecture Components:

1. **UserNotificationService**: Main service for user notification operations
2. **NotificationRecipient**: Database table linking users to notifications
3. **Dynamic Content Generation**: Uses existing notification services to format content
4. **Status Management**: Handles read/unread status tracking

## Usage Examples

### 1. Get All User Notifications (Dashboard)

```python
from app.services.notifications import UserNotificationService

# Get user's notifications with formatted content
service = UserNotificationService(db_session)
notifications = await service.get_user_notifications(
    user_id=user_uuid,
    limit=20,
    offset=0,
    unread_only=False  # Set to True for unread only
)

# Returns formatted notifications with subject/body content
for notification in notifications:
    print(f"Subject: {notification['subject']}")
    print(f"Body: {notification['body']}")
    print(f"Read: {notification['is_read']}")
    print(f"Priority: {notification['priority']}")
    print(f"Created: {notification['created_at']}")
```

### 2. Quick Dashboard Summary

```python
from app.services.notifications import get_user_notifications_summary

# One-line function for dashboard/header
summary = await get_user_notifications_summary(
    user_id=user_uuid,
    db_session=db,
    limit=5
)

# Returns:
# {
#   "unread_count": 3,
#   "recent_notifications": [...],
#   "has_more": true
# }
```

### 3. Mark Notifications as Read

```python
# Mark specific notification as read
success = await service.mark_notification_as_read(
    user_id=user_uuid,
    notification_recipient_id=notification_id
)

# Mark all as read
updated_count = await service.mark_all_as_read(user_id=user_uuid)
```

### 4. Get Unread Count (for badges)

```python
unread_count = await service.get_unread_count(user_id=user_uuid)
```

## Complete Notification Response Format

Each notification includes:

```json
{
  "id": "notification_recipient_uuid",
  "notification_id": "notification_uuid", 
  "subject": "Certificate Verified: AWS Cloud Practitioner",
  "body": "AWS Cloud Practitioner for John Doe 12345678 approved by System.",
  "notification_type": {
    "code": "certificate_submission_verify",
    "name": "Certificate Verified",
    "entity_type": "CertificateSubmission"
  },
  "priority": "medium",
  "status": "delivered",
  "in_app_enabled": true,
  "line_app_enabled": false,
  "created_at": "2024-01-15T10:30:00Z",
  "delivered_at": "2024-01-15T10:30:01Z",
  "read_at": null,
  "is_read": false,
  "entity_id": "certificate_submission_uuid",
  "actor_type": "system",
  "scheduled_for": null,
  "expires_at": null
}
```

## Integration with Existing Services

The user notification system **leverages your existing notification services**:

- ✅ Uses `NotificationServiceRegistry` to find the right service
- ✅ Calls `get_notification_data()` to fetch entity data  
- ✅ Calls `construct_message()` to format subject/body
- ✅ Handles errors gracefully with fallback content

## Database Queries Optimized

The service uses optimized queries:

- **Single Query**: Gets notifications with all related data via `selectinload`
- **Indexed Lookups**: Uses database indexes on `recipient_id`, `status`, `created_at`
- **Pagination**: Built-in limit/offset support
- **Filtering**: Status filters, unread-only mode

## Router Integration Example

```python
from fastapi import APIRouter, Depends
from app.services.notifications import get_user_notification_service, get_user_notifications_summary

router = APIRouter()

@router.get("/notifications")
async def get_user_notifications(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    unread_only: bool = False,
    service: UserNotificationService = Depends(get_user_notification_service)
):
    notifications = await service.get_user_notifications(
        user_id=UUID(user_id),
        limit=limit,
        offset=offset,
        unread_only=unread_only
    )
    return {"notifications": notifications}

@router.get("/notifications/summary")
async def get_notifications_summary(
    user_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    summary = await get_user_notifications_summary(
        user_id=UUID(user_id),
        db_session=db
    )
    return summary

@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user_id: str,
    service: UserNotificationService = Depends(get_user_notification_service)
):
    success = await service.mark_notification_as_read(
        user_id=UUID(user_id),
        notification_recipient_id=UUID(notification_id)
    )
    return {"success": success}
```

## Key Benefits

1. **Leverages Existing Architecture**: Uses your notification services for content
2. **Database Efficient**: Optimized queries with proper indexing
3. **Content Rich**: Full subject/body formatting using entity data
4. **Status Management**: Read/unread tracking built-in
5. **Error Resilient**: Graceful handling of missing entities
6. **Paginated**: Built-in pagination support
7. **Filtered**: Support for status and read/unread filters
8. **Extensible**: Easy to add new notification types

## Architecture Completeness ✅

The notification architecture now supports **both directions**:

- ✅ **Creating Notifications**: Using `create_notification_simple_by_code()`
- ✅ **Retrieving User Notifications**: Using `UserNotificationService`
- ✅ **Formatting Content**: Dynamic subject/body generation
- ✅ **Status Management**: Read/unread tracking
- ✅ **Dashboard Integration**: Quick summary functions

Your notification system is now complete and ready for production use!