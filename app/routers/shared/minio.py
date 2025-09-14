from fastapi import APIRouter, HTTPException, Depends, Request

from app.services.minio_service import get_minio_service, MinIOService
from app.utils.logging import get_logger
from app.utils.responses import ResponseBuilder

minio_router = APIRouter()
logger = get_logger()


@minio_router.get("/files/{object_name:path}/presigned-url")
async def get_file_presigned_url(
    request: Request,
    object_name: str,
    expires_in_hours: int = 24,
    minio_service: MinIOService = Depends(get_minio_service),
):
    """
    Generate a presigned URL for accessing a file in MinIO storage.

    Args:
        object_name: The full object name/path in MinIO bucket
        expires_in_hours: URL expiration time in hours (default: 24, max: 168)

    Returns:
        Dict containing presigned URL and file metadata
    """
    try:
        # Validate expiration hours
        if expires_in_hours < 1 or expires_in_hours > 168:  # Max 7 days
            raise HTTPException(
                status_code=400,
                detail="expires_in_hours must be between 1 and 168 hours (7 days)",
            )

        result = await minio_service.generate_presigned_url(
            object_name=object_name, expires_in_hours=expires_in_hours
        )

        return ResponseBuilder.success(
            request=request,
            data={
                "presignedUrl": result["presigned_url"],
            },
            message=f"Generated presigned URL for {object_name}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for {object_name}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate presigned URL: {str(e)}"
        )
