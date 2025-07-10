import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import Role
from ...utils.logging import get_logger

logger = get_logger()


async def seed_roles(db_session: AsyncSession):
    roles_data = [
        {
            "id": uuid.uuid4(),
            "name": "admin",
            "description": "Administrator role with full access",
        },
    ]

    stmt = select(Role.name)
    result = await db_session.execute(stmt)
    existing_roles = {row[0] for row in result.fetchall()}

    roles_to_add = []
    for role_data in roles_data:
        if role_data["name"] not in existing_roles:
            role = Role(**role_data)
            roles_to_add.append(role)

    if roles_to_add:
        db_session.add_all(roles_to_add)
        logger.info(f"Successfully seeded {len(roles_to_add)} roles")
    else:
        logger.info("No new roles to seed")
