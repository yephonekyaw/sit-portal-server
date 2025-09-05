from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Request, status, Path

from app.services.staff.submission_service import (
    SubmissionService,
    get_submission_service,
)
from app.schemas.staff.submission_schemas import (
    GetListOfSubmissions,
    VerificationHistoryListResponse,
)
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError
from app.utils.error_handlers import handle_service_error
from app.middlewares.auth_middleware import require_staff

submissions_router = APIRouter(dependencies=[Depends(require_staff)])


@submissions_router.get(
    "/schedule/{schedule_id}",
    response_model=GetListOfSubmissions,
    status_code=status.HTTP_200_OK,
    summary="Get all submissions by schedule",
    description="Retrieve all student submissions (both submitted and unsubmitted) for a specific program requirement schedule",
)
async def get_submissions_by_schedule_id(
    request: Request,
    schedule_id: Annotated[
        uuid.UUID, Path(description="Program requirement schedule ID")
    ],
    submission_service: SubmissionService = Depends(get_submission_service),
):
    """Get all student submissions for a specific program requirement schedule"""
    try:
        submissions_data = await submission_service.get_all_submissions_by_schedule_id(
            schedule_id=str(schedule_id)
        )

        total_students = len(submissions_data.submitted_submissions) + len(
            submissions_data.unsubmitted_submissions
        )
        return ResponseBuilder.success(
            request=request,
            data=submissions_data.model_dump(by_alias=True),
            message=f"Retrieved {total_students} student submissions for schedule {schedule_id}",
            status_code=status.HTTP_200_OK,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception as e:
        raise BusinessLogicError(
            message="Failed to retrieve submissions",
            error_code="SUBMISSIONS_RETRIEVAL_FAILED",
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
            data=history_data.model_dump(by_alias=True),
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
