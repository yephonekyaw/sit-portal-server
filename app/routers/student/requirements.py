from typing import List, Annotated

from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.schemas.student.requirement_schemas import (
    StudentRequirementWithSubmissionResponse,
    RequirementSubmissionRequest,
)
from app.services.minio_service import get_minio_service, MinIOService
from app.services.student.requirements_service import RequirementsService
from app.utils.logging import get_logger
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError
from app.tasks.citi_cert_verification_task import verify_certificate_task
from app.middlewares.auth_middleware import require_student, AuthState
from app.db.session import AsyncSessionLocal

logger = get_logger()
requirement_router = APIRouter()


@requirement_router.post("/submit")
async def submit_student_certificate(
    request: Request,
    submission_data: Annotated[
        RequirementSubmissionRequest, Form(..., media_type="multipart/form-data")
    ],
    current_user: AuthState = Depends(require_student),
    minio_service: MinIOService = Depends(get_minio_service),
):
    async with AsyncSessionLocal.begin() as db_session:
        try:
            requirements_service = RequirementsService(db_session, minio_service)

            # Get student information
            student = await requirements_service.get_student_by_user_id(
                current_user.user_id
            )

            # Submit certificate
            submission_response = await requirements_service.submit_certificate(
                student=student, submission_data=submission_data
            )

            # Call celery verification task
            verify_certificate_task.delay(request.state.request_id, submission_response.submission_id)  # type: ignore

            return ResponseBuilder.success(
                request=request,
                data=submission_response.model_dump(by_alias=True),
                message="Certificate submitted successfully",
            )

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.info(f"Certificate submission error: {str(e)}")
            raise BusinessLogicError("Certificate submission failed")


@requirement_router.get(
    "/all", response_model=List[StudentRequirementWithSubmissionResponse]
)
async def get_student_requirements_with_submissions(
    request: Request,
    current_user: AuthState = Depends(require_student),
    db_session: AsyncSession = Depends(get_async_session),
    minio_service: MinIOService = Depends(get_minio_service),
):
    """
    Get all certificate requirements for the current student with their submission status.

    Returns both submitted and unsubmitted requirements for the student's program and academic year.
    Includes requirement details, program info, certificate type info, and submission data if exists.
    """
    try:
        # Initialize service
        requirements_service = RequirementsService(db_session, minio_service)

        # Get student information
        student = await requirements_service.get_student_by_user_id(
            current_user.user_id
        )

        # Get requirements with submissions through service
        requirements_data = (
            await requirements_service.get_student_requirements_with_submissions(
                student
            )
        )

        return ResponseBuilder.success(
            request=request,
            data=[item.model_dump(by_alias=True) for item in requirements_data],
            message="Student requirements retrieved successfully",
        )

    except BusinessLogicError:
        raise
    except Exception as e:
        logger.info(f"Requirements retrieval error: {str(e)}")
        raise BusinessLogicError("Failed to load requirements")
