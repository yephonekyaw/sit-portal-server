from .models import Base
from .seed.main import seed_db
from .session import engine


def create_tables():
    Base.metadata.create_all(bind=engine)


def drop_tables():
    Base.metadata.drop_all(bind=engine)


if __name__ == "__main__":
    # create_tables()
    # seed_db()
    # drop_tables()
    pass
