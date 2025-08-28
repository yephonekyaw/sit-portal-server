import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.db.models import AcademicYear
from app.utils.logging import get_logger

logger = get_logger()


def seed_academic_years(db_session: Session):
    """Sync version: Seed academic years data - clear existing and add new"""

    # Clear existing academic years
    db_session.execute(delete(AcademicYear))

    # Generate academic years from 2000 to 2050
    academic_years = []
    for year in range(2000, 2051):
        # August 1 start date, May 31 end date (next year)
        start_date = datetime(
            year, 8, 1, 0, 0, 0
        )  # Remove timezone for MSSQL compatibility
        end_date = datetime(
            year + 1, 5, 31, 23, 59, 59
        )  # Remove timezone for MSSQL compatibility

        # Current academic year
        is_current = year == 2024

        academic_year = AcademicYear(
            id=str(uuid.uuid4()),
            year_code=year,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
        )
        academic_years.append(academic_year)

    db_session.add_all(academic_years)
    db_session.commit()
    logger.info(f"Seeded {len(academic_years)} academic years (2000-2050)")
