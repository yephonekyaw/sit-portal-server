from typing import Annotated, List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, Query

from app.services.minio_service import MinIOService
from app.services.citi_automation_service import CitiProgramAutomationService
from app.schemas.minio_schemas import (
    FileUploadResponse,
    FileDeleteResponse,
    PresignedUrlResponse,
    FileListResponse,
    DeleteFileRequest,
    GenerateUrlRequest,
    CitiAutomationRequest,
    CitiAutomationResponse,
)
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError

storage_router = APIRouter()


def get_minio_service() -> MinIOService:
    """Dependency to get MinIO service instance"""
    return MinIOService()


def get_citi_automation_service() -> CitiProgramAutomationService:
    """Dependency to get CITI automation service instance"""
    return CitiProgramAutomationService()


@storage_router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    request: Request,
    minio_service: Annotated[MinIOService, Depends(get_minio_service)],
    file: UploadFile = File(...),
):
    """
    Upload a single file to MinIO storage

    - Accepts any file type as UploadFile
    - Automatically generates unique object name with timestamp
    - Returns upload metadata including ETag and version ID
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a filename")

        result = await minio_service.upload_file(file)

        return ResponseBuilder.success(
            request=request,
            data=result,
            message=f"File '{file.filename}' uploaded successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise BusinessLogicError(f"Failed to upload file: {str(e)}")


@storage_router.delete("/delete", response_model=FileDeleteResponse)
async def delete_file(
    request: Request,
    delete_request: DeleteFileRequest,
    minio_service: Annotated[MinIOService, Depends(get_minio_service)],
):
    """
    Delete a single file from MinIO storage

    - Requires object name in request body
    - Returns 404 if file doesn't exist
    - Returns deletion confirmation with timestamp
    """
    try:
        result = await minio_service.delete_file(delete_request.object_name)

        return ResponseBuilder.success(
            request=request,
            data=result,
            message=f"File '{delete_request.object_name}' deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise BusinessLogicError(f"Failed to delete file: {str(e)}")


@storage_router.post("/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url(
    request: Request,
    url_request: GenerateUrlRequest,
    minio_service: Annotated[MinIOService, Depends(get_minio_service)],
):
    """
    Generate a presigned URL for accessing a file

    - Requires object name and optional expiration time
    - Returns publicly accessible URL that expires after specified time
    - Default expiration is 24 hours, maximum is 7 days (168 hours)
    - Returns 404 if file doesn't exist
    """
    try:
        result = await minio_service.generate_presigned_url(
            url_request.object_name, url_request.expires_in_hours
        )

        return ResponseBuilder.success(
            request=request,
            data=result,
            message=f"Presigned URL generated for '{url_request.object_name}' (expires in {url_request.expires_in_hours} hours)",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise BusinessLogicError(f"Failed to generate presigned URL: {str(e)}")


@storage_router.get("/list", response_model=FileListResponse)
async def list_files(
    request: Request,
    minio_service: Annotated[MinIOService, Depends(get_minio_service)],
    prefix: str = Query(default="", description="Prefix to filter files"),
    limit: int = Query(
        default=100, ge=1, le=1000, description="Maximum number of files to return"
    ),
):
    """
    List files in the MinIO bucket

    - Optional prefix parameter to filter files
    - Configurable limit (1-1000 files, default 100)
    - Returns file metadata including size, last modified, and ETag
    """
    try:
        result = await minio_service.list_files(prefix=prefix, limit=limit)

        message = f"Found {result['count']} files"
        if prefix:
            message += f" with prefix '{prefix}'"

        return ResponseBuilder.success(request=request, data=result, message=message)

    except HTTPException:
        raise
    except Exception as e:
        raise BusinessLogicError(f"Failed to list files: {str(e)}")


@storage_router.get("/health")
async def storage_health_check(
    request: Request,
    minio_service: Annotated[MinIOService, Depends(get_minio_service)],
):
    """
    Health check endpoint for MinIO storage service

    - Verifies MinIO connection and bucket accessibility
    - Returns service status and configuration info
    """
    try:
        # Test basic connectivity by listing one object
        result = await minio_service.list_files(limit=1)

        return ResponseBuilder.success(
            request=request,
            data={
                "status": "healthy",
                "bucket_name": result["bucket_name"],
                "connection": "ok",
            },
            message="Storage service is healthy",
        )

    except Exception as e:
        return ResponseBuilder.error(
            request=request,
            message="Storage service is unhealthy",
            data={"error": str(e)},
        )


@storage_router.post("/citi-automation", response_model=CitiAutomationResponse)
async def citi_automation(
    request: Request,
    automation_request: CitiAutomationRequest,
    citi_service: Annotated[
        CitiProgramAutomationService, Depends(get_citi_automation_service)
    ],
):
    """
    Automate CITI Program certificate download

    - Downloads certificate from provided CITI Program URL
    - Handles login flow automatically using configured credentials
    - Saves certificate to MinIO storage with specified filename and prefix
    - Returns download result and MinIO upload metadata
    """
    try:
        result = await citi_service.download_certificate(
            url=automation_request.url,
            filename=automation_request.filename,
            prefix=automation_request.prefix,
        )

        if result:
            return ResponseBuilder.success(
                request=request,
                data=result,
                message=f"Certificate downloaded and saved to MinIO successfully",
            )
        else:
            return ResponseBuilder.error(
                request=request,
                message="Failed to download certificate",
                data={
                    "success": False,
                    "certificate_downloaded": False,
                    "error_message": "Automation failed",
                },
            )

    except Exception as e:
        raise BusinessLogicError(f"CITI automation failed: {str(e)}")
