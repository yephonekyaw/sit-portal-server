from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import CertificateType
from app.templates.citi_program_template import citi_program_verification_template

from app.utils.logging import get_logger

logger = get_logger()


async def seed_certificate_types(db_session: AsyncSession):
    certificate_types = [
        {
            "cert_code": "citi_program_certificate",
            "cert_name": "CITI Program Certificate",
            "description": "Certificate for CITI Program courses.",
            "verification_template": citi_program_verification_template,
            "has_expiration": False,
        },
    ]

    existing_certificates = select(CertificateType.cert_code)
    existing_codes_result = await db_session.execute(existing_certificates)
    existing_codes = {code for code, in existing_codes_result.fetchall()}

    certificates_types_to_add = []
    for cert_type in certificate_types:
        if cert_type["code"] not in existing_codes:
            certificate_type = CertificateType(**cert_type)
            certificates_types_to_add.append(certificate_type)

    if certificates_types_to_add:
        db_session.add_all(certificates_types_to_add)
        logger.info(f"Seeded {len(certificates_types_to_add)} certificate types.")
    else:
        logger.info("No new certificate types to seed.")
