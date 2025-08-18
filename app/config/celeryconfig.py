from celery.schedules import crontab
from .settings import settings

# Basic Celery Configuration
broker_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
result_backend = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

# Task Discovery
imports = ["app.tasks"]

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

# Beat Schedule Configuration
beat_schedule = {
    # Daily scheduled notifications processor at 9:00 AM Bangkok time
    "daily-scheduled-notifications-processor": {
        "task": "app.tasks.daily_scheduled_processor.daily_scheduled_notifications_processor_task",
        "schedule": crontab(hour=9, minute=0),  # 9:00 AM Bangkok time
        "args": ("daily_scheduled_processor_cron",),
        "options": {"queue": "notifications"},
    },
    # Daily notification expiration task at 00:05 AM Bangkok time
    "daily-notification-expiration": {
        "task": "app.tasks.daily_notification_expiration.daily_notification_expiration_task",
        "schedule": crontab(hour=0, minute=5),  # 00:05 AM Bangkok time
        "args": ("daily_expiration_cron",),
        "options": {"queue": "notifications"},
    },
}

# Queue Configuration
task_routes = {
    "app.tasks.notification_*": {"queue": "notifications"},
    "app.tasks.daily_scheduled_processor.*": {"queue": "notifications"},
    "app.tasks.daily_notification_expiration.*": {"queue": "notifications"},
    "app.tasks.citi_cert_verification_task.*": {"queue": "verification"},
}

# Default Queue
task_default_queue = "default"

# Beat Scheduler Configuration
beat_schedule_filename = "app/celerybeat-schedule"

# Environment-specific configurations
if settings.ENVIRONMENT == "production":
    # Production-specific settings
    worker_concurrency = 4
    worker_max_memory_per_child = 200000  # 200MB
    task_time_limit = 60 * 60  # 1 hour in production
    task_soft_time_limit = 55 * 60  # 55 minutes

elif settings.ENVIRONMENT == "development":
    # Development-specific settings
    worker_concurrency = 2
    task_always_eager = False  # Set to True to run tasks synchronously for debugging
    task_eager_propagates = True
else:
    # Default/testing settings
    worker_concurrency = 1
    task_always_eager = False
