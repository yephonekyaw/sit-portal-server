import asyncio
import datetime
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()
        await page.goto(
            "https://www.citiprogram.org/verify/?w36310e6b-de5c-4be4-b913-ce8198bd33e0-67797922"
        )

        print("🎯 Solve the CAPTCHA manually...")
        input("Press Enter after solving the CAPTCHA...")

        await page.wait_for_load_state("load")

        screenshot_path = f"citiprogram_screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await page.screenshot(path=f"files/{screenshot_path}")

        input("Press Enter to close browser...")
        await browser.close()


asyncio.run(main())


class WebScraper:
    """
    A class to handle the downloading of a certificate from the provided URL
    used to further authenticate the submitted certificate.
    """

    def __init__(self):
        """
        Initialize the WebScraper class.
        """
        pass
