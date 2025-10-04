from fastapi import APIRouter, Request, responses
from httpx import AsyncClient, HTTPStatusError

from app.config.settings import settings
from app.utils.cookies import CookieUtils
from app.utils.logging import get_logger


sitbrain_router = APIRouter()
logger = get_logger()


@sitbrain_router.get("{full_path:path}")
@sitbrain_router.post("{full_path:path}")
@sitbrain_router.put("{full_path:path}")
@sitbrain_router.delete("{full_path:path}")
@sitbrain_router.patch("{full_path:path}")
@sitbrain_router.options("{full_path:path}")
async def sitbrain_proxy(request: Request, full_path: str):
    async with AsyncClient(base_url=settings.SITBRAIN_BASE_URL) as client:
        try:
            response = await client.request(
                method=request.method,
                url=full_path,
                headers={
                    "authorization": f"Bearer {CookieUtils.extract_bearer_token(request.headers.get('authorization')) or request.cookies.get('jwt_token')}",
                    "content-type": request.headers.get(
                        "content-type", "application/json"
                    ),
                },
                content=await request.body(),
                timeout=30.0,
            )

            content_type = response.headers.get("content-type")
            logger.info(f"SITBrain response content type: {content_type}")

            if "text/plain" in content_type:
                return responses.PlainTextResponse(
                    content=response.text,
                )
            elif "application/json" in content_type:
                return responses.JSONResponse(
                    content=response.json(),
                )
            response.raise_for_status()
            raise HTTPStatusError(
                "Unsupported response content type",
                request=response.request,
                response=response,
            )
        except Exception as e:
            logger.error(f"Error proxying request to SITBrain: {e}")
            return {"error": "Failed to connect to SITBrain service."}
