# Database-Integrated Notification Service Usage Guide

## ✅ Complete Database Integration

The notification service now fetches `notification_type_id` and `priority` directly from the database using the `notification_code`, ensuring data consistency with your seed data.

## Architecture Changes

### Base Class Updates
- **notification_code**: Each service defines its code (matches seed data)
- **Database Fetching**: `notification_type_id` and `priority` retrieved from `NotificationType` table
- **Caching**: Database values cached per service instance for performance

### Registry Updates
- **Dual Registration**: Services register by both UUID and code
- **Code-Based Access**: New methods to access services by notification code
- **Flexible Lookup**: Support for both UUID and code-based service creation

## Updated Usage Examples

### Option 1: Using Notification Code (Recommended)

```python
from app.services.notifications import create_notification_simple_by_code, get_notification_message_by_code

# Create notification using code (matches seed data)
result = await create_notification_simple_by_code(
    notification_code="certificate_submission_submit",
    entity_id=certificate_submission_id,
    actor_type="STUDENT",
    recipient_ids=[staff_id1, staff_id2],
    db_session=db,
    actor_id=student_id
)

# Get message using code
message = await get_notification_message_by_code(
    notification_code="certificate_submission_verify",
    entity_id=certificate_submission_id,
    channel_type="IN_APP",
    db_session=db
)
```

### Option 2: Using UUID (Still Supported)

```python
from app.services.notifications import create_notification_simple, get_notification_message

# If you have the UUID from database
result = await create_notification_simple(
    notification_type_id=notification_type_uuid,  # From database
    entity_id=certificate_submission_id,
    actor_type="STUDENT", 
    recipient_ids=[staff_id1, staff_id2],
    db_session=db
)
```

## Service Implementation Details

### Each Service Now Has:
```python
@notification_service(notification_code="certificate_submission_submit")
class CertificateSubmissionSubmitNotificationService(BaseNotificationService):
    
    @property
    def notification_code(self) -> str:
        return "certificate_submission_submit"  # Matches seed data
    
    # notification_type_id and priority are fetched from database automatically
    # using the notification_code via _fetch_notification_type()
```

### Database Integration Flow:
1. Service instantiated with `db_session`
2. `notification_code` property defines the database lookup key
3. First access to `get_notification_type_id()` or `get_priority()` queries database
4. Results cached in service instance for performance
5. Values come directly from `NotificationType` table seeded data

## Available Notification Codes

### Certificate Submission Services
- `"certificate_submission_submit"`
- `"certificate_submission_update"`
- `"certificate_submission_delete"`
- `"certificate_submission_verify"`
- `"certificate_submission_reject"`
- `"certificate_submission_request"`

### Program Requirement Schedule Services  
- `"program_requirement_overdue"`
- `"program_requirement_warn"`
- `"program_requirement_remind"`

## Registry Access

```python
from app.services.notifications import NotificationServiceRegistry

# List services by code (recommended for debugging)
codes = NotificationServiceRegistry.list_registered_codes()
print(codes)
# {
#   "certificate_submission_submit": "CertificateSubmissionSubmitNotificationService",
#   "certificate_submission_update": "CertificateSubmissionUpdateNotificationService",
#   ...
# }

# Create service by code
service = NotificationServiceRegistry.create_service_by_code(
    "certificate_submission_submit", 
    db_session
)

# Get notification type ID and priority from database
notification_type_id = await service.get_notification_type_id()
priority = await service.get_priority()
```

## Benefits of Database Integration

1. **Data Consistency**: Values always match database seed data
2. **Dynamic Configuration**: Priority/settings can be changed in database
3. **Centralized Management**: Single source of truth in `NotificationType` table
4. **Flexible Access**: Support for both UUID and code-based access
5. **Performance**: Database values cached per service instance
6. **Maintainable**: No hardcoded UUIDs in service code

## Migration from Hardcoded Values

**Old way (hardcoded):**
```python
@property
def notification_type_id(self) -> uuid.UUID:
    return uuid.UUID("hardcoded-uuid")

@property  
def priority(self) -> str:
    return "medium"
```

**New way (database-driven):**
```python
@property
def notification_code(self) -> str:
    return "certificate_submission_submit"

# notification_type_id and priority automatically fetched from database
# using base class methods get_notification_type_id() and get_priority()
```

The system now provides a clean separation between service logic and configuration data, with all notification metadata managed through the database.