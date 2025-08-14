# Notification Service Architecture

This notification service follows object-oriented design principles with a base class and specialized sub-classes for each notification type.

## Architecture Overview

### Base Class: `BaseNotificationService`
- Contains common functionality for all notification types
- Has `db_session: AsyncSession` in constructor (like `ProgramServiceProvider`)
- Implements the common `create()` method that all sub-classes use
- Defines abstract methods that sub-classes must implement

### Sub-classes
- Each notification type has its own service class
- Inherits from `BaseNotificationService`
- Defines `notification_type_id` and `priority` as properties
- Implements entity-specific logic in `get_notification_data()`
- Implements message construction logic in `construct_message()`

### Registry Pattern
- `NotificationServiceRegistry` maps notification type IDs to service classes
- Solves the GET request problem by dynamically selecting the right service
- Uses decorator `@notification_service(type_id)` for auto-registration

## Usage Examples

### Creating a New Notification Type

```python
from .base import BaseNotificationService
from .registry import notification_service

@notification_service(notification_type_id=2)  # Auto-registers
class CertificateNotificationService(BaseNotificationService):
    @property
    def notification_type_id(self) -> int:
        return 2
    
    @property
    def priority(self) -> int:
        return 8  # High priority
    
    async def get_notification_data(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        # Implement certificate-specific data retrieval
        pass
    
    def construct_message(self, channel_type: str, notification_data: Dict[str, Any]) -> Dict[str, str]:
        # Implement certificate-specific message construction
        pass
```

### Client Layer Usage (One Line)

```python
from app.services.notifications import create_notification_simple

# One line notification creation
result = await create_notification_simple(
    notification_type_id=1,  # Program notification
    entity_id=program_id,
    actor_type="STAFF",
    recipient_ids=[student_id1, student_id2],
    db_session=db,
    actor_id=staff_id,  # optional
    scheduled_for=datetime.now(),  # optional
    custom_data="any_value"  # optional metadata
)
```

### GET Request Handling

```python
from app.services.notifications import get_notification_message

# Get formatted message for any notification type
message = await get_notification_message(
    notification_type_id=1,
    entity_id=program_id,
    channel_type="EMAIL",
    db_session=db
)

# Returns: {"subject": "Program Update: CS101", "body": "..."}
```

## Key Benefits

1. **OO Best Practices**: Proper inheritance with base class containing common logic
2. **Single Responsibility**: Each sub-class handles only one notification type
3. **Easy Extension**: Add new notification types by creating new sub-classes
4. **Registry Pattern**: Solves the GET request dynamic dispatch problem
5. **One-Line Client Usage**: Simple interface for creating notifications
6. **Consistent Architecture**: Follows existing service provider pattern

## Files Structure

```
app/services/notifications/
├── __init__.py                          # Package exports
├── base.py                              # BaseNotificationService
├── registry.py                          # Registry pattern implementation
├── utils.py                             # Utility functions for client layer
├── program_notification_service.py     # Example implementation
└── README.md                            # This documentation
```