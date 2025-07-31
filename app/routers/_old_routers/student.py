# from datetime import datetime
# from uuid import UUID

# from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.db.session import get_async_session
# from app.db.models import (
#     CertificateSubmission,
#     CertificateType,
#     ProgramRequirementSchedule,
#     SubmissionTiming
# )
# from app.schemas.response_schemas import ApiResponse, ResponseStatus
# from app.schemas.submission_schemas import CertificateSubmissionResponse
# from app.services.minio_service import get_minio_service, MinIOService
# from app.utils.logging import get_logger

# logger = get_logger()
# student_router = APIRouter()


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
