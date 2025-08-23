import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.db.models import Role
from app.utils.logging import get_logger

logger = get_logger()


async def seed_roles(db_session: AsyncSession):
    """Seed roles data - clear existing and add new"""

    # Clear existing roles
    await db_session.execute(delete(Role))

    # Add roles
    roles = [
        Role(
            id=uuid.uuid4(),
            name="admin",
            description="Administrator role with full access",
        ),
    ]

    db_session.add_all(roles)
    await db_session.commit()
    logger.info(f"Seeded {len(roles)} roles")