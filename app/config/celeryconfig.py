from celery.schedules import crontab
from .settings import settings

# Basic Celery Configuration
broker_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
result_backend = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

# Task Discovery
include = ["app.tasks"]

# Timezone Configuration
timezone = "Asia/Bangkok"
enable_utc = True

# Task Result Configuration
result_expires = 3600

# Task Serialization
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"

# Task Execution Configuration
task_track_started = True
task_time_limit = 30 * 60  # 30 minutes
task_soft_time_limit = 25 * 60  # 25 minutes

# Worker Configuration
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000

# Task Retry Configuration
task_acks_late = True
task_reject_on_worker_lost = True
task_default_retry_delay = 60  # 60 seconds
task_max_retries = 3

# Exponential Backoff Settings
task_retry_backoff = True
task_retry_backoff_max = 700  # Max 700 seconds
task_retry_jitter = False

# All scheduled tasks use Asia/Bangkok timezone
beat_schedule = {
    # Daily notification tasks - Run at 9:00 AM Bangkok time
    "daily-scheduled-notifications-processor": {
        "task": "app.tasks.cron.daily_scheduled_notification_processor.daily_scheduled_notifications_processor_task",
        "schedule": crontab(hour=9, minute=0),
        "args": ("daily_scheduled_processor_cron",),
    },
    "daily-requirement-schedule-notifier": {
        "task": "app.tasks.cron.daily_requirement_schedule_notifier.daily_requirement_schedule_notifier_task",
        "schedule": crontab(hour=9, minute=0),
        "args": ("daily_requirement_schedule_notifier_cron",),
    },
    # Daily maintenance tasks - Run at midnight Bangkok time
    "daily-notification-expiration": {
        "task": "app.tasks.cron.daily_notification_expiration.daily_notification_expiration_task",
        "schedule": crontab(hour=0, minute=5),
        "args": ("daily_expiration_cron",),
    },
    # Monthly schedule management - 1st of every month at midnight Bangkok time
    "monthly-schedule-creator": {
        "task": "app.tasks.cron.monthly_schedule_creator.monthly_schedule_creator_task",
        "schedule": crontab(hour=0, minute=0, day_of_month=1),
        "args": ("monthly_schedule_creator_cron",),
    },
    # Annual maintenance - Second Monday of August at 2:00 AM Bangkok time
    "annual-requirement-archiver": {
        "task": "app.tasks.cron.annual_requirement_archiver.annual_requirement_archiver_task",
        "schedule": crontab(
            hour=2, minute=0, day_of_week=1, month_of_year=8, day_of_month="8-14"
        ),
        "args": ("annual_requirement_archiver_cron",),
    },
    # Annual batch processing - Midnight on every Wednesday in August and February Bangkok time
    "annual-batch-processor": {
        "task": "app.tasks.cron.annual_batch_processor.annual_batch_processor_task",
        "schedule": crontab(hour=0, minute=0, day_of_week=3, month_of_year="2,8"),
        "args": ("annual_batch_processor_cron",),
    },
    # LINE API management - Every 15 days at 3:00 AM Bangkok time
    "line-token-manager": {
        "task": "app.tasks.cron.line_token_manager.line_token_manager_task",
        "schedule": crontab(hour=3, minute=0, day_of_month="*/15"),
        "args": ("line_token_manager_cron",),
    },
}

# Default Queue
task_default_queue = "sitportal"

# Beat Scheduler Configuration
beat_schedule_filename = "tmp/celerybeat-schedule"
