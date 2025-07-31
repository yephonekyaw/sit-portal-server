import asyncio
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Error as PlaywrightError

from app.utils.logging import get_logger
from app.config.settings import settings
from app.services.minio_service import MinIOService

logger = get_logger()


def run_playwright_automation_sync(
    url: str, username: str, password: str, headless: bool, timeout: int
) -> Optional[bytes]:
    """
    Synchronous function to run Playwright automation in a separate process.
    """
    # Set event loop policy for Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    async def _automation():
        certificate_data = None  # Initialize at function scope

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless, timeout=timeout)
                context = await browser.new_context(
                    accept_downloads=True,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )

                try:
                    # Navigate to initial page
                    page = await context.new_page()
                    await page.goto(url)
                    await page.wait_for_load_state("networkidle")

                    # Handle login page opening
                    async with page.context.expect_page() as new_page_info:
                        await page.get_by_role(
                            "link",
                            name=re.compile("log in for easier access.", re.IGNORECASE),
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
                        logger.info(f"PDF captured ({len(certificate_data)} bytes)")
                        await route.continue_()

                    await pdf_page.route("**/*", handle_pdf_requests)
                    await pdf_page.goto(url)
                    await pdf_page.wait_for_load_state("networkidle")

                    # Wait for the PDF to be captured
                    await asyncio.sleep(5)

                except PlaywrightError as e:
                    if "net::ERR_ABORTED" in str(e):
                        logger.warning(
                            "Request aborted, expected behaviour due to headless browsing mode."
                        )
                        # certificate_data may have been captured before the abort
                    else:
                        logger.error(f"Playwright error: {e}")

                except Exception as e:
                    logger.error(f"Automation error: {e}")

                finally:
                    await context.close()

        except Exception as e:
            logger.error(f"Playwright failed: {e}")

        return certificate_data

    return asyncio.run(_automation())


class CitiProgramAutomationService:
    """Service for automating CITI Program certificate downloads."""

    def __init__(self):
        self.minio_service = MinIOService()

    async def download_certificate(
        self, url: str, filename: Optional[str] = None, prefix: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Download certificate from CITI Program and save to MinIO."""

        if not settings.CITI_USERNAME or not settings.CITI_PASSWORD:
            logger.error("CITI credentials not configured")
            return None

        filename = filename or "citi_certificate.pdf"
        prefix = prefix or "temp"

        try:
            logger.info("Starting CITI automation...")

            # Run automation in separate process
            loop = asyncio.get_event_loop()
            with ProcessPoolExecutor(max_workers=1) as executor:
                certificate_data = await loop.run_in_executor(
                    executor,
                    run_playwright_automation_sync,
                    url,
                    settings.CITI_USERNAME,
                    settings.CITI_PASSWORD,
                    settings.CITI_HEADLESS,
                    settings.CITI_TIMEOUT,
                )

            if certificate_data:
                # Upload to MinIO
                upload_result = await self.minio_service.upload_bytes(
                    data=certificate_data,
                    filename=filename,
                    prefix=prefix,
                    content_type="application/pdf",
                )

                logger.info(f"Certificate uploaded: {upload_result['object_name']}")
                return {
                    "success": True,
                    "certificate_downloaded": True,
                    "minio_upload": upload_result,
                }
            else:
                logger.warning("No certificate data captured")
                return None

        except Exception as e:
            logger.error(f"CITI automation failed: {e}")
            return None


def get_citi_automation_service() -> CitiProgramAutomationService:
    """Get CITI automation service instance."""
    return CitiProgramAutomationService()
