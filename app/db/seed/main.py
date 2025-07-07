from .seed_programs import seed_programs
from ..session import SessionLocal
from ...utils.logging import get_logger

logger = get_logger()


def seed_db():
    """Seed the database with initial data."""
    with SessionLocal.begin() as db_session:
        try:
            logger.info("Initiated database seeding process")
            seed_programs(db_session)
        except Exception as e:
            logger.error("Error occurred while seeding the database", exc_info=e)
