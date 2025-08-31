import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import delete, select

from app.db.models import StaffPermission, Staff, Permission, User
from app.utils.logging import get_logger

logger = get_logger()


def seed_staff_permissions(db_session: Session):
    """Sync version: Seed staff permissions data - clear existing and add new"""

    # Clear existing staff permissions
    db_session.execute(delete(StaffPermission))
    db_session.commit()

    # Get CSCMS staff record
    staff_result = db_session.execute(
        select(Staff).join(User).where(User.username == "cscms")
    )
    staff = staff_result.scalar_one_or_none()
    if not staff:
        logger.error("Staff CSCMS not found")
        return

    # Get all permissions
    permissions_result = db_session.execute(select(Permission))
    permissions = permissions_result.scalars().all()

    if not permissions:
        logger.error("No permissions found")
        return

    staff_permissions = []

    # Assign all permissions to CSCMS
    for permission in permissions:
        staff_permission = StaffPermission(
            id=str(uuid.uuid4()),
            staff_id=staff.id,
            permission_id=permission.id,
            is_active=True,
            assigned_by=None,  # System assigned
            assigned_at=datetime.now(),
            expires_at=None,  # Never expires
        )
        staff_permissions.append(staff_permission)

    db_session.add_all(staff_permissions)
    db_session.commit()
    logger.info(f"Seeded {len(staff_permissions)} staff permissions for CSCMS")
