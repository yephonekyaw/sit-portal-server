import asyncio
import sys

from app.celery import celery
from app.db.session import AsyncSessionLocal
from app.services.citi_automation_service import get_citi_automation_service
from app.utils.logging import get_logger

logger = get_logger()


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def verify_certificate_task(self, request_id: str, submission_id: str):
    """
    Celery task to verify a certificate submission.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        result = asyncio.run(_async_verify_certificate(request_id, submission_id))
        return result
    except Exception as e:
        logger.error(
            f"Certificate verification task failed for {submission_id}: {str(e)}",
            request_id=request_id,
        )
        return {
            "success": False,
            "error": str(e),
            "submission_id": submission_id,
            "request_id": request_id,
        }


async def _async_verify_certificate(request_id: str, submission_id: str):
    logger = get_logger().bind(request_id=request_id)

    async with AsyncSessionLocal() as session:
        try:
            citi_service = get_citi_automation_service()

            result = await citi_service.verify_certificate_submission(
                db_session=session,
                request_id=request_id,
                submission_id=submission_id,
            )

            if result["success"]:
                await session.commit()
            else:
                await session.rollback()
                logger.error(
                    f"Certificate verification task failed for {submission_id}: {result.get('error')}"
                )

            return result

        except Exception as e:
            await session.rollback()
            logger.error(
                f"Certificate verification task exception for {submission_id}: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e),
                "submission_id": submission_id,
                "request_id": request_id,
            }
        finally:
            await session.close_all()
