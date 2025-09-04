import uuid
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import delete, select

from app.db.models import (
    ProgramRequirement,
    Program,
    CertificateType,
    ProgReqRecurrenceType,
)
from app.utils.logging import get_logger

logger = get_logger()


def seed_program_requirements(db_session: Session):
    """Sync version: Seed program requirements data - clear existing and add new"""

    # Clear existing program requirements
    db_session.execute(delete(ProgramRequirement))

    # Get Bc.CS program
    program_stmt = select(Program).where(Program.program_code == "Bc.CS")
    program_result = db_session.execute(program_stmt)
    bccs_program = program_result.scalar_one_or_none()

    if not bccs_program:
        logger.error("Bc.CS program not found. Make sure programs are seeded first.")
        return

    # Get CITI Program certificate type
    cert_type_stmt = select(CertificateType).where(
        CertificateType.cert_code == "citi_program_certificate"
    )
    cert_type_result = db_session.execute(cert_type_stmt)
    citi_cert_type = cert_type_result.scalar_one_or_none()

    if not citi_cert_type:
        logger.error(
            "CITI Program certificate type not found. Make sure certificate types are seeded first."
        )
        return

    # Add program requirements
    program_requirements = [
        ProgramRequirement(
            id=str(uuid.uuid4()),
            program_id=bccs_program.id,
            cert_type_id=citi_cert_type.id,
            name="CITI Responsible Conduct of Research",
            target_year=3,
            deadline_date=date(2000, 11, 30),  # Year 2000 as template, month 11, day 30
            grace_period_days=7,
            is_mandatory=True,
            special_instruction=(
                "Complete the CITI Responsible Conduct of Research training modules. "
                "This training covers research ethics, data management, publication practices, "
                "and responsible authorship. Ensure you download and submit the completion "
                "certificate in PDF format upon finishing all required modules."
            ),
            is_active=True,
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=90,
            effective_from_year=2023,
            effective_until_year=2030,
            months_before_deadline=1,
        ),
    ]

    db_session.add_all(program_requirements)
    db_session.commit()
    logger.info(f"Seeded {len(program_requirements)} program requirements")
