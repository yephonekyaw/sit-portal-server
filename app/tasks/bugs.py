import asyncio
from sqlalchemy import select

from app.celery import celery

from app.db.session import get_sync_session
from app.db.models import LineChannelAccessToken
from app.utils.logging import get_logger

logger = get_logger()


@celery.task
def report_bugs():
    asyncio.get_event_loop().run_until_complete(_async_report_bugs())


async def _async_report_bugs():
    for session in get_sync_session():
        try:
            result = session.execute(select(LineChannelAccessToken))
            tokens = result.scalars().all()
            for token in tokens:
                logger.info(f"Reporting bug for token: {token.key_id}")
                # Simulate bug reporting
                await asyncio.sleep(1)
            logger.info("All bugs reported successfully.")
            return {"success": True}
        except Exception:
            logger.error("Error occurred while reporting bugs.")
            return {"error": "Error occurred while reporting bugs."}
