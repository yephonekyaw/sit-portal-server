import asyncio
import httpx
from datetime import datetime

from app.celery import celery
from app.db.session import get_sync_session
from app.utils.logging import get_logger
from app.utils.datetime_utils import utc_now


def annual_batch_processor_task(self, request_id: str, semester: int = 1):
    """
    Annual task to import list of students per batch for all supported programs.

    Runs on every Wednesday of August and September to import student lists for all programs from master data source.
    """
    return asyncio.run(_async_annual_batch_processor(request_id, semester))


async def _async_annual_batch_processor(request_id: str, semester: int = 1):
    logger = get_logger().bind(request_id=request_id)

    for db_session in get_sync_session():
        try:
            current_datetime = utc_now()
            current_academic_year = _calculate_current_academic_year(current_datetime)
            current_thai_academic_year = _convert_to_thai_academic_year(
                current_academic_year
            )
        except Exception as e:
            logger.error(
                "Annual batch processor task exception",
                request_id=request_id,
                error=str(e),
                exc_info=True,
            )
            return {"success": False, "error": str(e), "request_id": request_id}


def _convert_to_thai_academic_year(gregorian_year: int) -> int:
    """Convert Gregorian year to Thai academic year (Buddhist Era)"""
    return gregorian_year + 543


def _calculate_current_academic_year(current_datetime: datetime) -> int:
    """
    Calculate the current academic year based on the date.
    Academic year runs from August to May.

    Examples:
    - January 2025 -> Academic Year 2024 (Aug 2024 - May 2025)
    - August 2024 -> Academic Year 2024 (Aug 2024 - May 2025)
    - July 2024 -> Academic Year 2023 (Aug 2023 - May 2024)
    """
    if current_datetime.month >= 8:  # August or later
        return current_datetime.year
    else:  # Before August
        return current_datetime.year - 1
