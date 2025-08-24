import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.db.models import User, Staff, UserType
from app.utils.logging import get_logger

logger = get_logger()


async def seed_users_staff(db_session: AsyncSession):
    """Seed staff data - clear existing and add new"""

    # Clear existing staff and their users
    await db_session.execute(delete(Staff))
    # Note: Users will be cleared by the users_students_seed, so we only clear staff here
    await db_session.commit()

    # Create staff user and staff record
    user_id = uuid.uuid4()

    # Create user
    user = User(
        id=user_id,
        username="julian.san",
        first_name="Julian",
        last_name="San",
        user_type=UserType.STAFF,
        is_active=True,
        access_token_version=0,
    )

    # Create staff
    staff = Staff(
        id=uuid.uuid4(),
        user_id=user_id,
        employee_id="10000000000",
        department="Computer Science",
    )

    db_session.add(user)
    db_session.add(staff)
    await db_session.commit()
    logger.info("Seeded 1 staff member: Julian San (Computer Science)")
