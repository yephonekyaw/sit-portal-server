from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import Role, Program, Permission
from ...utils.logging import get_logger

logger = get_logger()


async def seed_permissions(db_session: AsyncSession):
    admin_role_stmt = select(Role).where(Role.name == "admin")
    programs_stmt = select(Program).where(Program.program_code.in_(["CS", "DSI", "IT"]))

    admin_role_result = await db_session.execute(admin_role_stmt)
    programs_result = await db_session.execute(programs_stmt)

    admin_role = admin_role_result.scalar_one_or_none()
    programs = programs_result.scalars().all()

    if not admin_role:
        logger.warning("Admin role not found, skipping permission seeding.")
        return

    if not programs:
        logger.warning("Programs not found, skipping permission seeding.")
        return

    # Check for existing permissions
    existing_permissions_stmt = select(Permission).where(
        Permission.role_id == admin_role.id
    )
    existing_permissions_result = await db_session.execute(existing_permissions_stmt)
    existing_permissions = {
        p.program_id for p in existing_permissions_result.scalars().all()
    }

    permissions_to_add = []
    for program in programs:
        if program.id not in existing_permissions:
            permission = Permission(role_id=admin_role.id, program_id=program.id)
            permissions_to_add.append(permission)

    if permissions_to_add:
        db_session.add_all(permissions_to_add)
        logger.info(f"Successfully seeded {len(permissions_to_add)} permissions")
    else:
        logger.info("No new permissions to seed")
