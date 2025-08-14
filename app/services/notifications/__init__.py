from .base import BaseNotificationService
from .registry import NotificationServiceRegistry, notification_service
from .utils import get_notification_message, create_notification_simple, get_notification_message_by_code, create_notification_simple_by_code, get_user_notifications_summary
from .user_notifications import UserNotificationService, get_user_notification_service

# Import all notification services to trigger registration
from .certificate_submission_notification_service import (
    CertificateSubmissionSubmitNotificationService,
    CertificateSubmissionUpdateNotificationService,
    CertificateSubmissionDeleteNotificationService,
    CertificateSubmissionVerifyNotificationService,
    CertificateSubmissionRejectNotificationService,
    CertificateSubmissionRequestNotificationService,
)
from .program_requirement_schedule_notification_service import (
    ProgramRequirementScheduleOverdueNotificationService,
    ProgramRequirementScheduleWarnNotificationService,
    ProgramRequirementScheduleRemindNotificationService,
)

__all__ = [
    "BaseNotificationService", 
    "NotificationServiceRegistry", 
    "notification_service",
    "get_notification_message",
    "get_notification_message_by_code", 
    "create_notification_simple",
    "create_notification_simple_by_code",
    "get_user_notifications_summary",
    "UserNotificationService",
    "get_user_notification_service",
    # Certificate submission services
    "CertificateSubmissionSubmitNotificationService",
    "CertificateSubmissionUpdateNotificationService", 
    "CertificateSubmissionDeleteNotificationService",
    "CertificateSubmissionVerifyNotificationService",
    "CertificateSubmissionRejectNotificationService",
    "CertificateSubmissionRequestNotificationService",
    # Program requirement schedule services
    "ProgramRequirementScheduleOverdueNotificationService",
    "ProgramRequirementScheduleWarnNotificationService", 
    "ProgramRequirementScheduleRemindNotificationService",
]