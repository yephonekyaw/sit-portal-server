import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select

from app.db.models import StaffPermission, Staff, Permission, User
from app.utils.logging import get_logger

logger = get_logger()


async def seed_staff_permissions(db_session: AsyncSession):
    """Seed staff permissions data - clear existing and add new"""

    # Clear existing staff permissions
    await db_session.execute(delete(StaffPermission))
    await db_session.commit()

    # Get Julian San's staff record
    staff_result = await db_session.execute(
        select(Staff).join(User).where(User.username == "julian.san")
    )
    staff = staff_result.scalar_one_or_none()
    if not staff:
        logger.error("Staff Julian San not found")
        return

    # Get all permissions
    permissions_result = await db_session.execute(select(Permission))
    permissions = permissions_result.scalars().all()

    if not permissions:
        logger.error("No permissions found")
        return

    staff_permissions = []

    # Assign all permissions to Julian San
    for permission in permissions:
        staff_permission = StaffPermission(
            id=uuid.uuid4(),
            staff_id=staff.id,
            permission_id=permission.id,
            is_active=True,
            assigned_by=None,  # System assigned
            assigned_at=datetime.now(timezone.utc),
            expires_at=None,  # Never expires
        )
        staff_permissions.append(staff_permission)

    db_session.add_all(staff_permissions)
    await db_session.commit()
    logger.info(f"Seeded {len(staff_permissions)} staff permissions for Julian San")
