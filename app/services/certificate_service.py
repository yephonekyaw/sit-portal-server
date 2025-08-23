from typing import Optional, List, Dict, Any
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, and_

from app.utils.logging import get_logger
from app.db.models import CertificateType, ProgramRequirement, CertificateSubmission
from app.db.session import get_async_session
from app.schemas.staff.certificate_schemas import (
    UpdateCertificateTypeRequest,
    CertificateTypeResponse,
)

logger = get_logger()


class CertificateServiceProvider:
    """Service provider for certificate-related business logic and database operations"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # Core CRUD Operations
    async def get_certificate_by_id(
        self, certificate_id: uuid.UUID
    ) -> Optional[CertificateType]:
        """Get certificate by ID or return None if not found"""
        result = await self.db.execute(
            select(CertificateType).where(CertificateType.id == certificate_id)
        )
        return result.scalar_one_or_none()

    async def check_certificate_code_exists(
        self, code: str, exclude_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Check if certificate code already exists (optionally excluding a specific ID)"""
        query = select(CertificateType).where(CertificateType.cert_code == code)
        if exclude_id:
            query = query.where(CertificateType.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_all_certificates_with_counts(self) -> List[Dict[str, Any]]:
        """Get all certificate types with requirement and submission counts"""
        try:
            # Build query with counts
            query = self._build_certificates_query_with_counts()

            # Execute query
            result = await self.db.execute(query)
            certificates_data = result.all()

            # Transform to response models
            certificates_list = []
            for row in certificates_data:
                certificate_item = CertificateTypeResponse(
                    id=row.id,
                    cert_code=row.cert_code,
                    cert_name=row.cert_name,
                    description=row.description,
                    verification_template=row.verification_template,
                    has_expiration=row.has_expiration,
                    is_active=row.is_active,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    active_requirements_count=row.active_requirements_count,
                    archived_requirements_count=row.archived_requirements_count,
                    total_submissions_count=row.total_submissions_count,
                )
                certificates_list.append(certificate_item.model_dump())

            return certificates_list

        except Exception as e:
            logger.error(f"Failed to retrieve certificates: {str(e)}")
            raise RuntimeError("CERTIFICATE_TYPES_RETRIEVAL_FAILED")

    async def update_certificate(
        self, certificate_id: uuid.UUID, certificate_data: UpdateCertificateTypeRequest
    ) -> Dict[str, Any]:
        """Update an existing certificate with template section preservation"""
        # Check if certificate exists
        certificate = await self.get_certificate_by_id(certificate_id)
        if not certificate:
            raise ValueError("CERTIFICATE_TYPE_NOT_FOUND")

        # Check if another certificate already has this code (excluding current certificate)
        if certificate_data.cert_code != certificate.cert_code:
            if await self.check_certificate_code_exists(
                certificate_data.cert_code, exclude_id=certificate_id
            ):
                raise ValueError("CERTIFICATE_CODE_EXISTS")

        try:
            # Preserve REQUIRED_DATA_INPUT section in verification template
            updated_template = self._preserve_required_data_input_section(
                certificate_data.verification_template,
                certificate.verification_template,
            )

            # Update certificate fields
            certificate.cert_code = certificate_data.cert_code
            certificate.cert_name = certificate_data.cert_name
            certificate.description = certificate_data.description
            certificate.verification_template = updated_template

            await self.db.commit()
            await self.db.refresh(certificate)

            logger.info(f"Updated certificate: {certificate.cert_code}")
            return {
                "id": str(certificate.id),
                "cert_code": certificate.cert_code,
                "cert_name": certificate.cert_name,
            }

        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(f"Integrity error updating certificate: {str(e)}")
            raise ValueError("CERTIFICATE_CODE_EXISTS")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update certificate {certificate_id}: {str(e)}")
            raise RuntimeError("CERTIFICATE_TYPE_UPDATE_FAILED")

    async def archive_certificate(self, certificate_id: uuid.UUID) -> Dict[str, Any]:
        """Archive a certificate only if it has no active requirements"""
        # Check if certificate exists
        certificate = await self.get_certificate_by_id(certificate_id)
        if not certificate:
            raise ValueError("CERTIFICATE_TYPE_NOT_FOUND")

        # Check if certificate is already archived
        if not certificate.is_active:
            raise ValueError("CERTIFICATE_TYPE_ALREADY_ARCHIVED")

        try:
            # Check if certificate has any active requirements
            active_requirements_result = await self.db.execute(
                select(func.count(ProgramRequirement.id)).where(
                    and_(
                        ProgramRequirement.cert_type_id == certificate_id,
                        ProgramRequirement.is_active.is_(True),
                    )
                )
            )
            active_requirements_count = active_requirements_result.scalar()

            # Prevent archiving if there are active requirements
            if active_requirements_count is not None and active_requirements_count > 0:
                raise ValueError(
                    f"CERTIFICATE_TYPE_HAS_ACTIVE_REQUIREMENTS: {active_requirements_count} active requirement{'s' if active_requirements_count != 1 else ''} must be archived first"
                )

            # Archive the certificate (no requirements to archive)
            certificate.is_active = False

            await self.db.commit()
            await self.db.refresh(certificate)

            logger.info(f"Archived certificate {certificate.cert_code}")

            return {
                "certificate": {
                    "id": str(certificate.id),
                    "cert_code": certificate.cert_code,
                    "cert_name": certificate.cert_name,
                },
                "archived_requirements_count": 0,
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to archive certificate {certificate_id}: {str(e)}")
            raise RuntimeError("CERTIFICATE_TYPE_ARCHIVE_FAILED")

    # Helper Methods
    def _build_certificates_query_with_counts(self):
        """Build optimized query for certificates with requirement and submission counts"""
        # Subquery for active requirements count
        active_req_subquery = (
            select(
                ProgramRequirement.cert_type_id,
                func.count(ProgramRequirement.id).label("active_count"),
            )
            .where(ProgramRequirement.is_active.is_(True))
            .group_by(ProgramRequirement.cert_type_id)
            .subquery()
        )

        # Subquery for archived requirements count
        archived_req_subquery = (
            select(
                ProgramRequirement.cert_type_id,
                func.count(ProgramRequirement.id).label("archived_count"),
            )
            .where(ProgramRequirement.is_active.is_(False))
            .group_by(ProgramRequirement.cert_type_id)
            .subquery()
        )

        # Subquery for total submissions count
        submissions_subquery = (
            select(
                CertificateSubmission.cert_type_id,
                func.count(CertificateSubmission.id).label("submissions_count"),
            )
            .group_by(CertificateSubmission.cert_type_id)
            .subquery()
        )

        # Main query with all counts
        return (
            select(
                CertificateType.id,
                CertificateType.cert_code,
                CertificateType.cert_name,
                CertificateType.description,
                CertificateType.verification_template,
                CertificateType.has_expiration,
                CertificateType.is_active,
                CertificateType.created_at,
                CertificateType.updated_at,
                func.coalesce(active_req_subquery.c.active_count, 0).label(
                    "active_requirements_count"
                ),
                func.coalesce(archived_req_subquery.c.archived_count, 0).label(
                    "archived_requirements_count"
                ),
                func.coalesce(submissions_subquery.c.submissions_count, 0).label(
                    "total_submissions_count"
                ),
            )
            .outerjoin(
                active_req_subquery,
                CertificateType.id == active_req_subquery.c.cert_type_id,
            )
            .outerjoin(
                archived_req_subquery,
                CertificateType.id == archived_req_subquery.c.cert_type_id,
            )
            .outerjoin(
                submissions_subquery,
                CertificateType.id == submissions_subquery.c.cert_type_id,
            )
            .order_by(CertificateType.created_at.asc())
        )

    def _preserve_required_data_input_section(
        self, new_template: str, current_template: str
    ) -> str:
        """
        Preserve the REQUIRED_DATA_INPUT section from the current template
        and combine it with the updated template content.
        """
        required_data_marker = "**REQUIRED_DATA_INPUT:**"

        if required_data_marker in current_template:
            # Extract the REQUIRED_DATA_INPUT section from current template
            current_parts = current_template.split(required_data_marker, 1)
            required_data_section = required_data_marker + current_parts[1]
        else:
            # If no REQUIRED_DATA_INPUT section exists, return new template as-is
            return new_template

        # Remove any REQUIRED_DATA_INPUT section from the new template
        if required_data_marker in new_template:
            new_parts = new_template.split(required_data_marker, 1)
            new_template_without_required_data = new_parts[0].rstrip()
        else:
            new_template_without_required_data = new_template.rstrip()

        # Combine the new template with the preserved REQUIRED_DATA_INPUT section
        return new_template_without_required_data + "\n\n" + required_data_section

    @staticmethod
    def build_archive_message(archived_requirements_count: int) -> str:
        """Build archive success message with requirement count"""
        return "Certificate type archived successfully"


# Dependency injection for service provider
def get_certificate_service(
    db: AsyncSession = Depends(get_async_session),
) -> CertificateServiceProvider:
    """Dependency to provide CertificateServiceProvider instance"""
    return CertificateServiceProvider(db)
