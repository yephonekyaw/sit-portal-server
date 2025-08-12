from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Request, status, Path

from app.services.certificate_service import CertificateServiceProvider, get_certificate_service
from app.schemas.staff.certificate_schemas import UpdateCertificateTypeRequest
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError

certificates_router = APIRouter()


def handle_service_error(request: Request, error: Exception):
    """Handle service errors and return appropriate error response"""
    error_message = str(error)

    # Handle certificate with active requirements (special case)
    if error_message.startswith("CERTIFICATE_TYPE_HAS_ACTIVE_REQUIREMENTS:"):
        requirement_details = error_message.split(": ", 1)[1]
        return ResponseBuilder.error(
            request=request,
            message=f"Cannot archive certificate type. {requirement_details}. Please archive these requirements individually first.",
            error_code="CERTIFICATE_TYPE_HAS_ACTIVE_REQUIREMENTS",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # For standard error codes, map to appropriate status codes
    error_status_mapping = {
        "CERTIFICATE_TYPE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CERTIFICATE_CODE_EXISTS": status.HTTP_409_CONFLICT,
        "CERTIFICATE_TYPE_ALREADY_ARCHIVED": status.HTTP_400_BAD_REQUEST,
    }

    status_code = error_status_mapping.get(
        error_message, status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    # Map error codes to user-friendly messages
    error_messages = {
        "CERTIFICATE_TYPE_NOT_FOUND": "Certificate type not found",
        "CERTIFICATE_CODE_EXISTS": "Certificate type with this code already exists",
        "CERTIFICATE_TYPE_ALREADY_ARCHIVED": "Certificate type is already archived",
        "CERTIFICATE_TYPE_UPDATE_FAILED": "Failed to update certificate type",
        "CERTIFICATE_TYPE_ARCHIVE_FAILED": "Failed to archive certificate type",
        "CERTIFICATE_TYPES_RETRIEVAL_FAILED": "Failed to retrieve certificate types",
    }

    message = error_messages.get(error_message, "An unexpected error occurred")

    return ResponseBuilder.error(
        request=request,
        message=message,
        error_code=error_message,
        status_code=status_code,
    )


# API Endpoints
@certificates_router.get(
    "/",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Get all certificate types with counts",
    description="Retrieve all certificate types with their basic information and counts of active/archived requirements and total submissions",
)
async def get_all_certificate_types(
    request: Request,
    certificate_service: CertificateServiceProvider = Depends(get_certificate_service),
):
    """Get all certificate types with requirement and submission counts"""
    try:
        certificates_list = await certificate_service.get_all_certificates_with_counts()

        return ResponseBuilder.success(
            request=request,
            data=certificates_list,
            message=f"Retrieved {len(certificates_list)} certificate type{'s' if len(certificates_list) != 1 else ''}",
            status_code=status.HTTP_200_OK,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception:
        raise BusinessLogicError(
            message="Failed to retrieve certificate types",
            error_code="CERTIFICATE_TYPES_RETRIEVAL_FAILED",
        )


@certificates_router.put(
    "/{certificate_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Update a certificate type",
    description="Update certificate type fields while preserving the REQUIRED_DATA_INPUT section of the verification template",
)
async def update_certificate_type(
    request: Request,
    certificate_id: Annotated[uuid.UUID, Path(description="Certificate type ID to update")],
    certificate_data: UpdateCertificateTypeRequest,
    certificate_service: CertificateServiceProvider = Depends(get_certificate_service),
):
    """Update a certificate type with template section preservation"""
    try:
        response_data = await certificate_service.update_certificate(
            certificate_id, certificate_data
        )

        return ResponseBuilder.success(
            request=request,
            data=response_data,
            message="Certificate type updated successfully",
            status_code=status.HTTP_200_OK,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception:
        raise BusinessLogicError(
            message="Failed to update certificate type",
            error_code="CERTIFICATE_TYPE_UPDATE_FAILED",
        )


@certificates_router.patch(
    "/{certificate_id}/archive",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Archive a certificate type",
    description="Archive a certificate type and all its active requirements. Returns count of archived requirements.",
)
async def archive_certificate_type(
    request: Request,
    certificate_id: Annotated[uuid.UUID, Path(description="Certificate type ID to archive")],
    certificate_service: CertificateServiceProvider = Depends(get_certificate_service),
):
    """Archive a certificate type and all its active requirements"""
    try:
        response_data = await certificate_service.archive_certificate(certificate_id)
        archived_count = response_data["archived_requirements_count"]
        message = CertificateServiceProvider.build_archive_message(archived_count)

        return ResponseBuilder.success(
            request=request,
            data=response_data,
            message=message,
            status_code=status.HTTP_200_OK,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception:
        raise BusinessLogicError(
            message="Failed to archive certificate type",
            error_code="CERTIFICATE_TYPE_ARCHIVE_FAILED",
        )