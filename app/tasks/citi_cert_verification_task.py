import asyncio

from app.celery import celery
from app.db.session import get_sync_session
from app.services.citi_automation_service import get_citi_automation_service
from app.utils.logging import get_logger

logger = get_logger()


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def verify_certificate_task(self, request_id: str, submission_id: str):
    """
    Celery task to verify a certificate submission.

    Args:
        request_id: The request ID from the original HTTP request
        submission_id: UUID of the certificate submission to verify
    """
    return asyncio.run(_async_verify_certificate(request_id, submission_id))


async def _async_verify_certificate(request_id: str, submission_id: str):

    logger = get_logger().bind(request_id=request_id)

    for db_session in get_sync_session():
        try:
            # Use the refactored service for verification
            citi_service = get_citi_automation_service()

            result = await citi_service.verify_certificate_submission(
                db_session=db_session,
                request_id=request_id,
                submission_id=submission_id,
            )

            if not result["success"]:
                logger.error(
                    f"Certificate verification task failed for {submission_id}: {result.get('error')}"
                )
            return result
        except Exception as e:
            logger.error(
                f"Certificate verification task exception for {submission_id}: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e),
                "submission_id": submission_id,
                "request_id": request_id,
            }
