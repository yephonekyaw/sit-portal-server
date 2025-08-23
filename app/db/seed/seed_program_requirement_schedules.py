import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import (
    ProgramRequirementSchedule,
    ProgramRequirement,
    AcademicYear,
    Program,
    CertificateType,
)
from app.utils.logging import get_logger

logger = get_logger()


async def seed_program_requirement_schedules(db_session: AsyncSession):
    # First, ensure we have an academic year (create one if needed)
    current_year = datetime.now().year
    academic_year_code = current_year

    academic_year_stmt = select(AcademicYear).where(
        AcademicYear.year_code == academic_year_code
    )
    academic_year_result = await db_session.execute(academic_year_stmt)
    academic_year = academic_year_result.scalar_one_or_none()

    if not academic_year:
        # Create current academic year
        academic_year = AcademicYear(
            id=uuid.uuid4(),
            year_code=academic_year_code,
            start_date=datetime(current_year, 1, 1),
            end_date=datetime(current_year, 12, 31),
            is_current=True,
        )
        db_session.add(academic_year)
        await db_session.flush()  # Ensure the academic year is available for the next query
        logger.info(f"Created academic year {academic_year_code}")

    # Get CS program
    cs_program_stmt = select(Program).where(Program.program_code == "CS")
    cs_program_result = await db_session.execute(cs_program_stmt)
    cs_program = cs_program_result.scalar_one_or_none()

    if not cs_program:
        logger.warning(
            "CS program not found. Cannot seed program requirement schedules."
        )
        return

    # Get CITI certificate type
    cert_type_stmt = select(CertificateType).where(
        CertificateType.cert_code == "citi_program_certificate"
    )
    cert_type_result = await db_session.execute(cert_type_stmt)
    cert_type = cert_type_result.scalar_one_or_none()

    if not cert_type:
        logger.warning(
            "CITI certificate type not found. Cannot seed program requirement schedules."
        )
        return

    # Get the program requirement we created
    program_req_stmt = select(ProgramRequirement).where(
        ProgramRequirement.program_id == cs_program.id,
        ProgramRequirement.cert_type_id == cert_type.id,
        ProgramRequirement.name == "CITI Program Research Ethics Training",
    )
    program_req_result = await db_session.execute(program_req_stmt)
    program_requirement = program_req_result.scalar_one_or_none()

    if not program_requirement:
        logger.warning(
            "Program requirement not found. Cannot seed program requirement schedules."
        )
        return

    # Create schedule for the current academic year
    submission_deadline = datetime(
        current_year,
        program_requirement.deadline_month,
        program_requirement.deadline_day,
        23,
        59,
        59,  # End of day
    )

    schedule_data = {
        "id": uuid.uuid4(),
        "program_requirement_id": program_requirement.id,
        "academic_year_id": academic_year.id,
        "submission_deadline": submission_deadline,
    }

    # Check if schedule already exists to avoid duplicates
    existing_schedule_stmt = select(ProgramRequirementSchedule).where(
        ProgramRequirementSchedule.program_requirement_id == program_requirement.id,
        ProgramRequirementSchedule.academic_year_id == academic_year.id,
    )
    existing_schedule_result = await db_session.execute(existing_schedule_stmt)
    existing_schedule = existing_schedule_result.scalar_one_or_none()

    if not existing_schedule:
        schedule = ProgramRequirementSchedule(**schedule_data)
        db_session.add(schedule)
        logger.info(
            f"Successfully seeded program requirement schedule for {academic_year_code}"
        )
    else:
        logger.info(
            "Program requirement schedule already exists for this academic year"
        )
