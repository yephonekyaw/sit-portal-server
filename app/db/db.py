from .models import Base
from .seed.main import seed_db
from .session import engine

from app.utils.logging import get_logger

logger = get_logger()


def create_tables():
    Base.metadata.create_all(bind=engine)
    logger.info("Created all tables.")


def drop_tables():
    Base.metadata.drop_all(bind=engine)
    logger.info("Dropped all tables.")


if __name__ == "__main__":
    create_tables()
    seed_db()
    # drop_tables()
    pass
