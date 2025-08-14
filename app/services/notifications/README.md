# Notification Service Documentation

Template-based notification system for the SIT Portal application.

## Overview

The notification service provides a unified interface for creating and managing notifications across different entity types (certificate submissions, program requirements, etc.) with template-based message formatting.

### Features

- **Unified API**: Single interface for all notification types
- **Template-based**: Database-driven message templates with placeholder substitution
- **Multi-channel**: Support for in-app and LINE app notifications
- **Type-safe**: Full database integration with proper transaction handling
- **Extensible**: Easy to add new notification types

## Architecture

### Core Components

```
notifications/
├── __init__.py           # Public API exports
├── base.py              # Abstract base service class
├── certificate_service.py # Certificate submission notifications
├── schedule_service.py   # Program requirement schedule notifications
├── deadline_utils.py     # Deadline calculation utilities
├── registry.py          # Service factory and registration
├── user_notifications.py # User-facing notification retrieval
└── utils.py             # Utility functions for common operations
```

### Database Schema

The system uses these main database tables:

- **`notification_types`**: Defines available notification types and default settings
- **`notification_channel_templates`**: Message templates per notification type and channel
- **`notifications`**: Individual notification instances
- **`notification_recipients`**: Links notifications to users with delivery status

## Usage

### Creating Notifications

```python
from app.services.notifications import create_notification

# Create a certificate submission notification
notification_id = await create_notification(
    notification_code="certificate_submission_submit",
    entity_id=submission_id,
    actor_type="user",
    recipient_ids=[user_id],
    db_session=db,
    actor_id=staff_user_id  # Optional
)
```

### Getting Formatted Messages

```python
from app.services.notifications import get_notification_message

# Get a formatted message for display
message = await get_notification_message(
    notification_code="certificate_submission_verify",
    entity_id=submission_id,
    channel_type="in_app",
    db_session=db
)

print(message["subject"])  # "Certificate Verified"
print(message["body"])     # "Your certificate submission has been verified..."
```

### User Notifications

```python
from app.services.notifications import UserNotificationService

service = UserNotificationService(db_session)

# Get user's notifications
notifications = await service.get_user_notifications(
    user_id=user_id,
    limit=20,
    unread_only=True
)

# Mark notification as read
success = await service.mark_notification_as_read(user_id, notification_id)

# Get summary for dashboard
summary = await get_user_notifications_summary(user_id, db_session)
```

## Notification Types

### Certificate Submissions

| Code | Description | Triggered When |
|------|-------------|----------------|
| `certificate_submission_submit` | New submission | Student uploads certificate |
| `certificate_submission_update` | Submission updated | Student modifies submission |
| `certificate_submission_delete` | Submission deleted | Student/staff deletes submission |
| `certificate_submission_verify` | Submission approved | Staff approves submission |
| `certificate_submission_reject` | Submission rejected | Staff rejects submission |
| `certificate_submission_request` | Review requested | Manual review needed |

### Program Requirements

| Code | Description | Triggered When |
|------|-------------|----------------|
| `program_requirement_overdue` | Deadline passed | Deadline exceeded without submission |
| `program_requirement_warn` | Approaching deadline | Configurable days before deadline |
| `program_requirement_remind` | General reminder | Periodic reminders |

## Templates

### Available Variables

Template variables are automatically provided based on the entity type:

#### Certificate Submissions
- `{submission_id}` - Submission UUID
- `{certificate_name}` - Certificate type name
- `{student_name}` - Full student name
- `{student_roll_number}` - Student ID
- `{program_name}` - Academic program name
- `{submission_date}` - Date submitted
- `{updated_date}` - Last updated date
- `{status}` - Current submission status
- `{filename}` - Uploaded file name
- `{verifier_name}` - Who verified/rejected

#### Program Requirements
- `{schedule_id}` - Schedule UUID
- `{requirement_name}` - Requirement name
- `{program_name}` - Academic program name
- `{program_code}` - Program code
- `{academic_year}` - Academic year
- `{deadline_date}` - Submission deadline
- `{days_remaining}` - Days until deadline
- `{days_overdue}` - Days past deadline
- `{mandatory_flag}` - "This is a mandatory/optional requirement."
- `{target_year}` - Target student year

### Example Template

**Template Definition:**
```
Subject: Certificate {status} - {certificate_name}

Body:
Dear {student_name},

Your {certificate_name} submission has been {status}.

Submission Details:
- Student ID: {student_roll_number}
- Program: {program_name}
- Status: {status}
- Date: {submission_date}

Thank you.
```

**Rendered Result:**
```
Subject: Certificate approved - Microsoft Azure Fundamentals

Dear John Doe,

Your Microsoft Azure Fundamentals submission has been approved.

Submission Details:
- Student ID: 2021001
- Program: Information Systems
- Status: approved  
- Date: 2024-01-15

Thank you.
```

