import asyncio
from .models import Base
from .seeds.main import seed_all_data
from .session import async_engine

from app.utils.logging import get_logger

logger = get_logger()


async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Created all tables.")


async def drop_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Dropped all tables.")


async def seed_db():
    """Seed the database with initial data"""
    await seed_all_data()


async def reset_db():
    logger.info("Resetting database...")
    await drop_tables()
    await create_tables()
    await seed_db()
    logger.info("Database reset complete.")


if __name__ == "__main__":
    asyncio.run(reset_db())
