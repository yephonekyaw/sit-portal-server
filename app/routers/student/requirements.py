from datetime import datetime, timezone
from uuid import UUID
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    Request,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_async_session
from app.db.models import (
    CertificateSubmission,
    CertificateType,
    ProgramRequirementSchedule,
    ProgramRequirement,
    Program,
    Student,
    SubmissionTiming,
)
from app.schemas.student.requirement_schemas import (
    CertificateSubmissionResponse,
    StudentRequirementWithSubmissionResponse,
)
from app.services.minio_service import get_minio_service, MinIOService
from app.utils.logging import get_logger
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError
from app.tasks.citi_cert_verification_task import verify_certificate_task
from app.middlewares.auth_middleware import require_student, AuthState

logger = get_logger()
requirement_router = APIRouter()


@requirement_router.post("/certificate")
async def submit_certificate(
    request: Request,
    student_id: UUID = Form(..., description="Student ID"),
    cert_type_id: UUID = Form(..., description="Certificate type ID"),
    requirement_schedule_id: UUID = Form(
        ..., description="Program requirement schedule ID"
    ),
    file: UploadFile = File(..., description="Certificate file to upload"),
    db_session: AsyncSession = Depends(get_async_session),
    minio_service: MinIOService = Depends(get_minio_service),
):
    """
    Submit a certificate for verification.

    This endpoint:
    1. Gets certificate code from cert_type_id to use as MinIO prefix
    2. Uploads file to MinIO storage
    3. Determines submission timing by comparing deadline with current time
    4. Saves submission data to database with default agent score of 0
    5. Queues Celery task for certificate verification processing
    6. Returns submission information
    """
    try:
        # Get certificate type to use code as prefix
        cert_type_stmt = select(CertificateType).where(
            CertificateType.id == cert_type_id
        )
        cert_type_result = await db_session.execute(cert_type_stmt)
        cert_type = cert_type_result.scalar_one_or_none()

        if not cert_type:
            raise BusinessLogicError("Certificate type not found")

        # Get requirement schedule to check deadline
        schedule_stmt = select(ProgramRequirementSchedule).where(
            ProgramRequirementSchedule.id == requirement_schedule_id
        )
        schedule_result = await db_session.execute(schedule_stmt)
        schedule = schedule_result.scalar_one_or_none()

        if not schedule:
            raise BusinessLogicError("Requirement schedule not found")

        # Check if student already has a submission for this requirement schedule
        existing_submission_stmt = select(CertificateSubmission).where(
            CertificateSubmission.student_id == student_id,
            CertificateSubmission.requirement_schedule_id == requirement_schedule_id,
        )
        existing_submission_result = await db_session.execute(existing_submission_stmt)
        existing_submission = existing_submission_result.scalar_one_or_none()

        if existing_submission:
            raise BusinessLogicError(
                f"Student already has a submission for this requirement. "
                f"Existing submission ID: {existing_submission.id}"
            )

        # Upload file to MinIO with certificate code as prefix
        upload_result = await minio_service.upload_file(
            file=file, prefix=cert_type.cert_code, filename=file.filename
        )

        if not upload_result["success"]:
            raise BusinessLogicError("Failed to upload file")

        # Determine submission timing
        current_time = datetime.now(timezone.utc)
        if current_time <= schedule.submission_deadline:
            timing = SubmissionTiming.ON_TIME
        else:
            timing = SubmissionTiming.LATE

        # Create submission record
        submission = CertificateSubmission(
            student_id=student_id,
            cert_type_id=cert_type_id,
            requirement_schedule_id=requirement_schedule_id,
            file_object_name=upload_result["object_name"],
            filename=file.filename or "unknown",
            file_size=upload_result["size"],
            mime_type=upload_result["content_type"],
            agent_confidence_score=0.0,
            submission_timing=timing,
        )

        db_session.add(submission)
        await db_session.commit()
        await db_session.refresh(submission)

        # Queue Celery task for processing
        verify_certificate_task.delay(request.state.request_id, str(submission.id))  # type: ignore

        # Prepare response data
        response_data = CertificateSubmissionResponse.model_validate(submission)

        return ResponseBuilder.success(
            request=request,
            data=response_data.model_dump(mode="json"),
            message="Certificate submitted successfully",
        )

    except BusinessLogicError:
        raise
    except Exception as e:
        logger.error(f"Error submitting certificate: {str(e)}", exc_info=True)
        await db_session.rollback()
        raise BusinessLogicError(f"Internal server error: {str(e)}")


