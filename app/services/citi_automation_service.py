import asyncio
import re
import sys
from uuid import UUID
from typing import Optional, Dict, Any, cast, Tuple
from playwright.async_api import async_playwright, Error as PlaywrightError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    """Service for automating CITI Program certificate downloads and verification."""

    def __init__(self):
        self.minio_service = MinIOService()
        self._configure_event_loop_policy()

    def _configure_event_loop_policy(self):
        """Configure Windows event loop policy if needed."""
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception as e:
                logger.warning(f"Could not set Windows event loop policy: {e}")

    # ========== PUBLIC API METHODS ==========

    async def download_certificate(
        self, url: str, filename: Optional[str] = None, prefix: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Download certificate from CITI Program and save to MinIO."""
        if not self._validate_citi_credentials():
            return {"success": False, "error": "CITI credentials not configured"}

        filename = filename or "citi_certificate.pdf"
        prefix = prefix or "temp"

        try:
            certificate_data = await self._download_certificate_via_playwright(url)

            if certificate_data and len(certificate_data) > 0:
                return await self._upload_certificate_to_minio(
                    certificate_data, filename, prefix
                )
            else:
                logger.warning("No certificate data captured")
                return {
                    "success": False,
                    "certificate_downloaded": False,
                    "error": "No certificate data captured",
                }

        except Exception as e:
            logger.error(f"CITI automation failed: {e}")
            return {"success": False, "certificate_downloaded": False, "error": str(e)}

    async def verify_certificate_submission(
        self, db_session: AsyncSession, request_id: str, submission_id: str
    ) -> Dict[str, Any]:
        """Main method to verify a certificate submission end-to-end."""
        try:
            logger.info(f"Starting certificate verification workflow for {submission_id}")

            # Step 1: Get submission data
            submission_data = await self._fetch_submission_data(db_session, submission_id)
            if not submission_data:
                return {"success": False, "error": "Certificate submission not found"}

            # Step 2: Process submitted document
            submitted_extraction = await self._process_submitted_document(submission_data["submission"])
            if not submitted_extraction:
                return {"success": False, "error": "Failed to process submitted certificate"}

            # Step 3: Verify certificate via download
            verification_extraction = await self._verify_certificate_via_download(
                submitted_extraction, submission_data["submission"]
            )
            if not verification_extraction:
                return {"success": False, "error": "Failed to process verification certificate"}

            # Step 4: Perform LLM verification
            llm_response = await self._perform_llm_verification(
                submission_data, submitted_extraction, verification_extraction
            )
            if not llm_response:
                return {"success": False, "error": "LLM verification failed"}

            # Step 5: Save results
            save_success = await self._save_verification_results(
                db_session, submission_data["submission"], llm_response
            )
            if not save_success:
                return {"success": False, "error": "Failed to save verification results"}

            return self._create_success_response(
                submission_id, request_id, submission_data, llm_response, submitted_extraction, verification_extraction
            )

        except Exception as e:
            logger.error(f"Certificate verification workflow failed for {submission_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "submission_id": submission_id,
                "request_id": request_id,
            }

    # ========== PRIVATE HELPER METHODS ==========

    def _validate_citi_credentials(self) -> bool:
        """Validate that CITI credentials are configured."""
        return bool(settings.CITI_USERNAME and settings.CITI_PASSWORD)

    async def _download_certificate_via_playwright(self, url: str) -> Optional[bytes]:
        """Download certificate using Playwright automation."""
        try:
            return await self._run_playwright_automation(
                url=url,
                username=settings.CITI_USERNAME,
                password=settings.CITI_PASSWORD,
                headless=settings.CITI_HEADLESS,
                timeout=settings.CITI_TIMEOUT,
            )
        except Exception as e:
            logger.error(f"Playwright automation failed: {e}")
            raise

    async def _upload_certificate_to_minio(
        self, certificate_data: bytes, filename: str, prefix: str
    ) -> Dict[str, Any]:
        """Upload certificate data to MinIO."""
        upload_result = await self.minio_service.upload_bytes(
            data=certificate_data,
            filename=filename,
            prefix=prefix,
            content_type="application/pdf",
        )

        logger.info(f"Certificate uploaded successfully: {upload_result['object_name']}")
        return {
            "success": True,
            "certificate_downloaded": True,
            "minio_upload": upload_result,
            "certificate_size": len(certificate_data),
        }

    async def _fetch_submission_data(
        self, db_session: AsyncSession, submission_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve certificate submission data with related objects."""
        try:
            submission_stmt = (
                select(CertificateSubmission, CertificateType, Student, User)
                .join(CertificateType, CertificateSubmission.cert_type_id == CertificateType.id)
                .join(Student, CertificateSubmission.student_id == Student.id)
                .join(User, Student.user_id == User.id)
                .where(CertificateSubmission.id == UUID(submission_id))
            )

            result = await db_session.execute(submission_stmt)
            row = result.first()

            if not row:
                logger.warning("Submission not found", submission_id=submission_id)
                return None

            submission, cert_type, student, user = row
            student_name = f"{user.first_name} {user.last_name}"

            logger.info(f"Retrieved submission data for {student_name}")

            return {
                "submission": submission,
                "cert_type": cert_type,
                "student": student,
                "user": user,
                "student_name": student_name,
            }

        except Exception as e:
            logger.error(f"Failed to retrieve submission data for {submission_id}: {str(e)}")
            return None

    async def _process_submitted_document(
        self, submission: CertificateSubmission
    ) -> Optional[Dict[str, Any]]:
        """Extract text from submitted document."""
        try:
            doc_result = await self._extract_document_text(
                submission.file_object_name, submission.filename
            )
            if not doc_result:
                return None

            extraction_result = doc_result["extraction_result"]
            verification_url = extraction_result.get("verification_url")
            
            if not verification_url:
                logger.error(f"No verification URL found in certificate {submission.id}")
                return None

            return extraction_result

        except Exception as e:
            logger.error(f"Failed to process submitted document {submission.id}: {str(e)}")
            return None

    async def _verify_certificate_via_download(
        self, submitted_extraction: Dict[str, Any], submission: CertificateSubmission
    ) -> Optional[Dict[str, Any]]:
        """Download and process verification certificate."""
        try:
            verification_url = submitted_extraction["verification_url"]
            
            # Download verification certificate
            download_result = await self.download_certificate(
                url=verification_url,
                filename=submission.filename,
                prefix="citi-automated-docs",
            )

            if not download_result or not download_result["success"]:
                logger.error(f"Failed to download verification certificate for {submission.id}")
                return None

            verification_object_name = download_result["minio_upload"]["object_name"]

            # Extract text from verification certificate
            verification_doc_result = await self._extract_document_text(
                verification_object_name, submission.filename
            )
            
            if not verification_doc_result:
                return None

            return verification_doc_result["extraction_result"]

        except Exception as e:
            logger.error(f"Failed to verify certificate via download for {submission.id}: {str(e)}")
            return None

    async def _extract_document_text(
        self, file_object_name: str, filename: str
    ) -> Optional[Dict[str, Any]]:
        """Extract text from a document stored in MinIO."""
        try:
            # Retrieve file from MinIO
            file_result = await self.minio_service.get_file(file_object_name)
            if not file_result["success"]:
                logger.error(f"Failed to retrieve file from MinIO: {file_object_name}")
                return None

            # Extract text from file
            document_service = get_document_service()
            extraction_result = await document_service.extract_text(
                file_result["data"], filename
            )

            if not extraction_result["success"]:
                logger.error(f"Text extraction failed for {filename}")
                return None

            return {
                "file_data": file_result["data"],
                "extraction_result": extraction_result,
            }

        except Exception as e:
            logger.error(f"Document extraction failed for {filename}: {str(e)}")
            return None

    async def _perform_llm_verification(
        self,
        submission_data: Dict[str, Any],
        submitted_extraction: Dict[str, Any],
        verification_extraction: Dict[str, Any],
    ) -> Optional[CitiValidationResponse]:
        """Perform LLM-based certificate verification."""
        try:
            student_name = submission_data["student_name"]
            verification_template = submission_data["cert_type"].verification_template

            langchain_service = get_langchain_service()

            # Prepare and format prompt
            citi_validation_prompt = self._prepare_llm_prompt(
                langchain_service,
                student_name,
                submitted_extraction,
                verification_extraction,
                verification_template,
            )

            # Get LLM response
            llm_chat = langchain_service.get_gemini_chat_model()
            llm_response = cast(
                CitiValidationResponse,
                llm_chat.with_structured_output(schema=CitiValidationResponse).invoke(
                    citi_validation_prompt
                ),
            )

            logger.info(f"LLM verification completed for {student_name}: {llm_response.validation_decision}")

            return llm_response

        except Exception as e:
            logger.error(f"LLM verification failed for {submission_data['student_name']}: {str(e)}")
            return None

    def _prepare_llm_prompt(
        self,
        langchain_service,
        student_name: str,
        submitted_extraction: Dict[str, Any],
        verification_extraction: Dict[str, Any],
        verification_template: str,
    ) -> str:
        """Prepare LLM prompt with all required variables."""
        input_variables = [
            "student_name",
            "submitted_content",
            "submitted_extraction_method",
            "submitted_confidence",
            "verification_content",
            "verification_extraction_method",
            "verification_confidence",
        ]

        return langchain_service.get_custom_prompt_template(
            input_variables, verification_template
        ).format(
            student_name=student_name,
            submitted_content=submitted_extraction["text"],
            submitted_extraction_method=submitted_extraction.get("method", "unknown"),
            submitted_confidence=submitted_extraction.get("confidence", 0),
            verification_content=verification_extraction["text"],
            verification_extraction_method=verification_extraction.get("method", "unknown"),
            verification_confidence=verification_extraction.get("confidence", 0),
        )

    async def _save_verification_results(
        self,
        db_session: AsyncSession,
        submission: CertificateSubmission,
        llm_response: CitiValidationResponse,
    ) -> bool:
        """Save verification results to database."""
        try:
            # Update submission
            old_status = submission.submission_status
            new_status = self._map_validation_decision_to_status(llm_response.validation_decision)
            
            submission.submission_status = new_status
            submission.agent_confidence_score = (
                llm_response.overall_score.value / 100.0
            )  # Convert to 0-1 range

            # Create verification history
            comments, reasons = self._extract_verification_comments_and_reasons(llm_response)
            
            verification_history = VerificationHistory(
                submission_id=submission.id,
                verifier_id=None,  # No human verifier for agent verification
                verification_type=VerificationType.AGENT,
                old_status=old_status,
                new_status=new_status,
                comments=comments,
                reasons=reasons,
                agent_analysis_result=llm_response.model_dump(),
            )

            # Persist changes
            db_session.add(verification_history)
            await db_session.commit()

            logger.info(f"Verification results saved for {submission.id}: {old_status.value} -> {new_status.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to save verification results for {submission.id}: {str(e)}")
            await db_session.rollback()
            return False

    def _create_success_response(
        self,
        submission_id: str,
        request_id: str,
        submission_data: Dict[str, Any],
        llm_response: CitiValidationResponse,
        submitted_extraction: Dict[str, Any],
        verification_extraction: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create success response with all relevant information."""
        logger.info(f"Certificate verification completed for {submission_data['student_name']}: {llm_response.validation_decision}")

        return {
            "success": True,
            "submission_id": submission_id,
            "request_id": request_id,
            "student_name": submission_data["student_name"],
            "validation_decision": llm_response.validation_decision,
            "confidence_level": llm_response.confidence_level,
            "overall_score": llm_response.overall_score.value,
            "verification_url": submitted_extraction.get("verification_url"),
            "submitted_extraction_method": submitted_extraction.get("method"),
            "verification_extraction_method": verification_extraction.get("method"),
        }

    # ========== UTILITY METHODS ==========

    def _map_validation_decision_to_status(self, decision: ValidationDecision) -> SubmissionStatus:
        """Map LLM validation decision to database submission status."""
        mapping = {
            ValidationDecision.APPROVE: SubmissionStatus.APPROVED,
            ValidationDecision.REJECT: SubmissionStatus.REJECTED,
            ValidationDecision.MANUAL_REVIEW: SubmissionStatus.MANUAL_REVIEW,
        }
        return mapping.get(decision, SubmissionStatus.MANUAL_REVIEW)

    def _extract_verification_comments_and_reasons(
        self, llm_response: CitiValidationResponse
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract comments and reasons from LLM response based on decision."""
        if llm_response.validation_decision == ValidationDecision.REJECT:
            return (
                llm_response.final_assessment.reasons_for_rejection,
                llm_response.final_assessment.reasons_for_rejection,
            )
        elif llm_response.validation_decision == ValidationDecision.MANUAL_REVIEW:
            return (
                llm_response.final_assessment.reasons_for_manual_review,
                llm_response.final_assessment.reasons_for_manual_review,
            )
        else:
            # For APPROVE, use general comments if available
            return (llm_response.final_assessment.comments, None)

    # ========== PLAYWRIGHT AUTOMATION ==========

    async def _run_playwright_automation(
        self, url: str, username: str, password: str, headless: bool, timeout: int
    ) -> Optional[bytes]:
        """Run Playwright automation to download certificate."""
        certificate_data = None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=headless,
                    timeout=timeout,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )

                context = await browser.new_context(
                    accept_downloads=True,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )

                try:
                    certificate_data = await self._execute_browser_automation(
                        context, url, username, password, timeout
                    )

                except PlaywrightError as e:
                    if "net::ERR_ABORTED" in str(e):
                        logger.warning(
                            "Request aborted - this may be expected behavior in headless mode"
                        )
                        # certificate_data may have been captured before the abort
                    else:
                        logger.error(f"Playwright error during automation: {e}")
                        raise

                except Exception as e:
                    logger.error(f"Automation error: {e}")
                    raise

                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.error(f"Playwright automation failed: {e}")
            raise

        return certificate_data

    async def _execute_browser_automation(
        self, context, url: str, username: str, password: str, timeout: int
    ) -> Optional[bytes]:
        """Execute the main browser automation flow."""
        certificate_data = None

        # Navigate to initial page
        page = await context.new_page()
        await page.goto(url, timeout=timeout)
        await page.wait_for_load_state("networkidle")

        # Handle login page opening
        async with page.context.expect_page() as new_page_info:
            await page.get_by_role(
                "link", name=re.compile("log in for easier access.", re.IGNORECASE)
            ).click()

        # Login process
        new_page = await new_page_info.value
        await new_page.wait_for_load_state("networkidle")
        await new_page.fill("#main-login-username", username)
        await new_page.fill("#main-login-password", password)
        await new_page.click('input[type="submit"][value="Log In"]')

        # Set up PDF interception
        pdf_page = await context.new_page()

        async def handle_pdf_requests(route, request):
            nonlocal certificate_data
            response = await context.request.get(request.url)
            certificate_data = await response.body()
            await route.continue_()

        await pdf_page.route("**/*", handle_pdf_requests)
        await pdf_page.goto(url, timeout=timeout)
        await pdf_page.wait_for_load_state("networkidle")

        # Wait for the PDF to be captured
        await asyncio.sleep(5)

        return certificate_data


def get_citi_automation_service() -> CitiProgramAutomationService:
    """Get CITI automation service instance."""
    return CitiProgramAutomationService()