from typing import List, Union
from fastapi import APIRouter, Request, HTTPException
from linebot.v3.webhook import WebhookHandler, WebhookParser, WebhookPayload
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent

from app.db.session import get_sync_session
from app.services.line.line_token_management_service import (
    get_line_channel_token_service,
)
from app.config.settings import settings
from app.utils.responses import ResponseBuilder


from fastapi import APIRouter

from .webhook import line_router

webhook_router = APIRouter()

webhook_router.include_router(line_router, prefix="/line", tags=["Line Webhook"])


async def _init() -> Union[Configuration, None]:
    for db_session in get_sync_session():
        line_channel_token_service = get_line_channel_token_service(db_session)
        line_access_token = (
            await line_channel_token_service.get_messaging_access_token()
        )
        return Configuration(access_token=line_access_token)

    return None


parser = WebhookParser(settings.LINE_CHANNEL_SECRET)


@webhook_router.post("/line")
async def process_line_webhook_events(request: Request):

    signature = request.headers.get("x-line-signature", "")
    body = (await request.body()).decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(
            status_code=400,
            detail="Invalid signature. Payload has been tampered with or signature is incorrect.",
        )

    configuration = await _init()

    if isinstance(events, List) and events is not None:

        for event in events:
            if isinstance(event, FollowEvent):
                await handle_follow_event(event, configuration)

    return ResponseBuilder.success(
        request=request,
        status_code=200,
        data={"events": "Processed"},
        message="Events processed successfully.",
    )


async def handle_follow_event(event: FollowEvent, configuration: Configuration | None):
    if configuration is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize LINE API configuration.",
        )

    async with AsyncApiClient(configuration=configuration) as api_client:
        line_bot_api = AsyncMessagingApi(api_client)
        response = await line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[
                    TextMessage(
                        quickReply=None,
                        quoteToken=None,
                        text="Thank you for following! How can I assist you today?",
                    )
                ],
                notificationDisabled=False,
            ),
            async_req=False,
        )
        print("Follow event response:", response)
