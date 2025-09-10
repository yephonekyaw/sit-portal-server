"""
Main seeding file that orchestrates all database seeding operations.

Runs seeding functions in the correct dependency order to ensure
referential integrity is maintained.
"""

from app.db.session import SessionLocal
from app.utils.logging import get_logger

# Import all seeding functions
from .programs_seed import seed_programs
from .academic_years_seed import seed_academic_years
from .certificate_types_seed import seed_certificate_types
from .program_requirements_seed import seed_program_requirements
from .program_requirement_schedules_seed import seed_program_requirement_schedules
from .dashboard_stats_seed import seed_dashboard_stats
from .notification_types_seed import seed_notification_types
from .notification_channel_templates_seed import seed_notification_channel_templates
from .roles_seed import seed_roles
from .permissions_seed import seed_permissions
from .users_students_seed import seed_users_students
from .usres_staff_seed import seed_users_staff
from .staff_permissions_seed import seed_staff_permissions

logger = get_logger()


def seed_all_data():
    """
    Sync version: Seed all database tables in the correct dependency order.

    Order matters due to foreign key relationships:
    1. Independent tables first (programs, academic_years, certificate_types, etc.)
    2. Tables that depend on others (users_students, permissions, etc.)
    3. Junction/relationship tables last (staff_permissions, etc.)
    """

    db_session = SessionLocal()
    try:
        logger.info("Starting database seeding...")

        # Phase 1: Independent tables
        logger.info("Phase 1: Seeding independent tables...")
        seed_programs(db_session)
        seed_academic_years(db_session)
        seed_certificate_types(db_session)
        seed_notification_types(db_session)
        seed_roles(db_session)

        # Phase 2: Tables with single dependencies
        logger.info("Phase 2: Seeding dependent tables...")
        seed_program_requirements(db_session)  # Depends on programs + certificate_types
        seed_program_requirement_schedules(
            db_session
        )  # Depends on program_requirements + academic_years
        seed_notification_channel_templates(db_session)
        seed_permissions(db_session)  # Depends on programs + roles
        seed_users_students(db_session)  # Depends on programs + academic_years
        seed_users_staff(db_session)  # Creates staff users

        # Phase 3: Junction/relationship tables
        logger.info("Phase 3: Seeding relationship tables...")
        seed_staff_permissions(db_session)  # Depends on staff + permissions

        # Phase 4: Tables that depend on multiple others
        logger.info("Phase 4: Seeding complex dependent tables...")
        seed_dashboard_stats(
            db_session
        )  # Depends on program_requirement_schedules, programs, certificate_types + academic_years

        logger.info("Database seeding completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Database seeding failed: {str(e)}")
        db_session.rollback()
        raise e
    finally:
        db_session.close()
