import asyncio
import time
from playwright.async_api import async_playwright


async def test_playwright_browser():
    """
    Test function to display a website using Playwright with a visible browser.
    Shows the website for 5-10 seconds for testing purposes.
    """
    # Website URL to test
    link = "https://www.google.com"  # Change this to any website you want to test
    
    async with async_playwright() as p:
        # Launch browser in non-headless mode (visible)
        browser = await p.chromium.launch(
            headless=False,  # Set to False to see the browser
            args=["--start-maximized"]  # Optional: start maximized
        )
        
        # Create a new page
        page = await browser.new_page()
        
        try:
            print(f"Opening website: {link}")
            
            # Navigate to the website
            await page.goto(link)
            
            # Wait for the page to load
            await page.wait_for_load_state("networkidle")
            
            print("Website loaded successfully!")
            print("Displaying for 8 seconds...")
            
            # Keep the browser open for 8 seconds
            await asyncio.sleep(8)
            
        except Exception as e:
            print(f"Error occurred: {e}")
            
        finally:
            # Close the browser
            await browser.close()
            print("Browser closed.")


if __name__ == "__main__":
    # Run the test function
    asyncio.run(test_playwright_browser())