import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select

from app.db.models import Permission, Program, Role
from app.utils.logging import get_logger

logger = get_logger()


async def seed_permissions(db_session: AsyncSession):
    """Seed permissions data - clear existing and add new"""

    # Clear existing permissions
    await db_session.execute(delete(Permission))
    await db_session.commit()

    # Get all programs
    programs_result = await db_session.execute(select(Program))
    programs = {p.program_code: p for p in programs_result.scalars().all()}

    # Get all roles
    roles_result = await db_session.execute(select(Role))
    roles = {r.name: r for r in roles_result.scalars().all()}

    if not programs:
        logger.error("No programs found")
        return

    if not roles:
        logger.error("No roles found")
        return

    permissions = []

    # Create permissions for each program-role combination
    for program_code, program in programs.items():
        for role_name, role in roles.items():
            permission = Permission(
                id=uuid.uuid4(),
                program_id=program.id,
                role_id=role.id,
            )
            permissions.append(permission)

    db_session.add_all(permissions)
    await db_session.commit()
    logger.info(
        f"Seeded {len(permissions)} permissions ({len(programs)} programs & {len(roles)} roles)"
    )