@requirement_router.get(
    "/all", response_model=List[StudentRequirementWithSubmissionResponse]
)
async def get_student_requirements_with_submissions(
    request: Request,
    current_user: AuthState = Depends(require_student),
    db_session: AsyncSession = Depends(get_async_session),
):
    """
    Get all certificate requirements for the current student with their submission status.

    Returns both submitted and unsubmitted requirements for the student's program and academic year.
    Includes requirement details, program info, certificate type info, and submission data if exists.
    """
    try:
        # Get student information
        student_stmt = (
            select(Student)
            .where(Student.user_id == UUID(current_user.user_id))
            .options(selectinload(Student.program), selectinload(Student.academic_year))
        )
        student_result = await db_session.execute(student_stmt)
        student = student_result.scalar_one_or_none()

        if not student:
            raise BusinessLogicError("Student record not found")

        # Get all requirement schedules for the student's program and academic year
        # with their related data and any existing submissions
        schedules_stmt = (
            select(ProgramRequirementSchedule)
            .join(ProgramRequirement)
            .join(Program)
            .join(CertificateType)
            .where(
                ProgramRequirement.program_id == student.program_id,
                ProgramRequirementSchedule.academic_year_id == student.academic_year_id,
                # ProgramRequirement.is_active == True,
                # CertificateType.is_active == True,
            )
            .options(
                selectinload(
                    ProgramRequirementSchedule.program_requirement
                ).selectinload(ProgramRequirement.program),
                selectinload(
                    ProgramRequirementSchedule.program_requirement
                ).selectinload(ProgramRequirement.certificate_type),
                selectinload(
                    ProgramRequirementSchedule.certificate_submissions.and_(
                        CertificateSubmission.student_id == student.id
                    )
                ),
            )
        )

        schedules_result = await db_session.execute(schedules_stmt)
        schedules = schedules_result.scalars().all()

        # Build response data
        requirements_data: List[StudentRequirementWithSubmissionResponse] = []
        for schedule in schedules:
            requirement = schedule.program_requirement
            program = requirement.program
            cert_type = requirement.certificate_type

            # Find existing submission for this student and requirement schedule
            submission = None
            for sub in schedule.certificate_submissions:
                if sub.student_id == student.id:
                    submission = sub
                    break

            requirement_data = StudentRequirementWithSubmissionResponse(
                # Schedule data
                schedule_id=str(schedule.id),
                submission_deadline=schedule.submission_deadline.isoformat(),
                # Requirement data
                requirement_id=str(requirement.id),
                requirement_name=requirement.name,
                target_year=requirement.target_year,
                is_mandatory=requirement.is_mandatory,
                special_instruction=requirement.special_instruction,
                # Program data
                program_id=str(program.id),
                program_code=program.program_code,
                program_name=program.program_name,
                # Certificate type data
                cert_type_id=str(cert_type.id),
                cert_code=cert_type.cert_code,
                cert_name=cert_type.cert_name,
                cert_description=cert_type.description,
                # Submission data (empty if not submitted)
                submission_id=str(submission.id) if submission else None,
                file_object_name=submission.file_object_name if submission else None,
                filename=submission.filename if submission else None,
                file_size=submission.file_size if submission else None,
                mime_type=submission.mime_type if submission else None,
                submission_status=(
                    submission.submission_status.value if submission else None
                ),
                agent_confidence_score=(
                    submission.agent_confidence_score if submission else None
                ),
                submission_timing=(
                    submission.submission_timing.value if submission else None
                ),
                submitted_at=(
                    submission.submitted_at.isoformat() if submission else None
                ),
                expired_at=(
                    submission.expired_at.isoformat()
                    if submission and submission.expired_at
                    else None
                ),
            )

            requirements_data.append(requirement_data)

        return ResponseBuilder.success(
            request=request,
            data=[item.model_dump(by_alias=True) for item in requirements_data],
            message="Student requirements retrieved successfully",
        )

    except BusinessLogicError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving student requirements: {str(e)}", exc_info=True)
        raise BusinessLogicError(f"Internal server error: {str(e)}")


# @student_router.post("/verify-certificate", response_model=ApiResponse)
# async def verify_certificate(
#     submitted: UploadFile, extracted: UploadFile, request: Request
# ):
#     try:
#         extractor = TextExtractionProvider()
#         langchain_service = LangChainServiceProvider()

#         submitted_content = await submitted.read()
#         verification_content = await extracted.read()

#         submitted_result = await extractor.extract_text(
#             submitted_content, str(submitted.filename)
#         )
#         extracted_result = await extractor.extract_text(
#             verification_content, str(extracted.filename)
#         )

#         stmt = select(CertificateType.verification_template).where(
#             CertificateType.code == "citi_program_certificate"
#         )
#         async with AsyncSessionLocal() as session:
#             result = await session.execute(stmt)
#             verification_template = result.scalar_one_or_none()

#             if not verification_template:
#                 raise ValueError(
#                     "Verification template not found for 'citi_program_certificate'"
#                 )

#             citi_validation_prompt = langchain_service.get_custom_prompt_template(
#                 [
#                     "student_name",
#                     "submitted_content",
#                     "submitted_extraction_method",
#                     "submitted_confidence",
#                     "verification_content",
#                     "verification_extraction_method",
#                     "verification_confidence",
#                 ],
#                 verification_template,
#             ).format(
#                 student_name="Su Lei Yin Win",
#                 submitted_content=submitted_result["text"],
#                 submitted_extraction_method=submitted_result.get("method", "unknown"),
#                 submitted_confidence=submitted_result.get("confidence", 0),
#                 verification_content=extracted_result["text"],
#                 verification_extraction_method=extracted_result.get(
#                     "method", "unknown"
#                 ),
#                 verification_confidence=extracted_result.get("confidence", 0),
#             )

#             llm_chat = langchain_service.get_gemini_chat_model()
#             llm_response = cast(
#                 CitiValidationResponse,
#                 llm_chat.with_structured_output(schema=CitiValidationResponse).invoke(
#                     citi_validation_prompt
#                 ),
#             )

#             return ResponseBuilder.success(
#                 request=request,
#                 data=llm_response.model_dump(),
#                 message="Text extraction completed successfully.",
#             )
#     except Exception as e:
#         raise StarletteHTTPException(status_code=500, detail=str(e))
