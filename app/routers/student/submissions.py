from datetime import datetime, timezone
from uuid import UUID

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

from app.db.session import get_async_session
from app.db.models import (
    CertificateSubmission,
    CertificateType,
    ProgramRequirementSchedule,
    SubmissionTiming,
)
from app.schemas.student.submission_schemas import CertificateSubmissionResponse
from app.services.minio_service import get_minio_service, MinIOService
from app.utils.logging import get_logger
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError
from app.tasks.citi_cert_verification_task import verify_certificate_task

logger = get_logger()
submissions_router = APIRouter()


@submissions_router.post("/certificate")
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
            file=file, prefix=cert_type.code, filename=file.filename
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
