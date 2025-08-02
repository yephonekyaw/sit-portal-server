# Procfile for running FastAPI and Celery together
# This file should be named exactly "Procfile" (no extension)

# FastAPI web server
web: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Celery worker (Windows-compatible with --pool=solo)
worker: celery -A app.celery worker --loglevel=info --pool=solo

# Optional: Celery Beat scheduler (for periodic tasks)
# beat: celery -A app.celery beat --loglevel=info

# Optional: Celery Flower monitoring (web UI for Celery)
# flower: celery -A app.celery flower --port=5555