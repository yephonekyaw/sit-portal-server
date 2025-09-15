from fastapi import APIRouter

from .line import line_router

webhook_router = APIRouter()

webhook_router.include_router(line_router, prefix="/line", tags=["LINE Webhook"])
