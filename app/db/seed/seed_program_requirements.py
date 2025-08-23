import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import (
    ProgramRequirement,
    Program,
    CertificateType,
    ProgReqRecurrenceType,
)
from app.utils.logging import get_logger

logger = get_logger()


async def seed_program_requirements(db_session: AsyncSession):
    # Get CS program
    cs_program_stmt = select(Program).where(Program.program_code == "CS")
    cs_program_result = await db_session.execute(cs_program_stmt)
    cs_program = cs_program_result.scalar_one_or_none()

    if not cs_program:
        logger.warning("CS program not found. Cannot seed program requirements.")
        return

    # Get CITI certificate type
    cert_type_stmt = select(CertificateType).where(
        CertificateType.cert_code == "citi_program_certificate"
    )
    cert_type_result = await db_session.execute(cert_type_stmt)
    cert_type = cert_type_result.scalar_one_or_none()

    if not cert_type:
        logger.warning(
            "CITI certificate type not found. Cannot seed program requirements."
        )
        return

    program_requirements_data = [
        {
            "id": uuid.uuid4(),
            "program_id": cs_program.id,
            "cert_type_id": cert_type.id,
            "name": "CITI Program Research Ethics Training",
            "target_year": 2,  # Second year requirement
            "deadline_month": 12,  # December
            "deadline_day": 30,  # 30th
            "is_mandatory": True,
            "special_instruction": "Complete the CITI Program training on research ethics and responsible conduct of research. This is required before participating in any research activities.",
            "is_active": True,
            "recurrence_type": ProgReqRecurrenceType.ANNUAL,
        },
    ]

    # Check if program requirements already exist to avoid duplicates
    existing_reqs_stmt = select(ProgramRequirement).where(
        ProgramRequirement.program_id == cs_program.id,
        ProgramRequirement.cert_type_id == cert_type.id,
    )
    existing_reqs_result = await db_session.execute(existing_reqs_stmt)
    existing_reqs = existing_reqs_result.scalars().all()

    requirements_to_add = []
    for req_data in program_requirements_data:
        # Check if this specific requirement already exists
        exists = any(
            req.name == req_data["name"] and req.target_year == req_data["target_year"]
            for req in existing_reqs
        )

        if not exists:
            requirement = ProgramRequirement(**req_data)
            requirements_to_add.append(requirement)

    if requirements_to_add:
        db_session.add_all(requirements_to_add)
        logger.info(
            f"Successfully seeded {len(requirements_to_add)} program requirements"
        )
    else:
        logger.info("No new program requirements to seed")
