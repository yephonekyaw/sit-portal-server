from celery import Celery

# Create Celery app
celery = Celery("app")

# Load configuration from app.config.celeryconfig module
celery.config_from_object("app.config.celeryconfig")
