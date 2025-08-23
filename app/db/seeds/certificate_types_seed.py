import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.db.models import CertificateType
from app.templates.citi_program_template import citi_program_verification_template
from app.utils.logging import get_logger

logger = get_logger()


async def seed_certificate_types(db_session: AsyncSession):
    """Seed certificate types data - clear existing and add new"""

    # Clear existing certificate types
    await db_session.execute(delete(CertificateType))

    # Add certificate types
    certificate_types = [
        CertificateType(
            id=uuid.uuid4(),
            cert_code="citi_program_certificate",
            cert_name="CITI Program Certificate",
            description="Certificate for CITI Program courses.",
            verification_template=citi_program_verification_template,
            has_expiration=False,
            is_active=True,
        ),
    ]

    db_session.add_all(certificate_types)
    await db_session.commit()
    logger.info(f"Seeded {len(certificate_types)} certificate types")