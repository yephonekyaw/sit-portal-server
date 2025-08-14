import asyncio
import re
from playwright.async_api import async_playwright
import os
from app.utils.logging import get_logger

logger = get_logger()


async def test_playwright_browser():
    """
    Test function to display a website using Playwright with a visible browser.
    Shows the website for 5-10 seconds for testing purposes.
    """
    # Website URL to test
    link = "https://www.citiprogram.org/verify/?w36310e6b-de5c-4be4-b913-ce8198bd33e0-67797922"

    async with async_playwright() as p:
        # Launch browser in non-headless mode for visibility
        browser = await p.chromium.launch(
            headless=False,  # Set to False to see the browser
            slow_mo=1000,  # Optional: slow down actions by 1 second for visibility
            timeout=60000,  # Optional: set a timeout for browser launch
        )
        context = await browser.new_context(
            accept_downloads=True,  # Enable downloads in the context
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        )

        # Create a new page
        page = await context.new_page()

        try:
            logger.info(f"Opening website: {link}")

            # Navigate to the website
            await page.goto(link)

            # Wait for the page to load
            await page.wait_for_load_state("networkidle")

            logger.info("Clicking the login link...")
            logger.info(f"Current URL before click: {page.url}")

            # Method 3: Handle new tab opening
            async with page.context.expect_page() as new_page_info:
                await page.get_by_role(
                    "link", name=re.compile("log in for easier access.", re.IGNORECASE)
                ).click()

            # Get the new tab that opened
            new_page = await new_page_info.value
            logger.info("New tab opened!")
            logger.info(f"New tab URL: {new_page.url}")

            # Wait for the new page to load completely
            await new_page.wait_for_load_state("networkidle")

            # You can now interact with elements on the NEW tab
            logger.info(f"New tab title: {await new_page.title()}")

            # Fill in the login form on the NEW tab
            logger.info("Filling in login credentials...")

            # Fill username field
            await new_page.fill("#main-login-username", "yephonekyaw")

            # Fill password field
            await new_page.fill("#main-login-password", f"8uPG?-y6jvid7A2")

            # Click the Log In button
            logger.info("Clicking Log In button...")
            await new_page.click('input[type="submit"][value="Log In"]')

            os.makedirs("downloads", exist_ok=True)

            page = await context.new_page()

            async def handle(route, request):
                if request.resource_type == "document":
                    response = await context.request.get(request.url)
                    raw_pdf_content = await response.body()
                    filename = "downloads/citi_certificate.pdf"
                    with open(filename, "wb") as f:
                        f.write(raw_pdf_content)

                    await route.continue_()
                else:
                    await route.continue_()

            await page.route("**/*", handle)
            await page.goto(link)
            await page.wait_for_load_state("networkidle")

            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Error occurred: {e}")
            # Keep browser open even on error for debugging
            logger.info("Waiting 5 seconds before closing due to error...")
            await asyncio.sleep(5)

        finally:
            # Close the browser
            await context.close()
            logger.info("Browser closed.")


if __name__ == "__main__":
    # Run the test function
    asyncio.run(test_playwright_browser())

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ChannelType,
    Notification,
    NotificationRecipient,
    NotificationType,
    User,
    UserType,
    ActorType,
    NotificationStatus,
    Priority,
)


class NotificationService:
    """Service for managing notifications and recipients"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def _get_notification_type_by_code(self, code: str) -> NotificationType:
        """Get notification type by code or raise ValueError if not found."""
        result = await self.db.execute(
            select(NotificationType).where(NotificationType.code == code)
        )
        notification_type = result.scalar_one_or_none()
        if not notification_type:
            raise ValueError(f"Notification type '{code}' not found.")
        return notification_type

    async def _get_recipient_by_ids(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[NotificationRecipient]:
        """Get notification recipient by notification and user IDs."""
        result = await self.db.execute(
            select(NotificationRecipient).where(
                NotificationRecipient.notification_id == notification_id,
                NotificationRecipient.recipient_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _create_notification_recipients(
        self, notification_id: uuid.UUID, recipient_ids: List[uuid.UUID]
    ) -> None:
        """Create notification recipients for given user IDs."""
        # Get all valid users in one query
        users_result = await self.db.execute(
            select(User).where(User.id.in_(recipient_ids))
        )
        users = {user.id: user for user in users_result.scalars().all()}

        # Create recipients
        recipients = []
        for recipient_id in recipient_ids:
            user = users.get(recipient_id)
            if user:
                recipients.append(
                    NotificationRecipient(
                        notification_id=notification_id,
                        recipient_id=user.id,
                        status=NotificationStatus.PENDING,
                        in_app_enabled=True,
                        microsoft_teams_enabled=(user.user_type == UserType.STUDENT),
                    )
                )

        self.db.add_all(recipients)

    async def create_notification(
        self,
        notification_type_code: str,
        entity_id: uuid.UUID,
        actor_type: ActorType,
        subject: str,
        body: str,
        recipient_ids: List[uuid.UUID],
        actor_id: Optional[uuid.UUID] = None,
        priority: Optional[Priority] = None,
        notification_metadata: Optional[dict] = None,
        scheduled_for: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> Notification:
        """Create a new notification and link it to recipients."""
        notification_type = await self._get_notification_type_by_code(
            notification_type_code
        )

        notification = Notification(
            notification_type_id=notification_type.id,
            entity_id=entity_id,
            actor_type=actor_type,
            actor_id=actor_id,
            subject=subject,
            body=body,
            priority=priority or notification_type.default_priority,
            notification_metadata=notification_metadata,
            scheduled_for=scheduled_for,
            expires_at=expires_at,
        )

        self.db.add(notification)
        await self.db.flush()  # Get notification ID

        await self._create_notification_recipients(notification.id, recipient_ids)
        await self.db.commit()

        return notification

    async def mark_notification_as_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Mark a notification as read for a specific user."""
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                NotificationRecipient.notification_id == notification_id,
                NotificationRecipient.recipient_id == user_id,
            )
            .values(status=NotificationStatus.READ, read_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_notification_as_delivered(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
        channel_type: Optional[ChannelType] = None,
    ) -> bool:
        """Mark a notification as delivered for a specific user."""
        update_values = {
            "status": NotificationStatus.DELIVERED,
            "delivered_at": datetime.now(timezone.utc),
        }

        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                NotificationRecipient.notification_id == notification_id,
                NotificationRecipient.recipient_id == user_id,
            )
            .values(**update_values)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_notification_as_failed(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Mark a notification as failed for a specific user."""
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                NotificationRecipient.notification_id == notification_id,
                NotificationRecipient.recipient_id == user_id,
            )
            .values(status=NotificationStatus.FAILED)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_notifications_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all unread notifications as read for a user."""
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                NotificationRecipient.recipient_id == user_id,
                NotificationRecipient.status == NotificationStatus.DELIVERED,
            )
            .values(status=NotificationStatus.READ, read_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount
