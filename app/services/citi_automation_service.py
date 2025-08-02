import asyncio
import re
import sys
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Error as PlaywrightError

from app.utils.logging import get_logger
from app.config.settings import settings
from app.services.minio_service import MinIOService

logger = get_logger()


class CitiProgramAutomationService:
    """Service for automating CITI Program certificate downloads."""

    def __init__(self):
        self.minio_service = MinIOService()
        # Set Windows event loop policy if needed
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception as e:
                logger.warning(f"Could not set Windows event loop policy: {e}")

    async def _run_playwright_automation(
        self, url: str, username: str, password: str, headless: bool, timeout: int
    ) -> Optional[bytes]:
        """Run Playwright automation to download certificate."""
        certificate_data = None

        try:
            logger.info(f"Starting CITI Program Playwright automation on URL: {url}")
            # Launch Playwright browser
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=headless,
                    timeout=timeout,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],  # Better for containerized environments
                )

                context = await browser.new_context(
                    accept_downloads=True,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )

                try:
                    # Navigate to initial page
                    logger.info(f"Navigating to CITI URL: {url}")
                    page = await context.new_page()
                    await page.goto(url, timeout=timeout)
                    await page.wait_for_load_state("networkidle")

                    # Handle login page opening
                    logger.info("Requesting login page...")
                    async with page.context.expect_page() as new_page_info:
                        await page.get_by_role(
                            "link",
                            name=re.compile("log in for easier access.", re.IGNORECASE),
                        ).click()

                    # Login process
                    logger.info("Trying to log in...")
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
                        logger.info(f"PDF captured ({len(certificate_data)} bytes)")
                        await route.continue_()

                    await pdf_page.route("**/*", handle_pdf_requests)
                    await pdf_page.goto(url, timeout=timeout)
                    await pdf_page.wait_for_load_state("networkidle")

                    # Wait for the PDF to be captured
                    await asyncio.sleep(5)

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
                    logger.info("Closing Playwright browser")
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.error(f"Playwright automation failed: {e}")
            raise

        return certificate_data

    async def download_certificate(
        self, url: str, filename: Optional[str] = None, prefix: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Download certificate from CITI Program and save to MinIO."""

        if not settings.CITI_USERNAME or not settings.CITI_PASSWORD:
            logger.error("CITI credentials not configured")
            return {"success": False, "error": "CITI credentials not configured"}

        filename = filename or "citi_certificate.pdf"
        prefix = prefix or "temp"

        try:
            certificate_data = await self._run_playwright_automation(
                url=url,
                username=settings.CITI_USERNAME,
                password=settings.CITI_PASSWORD,
                headless=settings.CITI_HEADLESS,
                timeout=settings.CITI_TIMEOUT,
            )

            if certificate_data and len(certificate_data) > 0:
                # Upload to MinIO
                upload_result = await self.minio_service.upload_bytes(
                    data=certificate_data,
                    filename=filename,
                    prefix=prefix,
                    content_type="application/pdf",
                )

                logger.info(
                    f"Certificate uploaded successfully: {upload_result['object_name']}"
                )
                return {
                    "success": True,
                    "certificate_downloaded": True,
                    "minio_upload": upload_result,
                    "certificate_size": len(certificate_data),
                }
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


def get_citi_automation_service() -> CitiProgramAutomationService:
    """Get CITI automation service instance."""
    return CitiProgramAutomationService()
