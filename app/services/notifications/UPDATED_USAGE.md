# Updated Notification Service Usage Guide

## Type Corrections Applied ✅

The notification service has been updated with correct types:

- **notification_type_id**: Changed from `int` to `uuid.UUID`
- **priority**: Changed from `int` to `str` (Priority enum values)

## Updated Usage Examples

### One-Line Notification Creation

```python
from app.services.notifications import create_notification_simple
import uuid

# Certificate submitted notification
result = await create_notification_simple(
    notification_type_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # certificate_submission_submit
    entity_id=certificate_submission_id,
    actor_type="STUDENT",
    recipient_ids=[staff_id1, staff_id2],
    db_session=db,
    actor_id=student_id
)

# Requirement overdue notification  
result = await create_notification_simple(
    notification_type_id=uuid.UUID("00000000-0000-0000-0000-000000000007"),  # program_requirement_overdue
    entity_id=program_requirement_schedule_id,
    actor_type="SYSTEM",
    recipient_ids=[student_id],
    db_session=db,
    scheduled_for=datetime.now() + timedelta(hours=1)
)
```

### GET Request Message Construction

```python
from app.services.notifications import get_notification_message
import uuid

# Get formatted message for certificate verification
message = await get_notification_message(
    notification_type_id=uuid.UUID("00000000-0000-0000-0000-000000000004"),  # certificate_submission_verify
    entity_id=certificate_submission_id,
    channel_type="IN_APP",
    db_session=db
)

# Get formatted message for overdue requirement
message = await get_notification_message(
    notification_type_id=uuid.UUID("00000000-0000-0000-0000-000000000007"),  # program_requirement_overdue  
    entity_id=schedule_id,
    channel_type="IN_APP",
    db_session=db
)
```

### Direct Service Usage

```python
from app.services.notifications import NotificationServiceRegistry
import uuid

# Get specific service directly
service = NotificationServiceRegistry.create_service(
    uuid.UUID("00000000-0000-0000-0000-000000000001"), 
    db_session
)
if service:
    # Get notification data
    data = await service.get_notification_data(entity_id)
    
    # Construct message
    message = service.construct_message("IN_APP", data)
    
    # Or use the helper method
    message = await service.get_template_message("IN_APP", entity_id)
```

## Updated Notification Type Mapping

### Certificate Submission Notifications
- **UUID("...001")**: Certificate Submitted (`certificate_submission_submit`)
- **UUID("...002")**: Certificate Updated (`certificate_submission_update`) 
- **UUID("...003")**: Certificate Deleted (`certificate_submission_delete`)
- **UUID("...004")**: Certificate Verified (`certificate_submission_verify`)
- **UUID("...005")**: Certificate Rejected (`certificate_submission_reject`)
- **UUID("...006")**: Certificate Review Requested (`certificate_submission_request`)

### Program Requirement Schedule Notifications
- **UUID("...007")**: Requirement Overdue (`program_requirement_overdue`)
- **UUID("...008")**: Requirement Warning (`program_requirement_warn`)
- **UUID("...009")**: Requirement Reminder (`program_requirement_remind`)

## Priority Values (String)

All services now return string values for priority:
- `Priority.LOW.value` → `"low"`
- `Priority.MEDIUM.value` → `"medium"`
- `Priority.HIGH.value` → `"high"`
- `Priority.URGENT.value` → `"urgent"`

## Registry Status Check

```python
from app.services.notifications import NotificationServiceRegistry

# List all registered types (now returns Dict[UUID, str])
registered = NotificationServiceRegistry.list_registered_types()
print(registered)
# {
#   UUID('00000000-0000-0000-0000-000000000001'): "CertificateSubmissionSubmitNotificationService",
#   UUID('00000000-0000-0000-0000-000000000002'): "CertificateSubmissionUpdateNotificationService", 
#   ...
# }
```

## Implementation Notes

1. **UUID Format**: Using consistent zero-padded UUIDs for notification type IDs
2. **Type Safety**: All type hints updated to match actual data types
3. **Backwards Compatibility**: The functionality remains the same, only types have been corrected
4. **Registry**: Updated to handle UUID keys instead of integers
5. **Decorators**: Updated to accept UUID parameters for service registration