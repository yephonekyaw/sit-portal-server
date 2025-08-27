from fastapi import APIRouter
import uuid
from datetime import datetime, timezone, timedelta

from app.db.session import AsyncSessionLocal
from app.db.models import LineChannelAccessToken
from app.utils.logging import get_logger
from app.tasks.bugs import report_bugs

bug_router = APIRouter()
logger = get_logger()


@bug_router.get("/report")
async def report_bug():
    async with AsyncSessionLocal.begin() as session:
        try:
            line_access_token = LineChannelAccessToken(
                key_id=str(uuid.uuid4()),
                access_token=str(uuid.uuid4()),
                token_type="Bearer",
                expires_in=3600,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=3600),
                is_active=True,
                is_revoked=False,
                revoked_at=None,
            )
            session.add(line_access_token)
            await session.commit()
            report_bugs.delay()  # type: ignore
            return {"message": "Bug reported successfully"}
        except Exception as e:
            logger.error(f"Error occurred while reporting bug: {e}")
            return {"error": f"Error occurred: {e}"}
