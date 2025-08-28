import uuid
from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.db.models import Role
from app.utils.logging import get_logger

logger = get_logger()


def seed_roles(db_session: Session):
    """Sync version: Seed roles data - clear existing and add new"""

    # Clear existing roles
    db_session.execute(delete(Role))

    # Add roles
    roles = [
        Role(
            id=str(uuid.uuid4()),
            name="admin",
            description="Administrator role with full access",
        ),
    ]

    db_session.add_all(roles)
    db_session.commit()
    logger.info(f"Seeded {len(roles)} roles")
