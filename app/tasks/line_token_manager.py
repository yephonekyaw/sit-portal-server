"""
LINE channel access token management background task.

This task runs every 15 days to:
1. Generate new channel access tokens before expiration
2. Revoke expired tokens via LINE API
3. Clean up old revoked tokens from database
"""

from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.celery import celery
from app.db.session import get_async_session
from app.services.line_token_management_service import LineChannelTokenService
from app.utils.logging import get_logger
from app.utils.errors import DatabaseError


@celery.task(bind=True, max_retries=3, default_retry_delay=300)
async def line_token_manager_task(self, request_id: str) -> Dict[str, Any]:
    """
    Manage LINE channel access tokens.

    1. Generate new token if current expires within 7 days
    2. Revoke expired tokens via LINE API
    3. Clean up old revoked tokens
    """
    logger = get_logger().bind(request_id=request_id)
    db_session: AsyncSession | None = None

    try:
        async for db_session in get_async_session():
            break
        if not db_session:
            raise DatabaseError("Failed to get database session")

        line_service = LineChannelTokenService(db_session)
        stats = {"new_tokens_generated": 0, "tokens_revoked": 0, "tokens_cleaned": 0}

        # Generate new token if needed
        current_token = await line_service.get_active_access_token()
        if (
            not current_token
            or (current_token.expires_at - datetime.now(timezone.utc)).days <= 7
        ):
            new_token = await line_service.generate_and_store_new_token()
            if new_token:
                stats["new_tokens_generated"] = 1
                logger.info(f"Generated new token: {new_token.key_id}")

        # Revoke expired tokens
        try:
            valid_kids = await line_service.get_valid_token_kids()
            expired_tokens = await line_service.get_expired_tokens_by_kids(valid_kids)

            for token in expired_tokens:
                if await line_service.revoke_channel_access_token(token.access_token):
                    await line_service.mark_token_as_revoked(token.key_id)
                    stats["tokens_revoked"] += 1
        except Exception as e:
            logger.error(f"Token revocation failed: {str(e)}")

        # Clean up old tokens
        stats["tokens_cleaned"] = await line_service.cleanup_expired_tokens()

        logger.info("LINE token management completed", **stats)
        return {"success": True, "request_id": request_id, "statistics": stats}

    except Exception as e:
        logger.error(f"LINE token management failed: {str(e)}", exc_info=True)
        if db_session:
            await db_session.rollback()

        if self.request.retries < self.max_retries:
            retry_delay = min(2**self.request.retries * 300, 1800)
            raise self.retry(countdown=retry_delay)

        return {"success": False, "error": str(e), "request_id": request_id}

    finally:
        if db_session:
            await db_session.close()
