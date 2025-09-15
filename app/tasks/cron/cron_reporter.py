import asyncio

from app.celery import celery
from app.db.session import get_sync_session
from app.db.models import CronReport
from app.utils.logging import get_logger
from app.utils.datetime_utils import naive_utc_now

logger = get_logger()


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def cron_reporter_task(self, request_id: str):
    """
    Simple Celery beat task to test cron functionality and create CronReport records.

    Args:
        request_id: The request ID from the scheduled beat task
    """
    return asyncio.run(_async_cron_reporter(request_id))


async def _async_cron_reporter(request_id: str):
    """
    Private async function that creates a test CronReport record.

    Args:
        request_id: The request ID for tracking
    """
    logger_ctx = logger.bind(request_id=request_id)

    try:
        logger_ctx.info("Starting cron reporter task")

        for db_session in get_sync_session():
            try:
                # Create a new CronReport record
                cron_report = CronReport(
                    job_name="cron_reporter_test",
                    run_at=naive_utc_now(),
                    status="SUCCESS",
                    message="Test cron job executed successfully",
                    details=f"This is a test cron job that runs every 2 minutes. Request ID: {request_id}",
                )

                db_session.add(cron_report)
                db_session.commit()

                logger_ctx.info(
                    f"Cron report created successfully with ID: {cron_report.id}"
                )

                return {
                    "success": True,
                    "message": "Cron reporter task completed successfully",
                    "report_id": cron_report.id,
                    "request_id": request_id,
                }

            except Exception as db_error:
                db_session.rollback()
                logger_ctx.error(
                    f"Database error in cron reporter task: {str(db_error)}"
                )

                # Create a failure record if possible
                try:
                    failure_report = CronReport(
                        job_name="cron_reporter_test",
                        run_at=naive_utc_now(),
                        status="FAILED",
                        message="Test cron job failed with database error",
                        details=f"Error: {str(db_error)}, Request ID: {request_id}",
                    )
                    db_session.add(failure_report)
                    db_session.commit()
                except Exception:
                    pass  # If we can't even log the failure, just continue

                raise db_error

    except Exception as e:
        logger_ctx.error(f"Cron reporter task failed: {str(e)}")
        return {"success": False, "error": str(e), "request_id": request_id}
