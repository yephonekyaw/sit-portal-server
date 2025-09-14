# import os
# import re
# import asyncio
# from playwright.async_api import async_playwright
# from app.utils.logging import get_logger
# logger = get_logger()
# async def test_playwright_browser():
#     """
#     Test function to display a website using Playwright with a visible browser.
#     Shows the website for 5-10 seconds for testing purposes.
#     """
#     # Website URL to test
#     link = "https://www.citiprogram.org/verify/?w36310e6b-de5c-4be4-b913-ce8198bd33e0-67797922"

#     async with async_playwright() as p:
#         # Launch browser in non-headless mode for visibility
#         browser = await p.chromium.launch(
#             headless=False,  # Set to False to see the browser
#             slow_mo=1000,  # Optional: slow down actions by 1 second for visibility
#             timeout=60000,  # Optional: set a timeout for browser launch
#         )
#         context = await browser.new_context(
#             accept_downloads=True,  # Enable downloads in the context
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
#         )

#         # Create a new page
#         page = await context.new_page()

#         try:
#             logger.info(f"Opening website: {link}")

#             # Navigate to the website
#             await page.goto(link)

#             # Wait for the page to load
#             await page.wait_for_load_state("networkidle")

#             logger.info("Clicking the login link...")
#             logger.info(f"Current URL before click: {page.url}")

#             # Method 3: Handle new tab opening
#             async with page.context.expect_page() as new_page_info:
#                 await page.get_by_role(
#                     "link", name=re.compile("log in for easier access.", re.IGNORECASE)
#                 ).click()

#             # Get the new tab that opened
#             new_page = await new_page_info.value
#             logger.info("New tab opened!")
#             logger.info(f"New tab URL: {new_page.url}")

#             # Wait for the new page to load completely
#             await new_page.wait_for_load_state("networkidle")

#             # You can now interact with elements on the NEW tab
#             logger.info(f"New tab title: {await new_page.title()}")

#             # Fill in the login form on the NEW tab
#             logger.info("Filling in login credentials...")

#             # Fill username field
#             await new_page.fill("#main-login-username", "yephonekyaw")

#             # Fill password field
#             await new_page.fill("#main-login-password", f"8uPG?-y6jvid7A2")

#             # Click the Log In button
#             logger.info("Clicking Log In button...")
#             await new_page.click('input[type="submit"][value="Log In"]')

#             os.makedirs("downloads", exist_ok=True)

#             page = await context.new_page()

#             async def handle(route, request):
#                 if request.resource_type == "document":
#                     response = await context.request.get(request.url)
#                     raw_pdf_content = await response.body()
#                     filename = "downloads/citi_certificate.pdf"
#                     with open(filename, "wb") as f:
#                         f.write(raw_pdf_content)

#                     await route.continue_()
#                 else:
#                     await route.continue_()

#             await page.route("**/*", handle)
#             await page.goto(link)
#             await page.wait_for_load_state("networkidle")

#             await asyncio.sleep(5)

#         except Exception as e:
#             logger.error(f"Error occurred: {e}")
#             # Keep browser open even on error for debugging
#             logger.info("Waiting 5 seconds before closing due to error...")
#             await asyncio.sleep(5)

#         finally:
#             # Close the browser
#             await context.close()
#             logger.info("Browser closed.")


# def tesseract():
#     pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
#     tesseract_config = r"--oem 1 --psm 3"
#     input_img = "tesseract/mock_file_1.pdf"

#     page = pymupdf.open(input_img).load_page(0)
#     pix = page.get_pixmap(dpi=300)  # type: ignore
#     pix = pymupdf.Pixmap(pix, 0) if pix.alpha else pix

#     img_bytes = pix.pil_tobytes(format="png")
#     input_img = Image.open(BytesIO(img_bytes))

#     # Get OCR results as a DataFrame
#     df = pytesseract.image_to_data(
#         input_img, output_type=pytesseract.Output.DATAFRAME, config=tesseract_config
#     )

#     df = df.loc[df["conf"] > 70, ["text", "conf"]]
#     confidence = df["conf"].mean()
#     text = " ".join(df["text"].fillna("").str.strip())
#     print(f"Extracted Text:\n{text} with confidence {confidence.round(2)}")


# def temp():
#     for db_session in get_sync_session():
#         program = (
#             (
#                 db_session.execute(
#                     select(Program).where(
#                         Program.id == "1FE58100-B598-4512-8E1B-08886532A2E1"
#                     )
#                 )
#             )
#             .scalars()
#             .first()
#         )
#         print(type(program.id))


if __name__ == "__main__":
    pass
