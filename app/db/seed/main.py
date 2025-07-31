from .seed_programs import seed_programs
from .seed_certificate_types import seed_certificate_types
from .seed_notification_types import seed_notification_types
from .seed_notification_channel_templates import seed_notification_channel_templates
from .seed_roles import seed_roles
from .seed_permissions import seed_permissions
from .seed_program_requirements import seed_program_requirements
from .seed_program_requirement_schedules import seed_program_requirement_schedules
from ..session import AsyncSessionLocal
from ...utils.logging import get_logger

logger = get_logger()


async def seed_db():
    """Seed the database with initial data."""
    async with AsyncSessionLocal.begin() as db_session:
        try:
            logger.info("Initiated database seeding process")
            # No foreign key dependencies
            await seed_programs(db_session)
            await seed_certificate_types(db_session)
            await seed_notification_types(db_session)
            await seed_roles(db_session)

            # One foreign key dependency
            await seed_notification_channel_templates(db_session)

            # Two foreign key dependencies
            await seed_permissions(db_session)
            await seed_program_requirements(db_session)

            # Three foreign key dependencies (depends on program_requirements and academic_years)
            await seed_program_requirement_schedules(db_session)
        except Exception as e:
            logger.error("Error occurred while seeding the database", exc_info=e)
            await db_session.rollback()
            raise
