import asyncio
import re
from uuid import UUID
from typing import Optional, Dict, Any, cast
from playwright.async_api import async_playwright, Error as PlaywrightError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.utils.logging import get_logger
from app.config.settings import settings
from app.services.minio_service import MinIOService
from app.services.document_service import get_document_service
from app.services.langchain_service import get_langchain_service
from app.db.models import (
    CertificateSubmission,
    CertificateType,
    Student,
    User,
    VerificationHistory,
    SubmissionStatus,
    VerificationType,
)
from app.schemas.citi_template_schemas import CitiValidationResponse, ValidationDecision

logger = get_logger()


class CitiProgramAutomationService:
    """Service for automating CITI Program certificate verification."""

    def __init__(self):
        self.minio_service = MinIOService()

    async def _download_certificate_from_url(self, url: str) -> Optional[bytes]:
        """Download certificate from CITI Program URL using Playwright automation."""
        if not all([settings.CITI_USERNAME, settings.CITI_PASSWORD]):
            logger.error("CITI credentials not configured")
            return None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=settings.CITI_HEADLESS,
                    timeout=settings.CITI_TIMEOUT,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )

                context = await browser.new_context(
                    accept_downloads=True,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )

                certificate_data = None

                try:
                    # Navigate and login
                    page = await context.new_page()
                    await page.goto(url, timeout=settings.CITI_TIMEOUT)
                    await page.wait_for_load_state("networkidle")

                    # Handle login
                    async with page.context.expect_page() as new_page_info:
                        await page.get_by_role(
                            "link",
                            name=re.compile("log in for easier access.", re.IGNORECASE),
                        ).click()

                    login_page = await new_page_info.value
                    await login_page.wait_for_load_state("networkidle")
                    await login_page.fill(
                        "#main-login-username", settings.CITI_USERNAME
                    )
                    await login_page.fill(
                        "#main-login-password", settings.CITI_PASSWORD
                    )
                    await login_page.click('input[type="submit"][value="Log In"]')

                    # Capture PDF
                    pdf_page = await context.new_page()

                    async def handle_pdf_requests(route, request):
                        nonlocal certificate_data
                        response = await context.request.get(request.url)
                        certificate_data = await response.body()
                        logger.info(f"PDF captured ({len(certificate_data)} bytes)")
                        await route.continue_()

                    await pdf_page.route("**/*", handle_pdf_requests)
                    await pdf_page.goto(url, timeout=settings.CITI_TIMEOUT)
                    await pdf_page.wait_for_load_state("networkidle")
                    await asyncio.sleep(5)  # Wait for PDF capture

                except PlaywrightError as e:
                    if "net::ERR_ABORTED" in str(e):
                        logger.warning(
                            "Request aborted - this may be expected behavior in headless mode"
                        )
                        # certificate_data may have been captured before the abort
                    else:
                        logger.error(f"Playwright error during automation: {e}")
                        raise
                finally:
                    await context.close()
                    await browser.close()

                return certificate_data

        except Exception as e:
            logger.error(f"Certificate download failed: {e}")
            return None

    async def _extract_document_text(
        self, file_object_name: str, filename: str
    ) -> Optional[Dict[str, Any]]:
        """Extract text from document stored in MinIO."""
        file_result = await self.minio_service.get_file(file_object_name)
        if not file_result["success"]:
            logger.error(f"Failed to retrieve file: {file_object_name}")
            return None

        document_service = get_document_service()
        extraction_result = await document_service.extract_text(
            file_result["data"], filename
        )

        if not extraction_result["success"]:
            logger.error(f"Text extraction failed: {filename}")
            return None

        logger.info(
            f"Document processed: {filename} ({extraction_result.get('method', 'unknown')})"
        )
        return extraction_result

    async def _get_submission_data(
        self, db_session: Session, submission_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve certificate submission with related data."""
        try:
            result = db_session.execute(
                select(CertificateSubmission, CertificateType, Student, User)
                .join(
                    CertificateType,
                    CertificateSubmission.cert_type_id == CertificateType.id,
                )
                .join(Student, CertificateSubmission.student_id == Student.id)
                .join(User, Student.user_id == User.id)
                .where(CertificateSubmission.id == UUID(submission_id))
            )

            row = result.first()
            if not row:
                return None

            submission, cert_type, student, user = row
            return {
                "submission": submission,
                "cert_type": cert_type,
                "student": student,
                "user": user,
                "student_name": f"{user.first_name} {user.last_name}",
            }
        except Exception as e:
            logger.error(f"Failed to retrieve submission data: {submission_id} - {e}")
            return None

    async def _perform_llm_verification(
        self,
        student_name: str,
        submitted_text: Dict,
        verification_text: Dict,
        template: str,
    ) -> Optional[CitiValidationResponse]:
        """Perform LLM-based certificate verification."""
        try:
            langchain_service = get_langchain_service()

            prompt_template = langchain_service.get_custom_prompt_template(
                [
                    "student_name",
                    "submitted_content",
                    "submitted_extraction_method",
                    "submitted_confidence",
                    "verification_content",
                    "verification_extraction_method",
                    "verification_confidence",
                ],
                template,
            )

            formatted_prompt = prompt_template.format(
                student_name=student_name,
                submitted_content=submitted_text["text"],
                submitted_extraction_method=submitted_text.get("method", "unknown"),
                submitted_confidence=submitted_text.get("confidence", 0),
                verification_content=verification_text["text"],
                verification_extraction_method=verification_text.get(
                    "method", "unknown"
                ),
                verification_confidence=verification_text.get("confidence", 0),
            )

            llm_chat = langchain_service.get_openai_chat_model()
            response = cast(
                CitiValidationResponse,
                llm_chat.with_structured_output(schema=CitiValidationResponse).invoke(
                    formatted_prompt
                ),
            )

            logger.info(
                f"LLM verification completed: {student_name} - {response.validation_decision}"
            )
            return response

        except Exception as e:
            logger.error(f"LLM verification failed: {student_name} - {e}")
            return None

    def _map_validation_to_status(
        self, decision: ValidationDecision
    ) -> SubmissionStatus:
        """Map validation decision to submission status."""
        mapping = {
            ValidationDecision.APPROVE: SubmissionStatus.APPROVED,
            ValidationDecision.REJECT: SubmissionStatus.REJECTED,
            ValidationDecision.MANUAL_REVIEW: SubmissionStatus.MANUAL_REVIEW,
        }
        return mapping.get(decision, SubmissionStatus.MANUAL_REVIEW)

    def _extract_verification_comments(
        self, response: CitiValidationResponse
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract comments and reasons from LLM response."""
        assessment = response.final_assessment
        if response.validation_decision == ValidationDecision.REJECT:
            return assessment.reasons_for_rejection, assessment.reasons_for_rejection
        elif response.validation_decision == ValidationDecision.MANUAL_REVIEW:
            return (
                assessment.reasons_for_manual_review,
                assessment.reasons_for_manual_review,
            )
        return assessment.comments, None

    async def _save_verification_results(
        self,
        db_session: Session,
        submission: CertificateSubmission,
        llm_response: CitiValidationResponse,
    ) -> bool:
        """Save verification results to database."""
        try:
            old_status = submission.submission_status
            new_status = self._map_validation_to_status(
                llm_response.validation_decision
            )

            # Update submission
            submission.submission_status = new_status
            submission.agent_confidence_score = llm_response.overall_score.value / 100.0

            # Create verification history
            comments, reasons = self._extract_verification_comments(llm_response)
            verification_history = VerificationHistory(
                submission_id=submission.id,
                verifier_id=None,
                verification_type=VerificationType.AGENT,
                old_status=old_status,
                new_status=new_status,
                comments=comments,
                reasons=reasons,
                agent_analysis_result=llm_response.model_dump_json(indent=2),
            )

            db_session.add(verification_history)
            db_session.commit()

            logger.info(
                f"Verification saved: {submission.id} - {old_status.value} → {new_status.value}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save verification: {submission.id} - {e}")
            return False

    async def verify_certificate_submission(
        self, db_session: Session, request_id: str, submission_id: str
    ) -> Dict[str, Any]:
        """Main method to verify certificate submission end-to-end."""
        logger.info(f"Starting verification workflow: {submission_id}")

        try:
            # Get submission data
            submission_data = await self._get_submission_data(db_session, submission_id)
            if not submission_data:
                return {"success": False, "error": "Submission not found"}

            submission = submission_data["submission"]
            cert_type = submission_data["cert_type"]
            student_name = submission_data["student_name"]

            # Extract text from submitted certificate
            submitted_extraction = await self._extract_document_text(
                submission.file_object_name, submission.filename
            )
            if not submitted_extraction:
                return {
                    "success": False,
                    "error": "Failed to process submitted certificate",
                }

            # Check verification URL
            verification_url = submitted_extraction.get("verification_url")
            if not verification_url:
                return {"success": False, "error": "No verification URL found"}

            logger.info(f"Found verification URL: {verification_url}")

            # Download verification certificate
            certificate_data = await self._download_certificate_from_url(
                verification_url
            )
            if not certificate_data:
                return {
                    "success": False,
                    "error": "Failed to download verification certificate",
                }

            # Upload verification certificate to MinIO
            upload_result = await self.minio_service.upload_bytes(
                data=certificate_data,
                filename=submission.filename,
                prefix="citi-automated-docs",
                content_type="application/pdf",
            )
            if not upload_result["success"]:
                return {
                    "success": False,
                    "error": "Failed to store verification certificate",
                }

            # Extract text from verification certificate
            verification_extraction = await self._extract_document_text(
                upload_result["object_name"], submission.filename
            )
            if not verification_extraction:
                return {
                    "success": False,
                    "error": "Failed to process verification certificate",
                }

            # Perform LLM verification
            llm_response = await self._perform_llm_verification(
                student_name,
                submitted_extraction,
                verification_extraction,
                cert_type.verification_template,
            )
            if not llm_response:
                return {"success": False, "error": "LLM verification failed"}

            # Save results
            if not await self._save_verification_results(
                db_session, submission, llm_response
            ):
                return {
                    "success": False,
                    "error": "Failed to save verification results",
                }

            logger.info(
                f"Verification completed: {submission_id} - {llm_response.validation_decision}"
            )

            return {
                "success": True,
                "submission_id": submission_id,
                "request_id": request_id,
                "student_name": student_name,
                "validation_decision": llm_response.validation_decision,
                "confidence_level": llm_response.confidence_level,
                "overall_score": llm_response.overall_score.value,
                "verification_url": verification_url,
            }

        except Exception as e:
            logger.error(f"Verification workflow failed: {submission_id} - {e}")
            return {
                "success": False,
                "error": str(e),
                "submission_id": submission_id,
                "request_id": request_id,
            }


def get_citi_automation_service() -> CitiProgramAutomationService:
    """Get CITI automation service instance."""
    return CitiProgramAutomationService()
