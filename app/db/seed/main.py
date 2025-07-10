from .seed_programs import seed_programs
from ..session import AsyncSessionLocal
from ...utils.logging import get_logger

logger = get_logger()


async def seed_db():
    """Seed the database with initial data."""
    async with AsyncSessionLocal() as db_session:
        try:
            logger.info("Initiated database seeding process")
            await seed_programs(db_session)
        except Exception as e:
            logger.error("Error occurred while seeding the database", exc_info=e)
            await db_session.rollback()
            raise
