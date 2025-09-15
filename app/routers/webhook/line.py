from fastapi import APIRouter, Request, HTTPException
from linebot.v3.exceptions import InvalidSignatureError

from app.db.session import get_sync_session
from app.utils.responses import ResponseBuilder
from app.services.line.line_webhook_service import LineWebhookService

line_router = APIRouter()


@line_router.post("")
async def process_line_webhook_events(request: Request):
    """Process LINE webhook events using LineWebhookService"""
    signature = request.headers.get("x-line-signature", "")
    body = (await request.body()).decode()

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing X-Line-Signature header",
        )

    try:
        # Get database session
        for db_session in get_sync_session():
            # Create LINE webhook service
            line_service = LineWebhookService(db_session)

            # Handle webhook events
            await line_service.handle_webhook_events(body, signature)

            break  # Only need first session

    except InvalidSignatureError:
        raise HTTPException(
            status_code=400,
            detail="Invalid signature. Payload has been tampered with or signature is incorrect.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing webhook events: {str(e)}",
        )

    return ResponseBuilder.success(
        request=request,
        status_code=200,
        data={"events": "Processed"},
        message="Events processed successfully.",
    )
