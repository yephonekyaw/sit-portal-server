from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Request, status, Query, Path

from app.services.staff.submission_service import (
    SubmissionService,
    get_submission_service,
)
from app.schemas.staff.certificate_submission_schemas import (
    CertificateSubmissionsListResponse,
    VerificationHistoryListResponse,
)
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError

submissions_router = APIRouter()


def handle_service_error(request: Request, error: Exception):
    """Handle service errors and return appropriate error response"""
    error_message = str(error)

    # Extract the actual error code if it follows the pattern "ERROR_CODE: message"
    if ":" in error_message:
        error_code = error_message.split(":", 1)[0]
    else:
        error_code = error_message

    # For standard error codes, map to appropriate status codes
    error_status_mapping = {
        "CERTIFICATE_SUBMISSIONS_RETRIEVAL_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "VERIFICATION_HISTORY_RETRIEVAL_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "CERTIFICATE_SUBMISSION_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "INVALID_YEAR_CODE": status.HTTP_400_BAD_REQUEST,
    }

    status_code = error_status_mapping.get(
        error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    # Map error codes to user-friendly messages
    error_messages = {
        "CERTIFICATE_SUBMISSIONS_RETRIEVAL_FAILED": "Failed to retrieve certificate submissions",
        "VERIFICATION_HISTORY_RETRIEVAL_FAILED": "Failed to retrieve verification history",
        "CERTIFICATE_SUBMISSION_NOT_FOUND": "Certificate submission not found",
        "INVALID_YEAR_CODE": "Invalid academic year code provided",
    }

    message = error_messages.get(error_code, "An unexpected error occurred")

    return ResponseBuilder.error(
        request=request,
        message=message,
        error_code=error_code,
        status_code=status_code,
    )


@submissions_router.get(
    "/certificates",
    response_model=CertificateSubmissionsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get certificate submissions by year",
    description="Retrieve certificate submissions for a specific academic year with all related information including user, student, program, certificate, and schedule details",
)
async def get_certificate_submissions_by_year(
    request: Request,
    year_code: Annotated[int, Query(description="Academic year code", example=2024)],
    is_submitted: Annotated[
        bool,
        Query(
            description="Filter by submission status - True for submitted, False for not submitted"
        ),
    ] = True,
    submission_service: SubmissionService = Depends(get_submission_service),
):
    """Get certificate submissions for a specific academic year"""
    try:
        if year_code < 2000 or year_code > 3000:
            raise ValueError("INVALID_YEAR_CODE")

        submissions_data = await submission_service.get_certificate_submissions_by_year(
            year_code=year_code, is_submitted=is_submitted
        )

        message_suffix = "submitted" if is_submitted else "not submitted"
        return ResponseBuilder.success(
            request=request,
            data=submissions_data.model_dump(),
            message=f"Retrieved {submissions_data.total_count} certificate submissions ({message_suffix}) for year {year_code}",
            status_code=status.HTTP_200_OK,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception as e:
        raise BusinessLogicError(
            message="Failed to retrieve certificate submissions",
            error_code="CERTIFICATE_SUBMISSIONS_RETRIEVAL_FAILED",
        )


@submissions_router.get(
    "/{submission_id}/verification-history",
    response_model=VerificationHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get verification history for a certificate submission",
    description="Retrieve all verification history records for a specific certificate submission, ordered by creation date descending",
)
async def get_verification_history_by_submission_id(
    request: Request,
    submission_id: Annotated[uuid.UUID, Path(description="Certificate submission ID")],
    submission_service: SubmissionService = Depends(get_submission_service),
):
    """Get verification history for a specific certificate submission"""
    try:
        history_data = (
            await submission_service.get_verification_history_by_submission_id(
                submission_id=str(submission_id)
            )
        )

        return ResponseBuilder.success(
            request=request,
            data=history_data.model_dump(),
            message=f"Retrieved {history_data.total_count} verification history record{'s' if history_data.total_count != 1 else ''} for submission",
            status_code=status.HTTP_200_OK,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception as e:
        raise BusinessLogicError(
            message="Failed to retrieve verification history",
            error_code="VERIFICATION_HISTORY_RETRIEVAL_FAILED",
        )
