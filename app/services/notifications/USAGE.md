# Notification Service Usage Guide

## Complete Implementation Based on Seed Data

This implementation now includes all notification types from the seed data files:

### Certificate Submission Notifications (Types 1-6)
- **Type 1**: Certificate Submitted (`certificate_submission_submit`)
- **Type 2**: Certificate Updated (`certificate_submission_update`) 
- **Type 3**: Certificate Deleted (`certificate_submission_delete`)
- **Type 4**: Certificate Verified (`certificate_submission_verify`)
- **Type 5**: Certificate Rejected (`certificate_submission_reject`)
- **Type 6**: Certificate Review Requested (`certificate_submission_request`)

### Program Requirement Schedule Notifications (Types 7-9)
- **Type 7**: Requirement Overdue (`program_requirement_overdue`)
- **Type 8**: Requirement Warning (`program_requirement_warn`)
- **Type 9**: Requirement Reminder (`program_requirement_remind`)

## Client Usage Examples

### One-Line Notification Creation

```python
from app.services.notifications import create_notification_simple

# Certificate submitted notification
result = await create_notification_simple(
    notification_type_id=1,  # certificate_submission_submit
    entity_id=certificate_submission_id,
    actor_type="STUDENT",
    recipient_ids=[staff_id1, staff_id2],
    db_session=db,
    actor_id=student_id
)

# Requirement overdue notification  
result = await create_notification_simple(
    notification_type_id=7,  # program_requirement_overdue
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

# Get formatted message for certificate verification
message = await get_notification_message(
    notification_type_id=4,  # certificate_submission_verify
    entity_id=certificate_submission_id,
    channel_type="IN_APP",
    db_session=db
)
# Returns: {
#   "subject": "Certificate Verified: AWS Cloud Practitioner",
#   "body": "AWS Cloud Practitioner for John Doe 12345678 approved by Dr. Smith."
# }

# Get formatted message for overdue requirement
message = await get_notification_message(
    notification_type_id=7,  # program_requirement_overdue  
    entity_id=schedule_id,
    channel_type="IN_APP",
    db_session=db
)
# Returns: {
#   "subject": "Requirement Overdue: Industry Certification",
#   "body": "Industry Certification for Computer Science is 5 days overdue. Deadline was 2024-01-15."
# }
```

### Direct Service Usage

```python
from app.services.notifications import NotificationServiceRegistry

# Get specific service directly
service = NotificationServiceRegistry.create_service(1, db_session)
if service:
    # Get notification data
    data = await service.get_notification_data(entity_id)
    
    # Construct message
    message = service.construct_message("IN_APP", data)
    
    # Or use the helper method
    message = await service.get_template_message("IN_APP", entity_id)
```

## Data Retrieved for Each Notification Type

### Certificate Submission Notifications
All certificate submission services retrieve:
```python
{
    "submission_id": "uuid-string",
    "certificate_name": "AWS Cloud Practitioner", 
    "student_name": "John Doe",
    "student_roll_number": "12345678",
    "program_name": "Computer Science",
    "verifier_name": "Dr. Smith",  # For verify/reject only
    "status": "approved"
}
```

### Program Requirement Schedule Notifications  
All requirement schedule services retrieve:
```python
{
    "schedule_id": "uuid-string",
    "requirement_name": "Industry Certification",
    "program_name": "Computer Science", 
    "program_code": "CS101",
    "academic_year": "2024-2025",
    "deadline_date": "2024-01-15",
    "days_overdue": 5,       # For overdue only
    "days_remaining": 10,    # For warning only  
    "mandatory_flag": "This is a mandatory requirement.",  # For reminder only
    "is_mandatory": true,
    "target_year": 2
}
```

## Registry Status

View all registered notification types:
```python
from app.services.notifications import NotificationServiceRegistry

# List all registered types
registered = NotificationServiceRegistry.list_registered_types()
print(registered)
# {
#   1: "CertificateSubmissionSubmitNotificationService",
#   2: "CertificateSubmissionUpdateNotificationService", 
#   ...
#   9: "ProgramRequirementScheduleRemindNotificationService"
# }
```

## Template Format Matching

The implementation matches the template formats from `seed_notification_channel_templates.py`:

- Uses `{certificate_name}`, `{student_name}`, etc. placeholders
- Supports IN_APP channel type (as specified in seed data)
- Can be easily extended for EMAIL, SMS channels
- Template format is MARKDOWN by default (as per seed data)