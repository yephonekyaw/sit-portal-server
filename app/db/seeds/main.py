"""
Main seeding file that orchestrates all database seeding operations.

Runs seeding functions in the correct dependency order to ensure
referential integrity is maintained.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.utils.logging import get_logger

# Import all seeding functions
from .programs_seed import seed_programs
from .academic_years_seed import seed_academic_years
from .certificate_types_seed import seed_certificate_types
from .notification_types_seed import seed_notification_types
from .notification_channel_templates_seed import seed_notification_channel_templates
from .roles_seed import seed_roles
from .permissions_seed import seed_permissions
from .users_students_seed import seed_users_students
from .usres_staff_seed import seed_users_staff
from .staff_permissions_seed import seed_staff_permissions

logger = get_logger()


async def seed_all_data():
    """
    Seed all database tables in the correct dependency order.

    Order matters due to foreign key relationships:
    1. Independent tables first (programs, academic_years, certificate_types, etc.)
    2. Tables that depend on others (users_students, permissions, etc.)
    3. Junction/relationship tables last (staff_permissions, etc.)
    """

    async for db_session in get_async_session():
        try:
            logger.info("Starting database seeding...")

            # Phase 1: Independent tables
            logger.info("Phase 1: Seeding independent tables...")
            await seed_programs(db_session)
            await seed_academic_years(db_session)
            await seed_certificate_types(db_session)
            await seed_notification_types(db_session)
            await seed_roles(db_session)

            # Phase 2: Tables with single dependencies
            logger.info("Phase 2: Seeding dependent tables...")
            await seed_notification_channel_templates(db_session)
            await seed_permissions(db_session)  # Depends on programs + roles
            await seed_users_students(
                db_session
            )  # Depends on programs + academic_years
            await seed_users_staff(db_session)  # Creates staff users

            # Phase 3: Junction/relationship tables
            logger.info("Phase 3: Seeding relationship tables...")
            await seed_staff_permissions(db_session)  # Depends on staff + permissions

            logger.info("Database seeding completed successfully!")
            return True

        except Exception as e:
            logger.error(f"Database seeding failed: {str(e)}")
            await db_session.rollback()
            raise e
        finally:
            await db_session.close()
        break


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_all_data())
