import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.db.models import Program
from app.utils.logging import get_logger

logger = get_logger()


async def seed_programs(db_session: AsyncSession):
    """Seed programs data - clear existing and add new"""

    # Clear existing programs
    await db_session.execute(delete(Program))

    # Add new programs
    programs = [
        Program(
            id=uuid.uuid4(),
            program_code="Bc.CS",
            program_name="Bachelor of Computer Science",
            description="A comprehensive Bachelor's program focusing on computer science fundamentals, software development, algorithms, data structures, and computational theory.",
            duration_years=4,
            is_active=True,
        ),
        Program(
            id=uuid.uuid4(),
            program_code="Bc.DSI",
            program_name="Bachelor of Digital Service Innovation",
            description="An innovative Bachelor's program that combines technology, design thinking, and business strategy to create digital solutions for real-world problems.",
            duration_years=4,
            is_active=True,
        ),
        Program(
            id=uuid.uuid4(),
            program_code="Bc.IT",
            program_name="Bachelor of Information Technology",
            description="A practical Bachelor's program focused on the application of technology in business environments.",
            duration_years=4,
            is_active=True,
        ),
    ]

    db_session.add_all(programs)
    await db_session.commit()
    logger.info(f"Seeded {len(programs)} programs")
