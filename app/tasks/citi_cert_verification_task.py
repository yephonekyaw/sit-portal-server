from sqlalchemy.ext.asyncio import AsyncSession

from app.celery import celery
from app.db.session import get_async_session
from app.services.citi_automation_service import get_citi_automation_service
from app.utils.logging import get_logger


@celery.task(bind=True)
async def verify_certificate_task(self, request_id: str, submission_id: str):
    """
    Celery task to verify a certificate submission.

    Args:
        request_id: The request ID from the original HTTP request
        submission_id: UUID of the certificate submission to verify
    """
    logger = get_logger().bind(request_id=request_id)
    db_session: AsyncSession | None = None

    try:

        # Get async database session using context manager
        async for db_session in get_async_session():
            break

        if not db_session:
            logger.error("Failed to get database session")
            return {
                "success": False,
                "error": "Failed to get database session",
                "request_id": request_id,
            }

        # Use the refactored service for verification
        citi_service = get_citi_automation_service()
        result = await citi_service.verify_certificate_submission(
            db_session=db_session,
            request_id=request_id,
            submission_id=submission_id,
        )

        if not result["success"]:
            logger.error(
                "Certificate verification task failed",
                submission_id=submission_id,
                error=result.get("error"),
            )

        return result

    except Exception as e:
        logger.error(
            "Certificate verification task exception",
            submission_id=submission_id,
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )
        if db_session:
            await db_session.rollback()
        return {
            "success": False,
            "error": str(e),
            "submission_id": submission_id,
            "request_id": request_id,
        }
    finally:
        if db_session:
            await db_session.close()
