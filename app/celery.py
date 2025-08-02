from celery import Celery
from app.config.settings import settings

celery = Celery(
    "app",
    broker=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    backend=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    include=["app.tasks"],
)

celery.conf.update(
    timezone="Asia/Bangkok",
    enable_utc=True,
    result_expires=3600,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Global retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,  # 60 seconds
    task_max_retries=3,
    # Exponential backoff settings
    task_retry_backoff=True,
    task_retry_backoff_max=700,  # Max 700 seconds
    task_retry_jitter=False,
)
