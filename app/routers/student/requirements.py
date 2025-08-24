from typing import List

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Request,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.schemas.student.requirement_schemas import (
    StudentRequirementWithSubmissionResponse,
    RequirementSubmissionRequest,
)
from app.services.minio_service import get_minio_service, MinIOService
from app.services.student.requirements_service import StudentRequirementsService
from app.utils.logging import get_logger
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError
from app.tasks.citi_cert_verification_task import verify_certificate_task
from app.middlewares.auth_middleware import require_student, AuthState

logger = get_logger()
requirement_router = APIRouter()


@requirement_router.post("/submit")
async def submit_student_certificate(
    request: Request,
    submission_data: RequirementSubmissionRequest,
    file: UploadFile = File(..., description="Certificate file to upload"),
    current_user: AuthState = Depends(require_student),
    db_session: AsyncSession = Depends(get_async_session),
    minio_service: MinIOService = Depends(get_minio_service),
):
    """
    Submit a certificate for verification by authenticated student.

    This endpoint:
    1. Validates student authentication and ownership
    2. Validates submission constraints (deadline, existing submission, etc.)
    3. Uploads file to MinIO storage with certificate code prefix
    4. Determines submission timing based on deadline
    5. Creates submission record in database
    6. Queues Celery task for certificate verification
    7. Returns submission ID
    """
    try:
        # Initialize service
        requirements_service = StudentRequirementsService(db_session, minio_service)

        # Get student information
        student = await requirements_service.get_student_by_user_id(
            current_user.user_id
        )

        # Submit certificate through service
        is_edit = bool(submission_data.submission_id)
        response_data = await requirements_service.submit_certificate(
            student, submission_data, file
        )

        # Queue Celery task for processing
        # verify_certificate_task.delay(request.state.request_id, response_data.submission_id)  # type: ignore

        return ResponseBuilder.success(
            request=request,
            data=response_data.model_dump(by_alias=True),
            message=(
                "Certificate submitted successfully"
                if not is_edit
                else "Certificate updated successfully"
            ),
        )

    except BusinessLogicError:
        raise
    except Exception as e:
        logger.info(f"Certificate submission error: {str(e)}")
        await db_session.rollback()
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
        requirements_service = StudentRequirementsService(db_session, minio_service)

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
