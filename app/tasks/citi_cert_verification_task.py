import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery import celery
from app.db.session import get_async_session
from app.services.citi_automation_service import get_citi_automation_service
from app.utils.logging import get_logger


@celery.task(bind=True)
def verify_certificate_task(self, request_id: str, submission_id: str):
    """
    Celery task to verify a certificate submission.

    Args:
        request_id: The request ID from the original HTTP request
        submission_id: UUID of the certificate submission to verify
    """

    async def _verify_certificate_async():
        logger = get_logger().bind(request_id=request_id)
        db_session: Optional[AsyncSession] = None

        try:
            logger.info(
                "Starting certificate verification task",
                submission_id=submission_id,
                request_id=request_id,
            )

            # Get async database session
            async_session_gen = get_async_session()
            db_session = await async_session_gen.__anext__()

            # Use the refactored service for verification
            citi_service = get_citi_automation_service()
            result = await citi_service.verify_certificate_submission(
                db_session=db_session,
                request_id=request_id,
                submission_id=submission_id,
            )

            if result["success"]:
                logger.info(
                    "Certificate verification task completed",
                    submission_id=submission_id,
                    decision=result.get("validation_decision"),
                    confidence=result.get("confidence_level"),
                    score=result.get("overall_score"),
                )
            else:
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

    # Run the async function
    return asyncio.run(_verify_certificate_async())
