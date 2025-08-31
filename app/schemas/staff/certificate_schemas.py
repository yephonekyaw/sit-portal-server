from datetime import datetime
from pydantic import Field
import uuid

from app.schemas.camel_base_model import CamelCaseBaseModel as BaseModel


class GetCertificatesItem(BaseModel):
    """Response schema for certificate type with counts"""

    id: uuid.UUID = Field(..., description="Certificate type ID")
    cert_code: str = Field(..., description="Certificate type code")
    cert_name: str = Field(..., description="Certificate type name")
    description: str = Field(..., description="Certificate type description")
    verification_template: str = Field(..., description="Verification template")
    has_expiration: bool = Field(..., description="Whether certificate has expiration")
    is_active: bool = Field(..., description="Whether certificate type is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Count fields
    active_requirements_count: int = Field(
        ..., description="Count of active requirements using this certificate"
    )
    archived_requirements_count: int = Field(
        ..., description="Count of archived requirements using this certificate"
    )
    total_submissions_count: int = Field(
        ..., description="Total submissions for this certificate type"
    )


class UpdateCertificateRequest(BaseModel):
    """Request schema for updating a certificate type"""

    id: uuid.UUID = Field(..., description="Certificate type ID")
    cert_code: str = Field(
        ..., min_length=1, max_length=50, description="Certificate type code"
    )
    cert_name: str = Field(
        ..., min_length=1, max_length=200, description="Certificate type name"
    )
    description: str = Field(
        ..., min_length=1, description="Certificate type description"
    )
    verification_template: str = Field(
        ..., min_length=1, description="Verification template"
    )
    has_expiration: bool = Field(..., description="Whether certificate has expiration")


class CertificateResponse(UpdateCertificateRequest):
    """Response schema for certificate type archive operation"""