## Adding New Notification Types

### Database Setup

Add new notification type:

```sql
INSERT INTO notification_types (code, name, description, entity_type, default_priority) 
VALUES ('new_notification_type', 'New Notification', 'Description', 'entity_name', 'medium');
```

Add templates for each channel:

```sql
INSERT INTO notification_channel_templates (notification_type_id, channel_type, template_subject, template_body)
VALUES (
    (SELECT id FROM notification_types WHERE code = 'new_notification_type'),
    'in_app',
    'Subject with {placeholder}',
    'Body with {placeholder} variables'
);
```

### Service Implementation

Create a service file for new entity types (e.g., `new_entity_service.py`):

```python
from .base import BaseNotificationService

class NewEntityNotificationService(BaseNotificationService):
    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        # Fetch entity data and return template variables
        result = await self.db.execute(select(NewEntity).where(NewEntity.id == entity_id))
        entity = result.scalar_one_or_none()
        
        return {
            "placeholder": entity.some_field,
            # ... other template variables
        }

def create_new_entity_service(db_session, notification_code: str) -> NewEntityNotificationService:
    return NewEntityNotificationService(db_session, notification_code)
```

### Registry Update

Import and add factory function to `registry.py`:

```python
from .new_entity_service import create_new_entity_service

# Add to _factories dict
_factories = {
    # ... existing factories
    "new_notification_type": create_new_entity_service,
}
```

## Error Handling

Common exceptions thrown:

- **`ValueError`**: Invalid notification code or entity not found
- **Database exceptions**: SQLAlchemy exceptions for database errors
- **Template errors**: `KeyError` for missing template variables

```python
try:
    await create_notification("invalid_code", entity_id, "user", [user_id], db)
except ValueError as e:
    logger.error(f"Invalid notification type: {e}")
except Exception as e:
    logger.error(f"Notification creation failed: {e}")
```

## Performance Notes

### Caching
- Notification types are cached per service instance
- Templates are fetched on-demand

### Batch Operations
```python
# Create notifications for multiple recipients
recipient_ids = [user1_id, user2_id, user3_id]
await create_notification(
    "program_requirement_warn",
    schedule_id,
    "system", 
    recipient_ids,
    db_session
)
```

### Database Queries
- Services use `selectinload` for efficient joins
- Single query per entity type regardless of template complexity

## Testing

### Unit Tests
```python
import pytest
from app.services.notifications import create_notification

@pytest.mark.asyncio
async def test_create_certificate_notification(db_session, sample_submission):
    notification_id = await create_notification(
        "certificate_submission_submit",
        sample_submission.id,
        "user",
        [sample_submission.student.user.id],
        db_session
    )
    assert notification_id is not None
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_notification_message_formatting(db_session, sample_submission):
    message = await get_notification_message(
        "certificate_submission_submit",
        sample_submission.id,
        "in_app", 
        db_session
    )
    
    assert "subject" in message
    assert "body" in message
    assert sample_submission.certificate_type.name in message["body"]
```

## Monitoring

### Logging
Operations are logged with appropriate levels:

```python
# Successful operations
logger.info(f"Created notification {notification_id} for {notification_code}")

# Warnings for recoverable issues  
logger.warning(f"No service found for notification code: {notification_code}")

# Errors for failures
logger.error(f"Failed to create notification: {e}", exc_info=True)
```

### Metrics to Track
- Notification creation success/failure rates
- Template formatting errors
- User notification read rates
- Channel delivery success rates

## Migration from Legacy System

This refactored system maintains backward compatibility through:

1. **Same database schema**: No changes to existing tables
2. **Equivalent functionality**: All previous features preserved
3. **Streamlined API**: Reduced from multiple complex functions to 3 main functions

### Code Migration

**Before:**
```python
from app.services.notifications.certificate_submission_notification_service import CertificateSubmissionSubmitNotificationService

service = CertificateSubmissionSubmitNotificationService(db_session)
await service.create(entity_id, "user", [user_id])
```

**After:**
```python
from app.services.notifications import create_notification

await create_notification("certificate_submission_submit", entity_id, "user", [user_id], db_session)
```

## Troubleshooting

### Common Issues

**"No service found for notification code"**
- Check notification code spelling
- Verify code exists in registry `_factories` dict
- Ensure database has corresponding `notification_types` record

**"Template formatting error: missing placeholder"**
- Check template uses correct variable names
- Verify entity service returns all required template variables
- Use debug logging to inspect `notification_data` dict

**"Notification type not found in database"**
- Run database seeding to create notification types
- Check `notification_types` table has record with matching code
- Verify database connection and permissions

**"Failed to create notification recipients"**
- Check recipient user IDs exist in database
- Verify foreign key constraints
- Check database transaction handling