from .models import Base
from .seeds.main import seed_all_data
from .session import engine

from app.utils.logging import get_logger

logger = get_logger()


def create_tables():
    Base.metadata.create_all(engine)
    logger.info("Created all tables.")


def drop_tables():
    Base.metadata.drop_all(engine)
    logger.info("Dropped all tables.")


def seed_db():
    """Seed the database with initial data"""
    seed_all_data()


def reset_db():
    logger.info("Resetting database...")
    drop_tables()
    create_tables()
    seed_db()
    logger.info("Database reset complete.")


if __name__ == "__main__":
    reset_db()
