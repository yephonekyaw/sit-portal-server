# from typing import Annotated, List
# from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, Query

# from app.services.minio_service import MinIOService
# from app.schemas.minio_schemas import (
#     FileUploadResponse,
#     MultipleFileUploadResponse,
#     FileDeleteResponse,
#     MultipleFileDeleteResponse,
#     PresignedUrlResponse,
#     MultiplePresignedUrlResponse,
#     FileListResponse,
#     DeleteFileRequest,
#     DeleteMultipleFilesRequest,
#     GenerateUrlRequest,
#     GenerateMultipleUrlsRequest,
# )
# from app.utils.responses import ResponseBuilder
# from app.utils.errors import BusinessLogicError

# minio_router = APIRouter()


# def get_minio_service() -> MinIOService:
#     """Dependency to get MinIO service instance"""
#     return MinIOService()


# @minio_router.post("/upload", response_model=FileUploadResponse)
# async def upload_file(
#     request: Request,
#     minio_service: Annotated[MinIOService, Depends(get_minio_service)],
#     file: UploadFile = File(...),
# ):
#     """
#     Upload a single file to MinIO storage

#     - Accepts any file type as UploadFile
#     - Automatically generates unique object name with timestamp
#     - Returns upload metadata including ETag and version ID
#     """
#     try:
#         if not file.filename:
#             raise HTTPException(status_code=400, detail="File must have a filename")

#         result = await minio_service.upload_file(file)

#         return ResponseBuilder.success(
#             request=request,
#             data=result,
#             message=f"File '{file.filename}' uploaded successfully",
#         )

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise BusinessLogicError(f"Failed to upload file: {str(e)}")


# @minio_router.post("/upload-multiple", response_model=MultipleFileUploadResponse)
# async def upload_multiple_files(
#     request: Request,
#     minio_service: Annotated[MinIOService, Depends(get_minio_service)],
#     files: List[UploadFile] = File(...),
# ):
#     """
#     Upload multiple files to MinIO storage

#     - Accepts multiple files as UploadFile list
#     - Processes all files and returns detailed results
#     - Continues processing even if some files fail
#     """
#     try:
#         if not files:
#             raise HTTPException(
#                 status_code=400, detail="At least one file must be provided"
#             )

#         # Validate all files have filenames
#         for file in files:
#             if not file.filename:
#                 raise HTTPException(
#                     status_code=400, detail="All files must have filenames"
#                 )

#         result = await minio_service.upload_multiple_files(files)

#         message = (
#             f"Uploaded {result['successful_uploads']} of {result['total_files']} files"
#         )
#         if result["failed_uploads"] > 0:
#             message += f" ({result['failed_uploads']} failed)"

#         return ResponseBuilder.success(request=request, data=result, message=message)

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise BusinessLogicError(f"Failed to upload files: {str(e)}")


# @minio_router.delete("/delete", response_model=FileDeleteResponse)
# async def delete_file(
#     request: Request,
#     delete_request: DeleteFileRequest,
#     minio_service: Annotated[MinIOService, Depends(get_minio_service)],
# ):
#     """
#     Delete a single file from MinIO storage

#     - Requires object name in request body
#     - Returns 404 if file doesn't exist
#     - Returns deletion confirmation with timestamp
#     """
#     try:
#         result = await minio_service.delete_file(delete_request.object_name)

#         return ResponseBuilder.success(
#             request=request,
#             data=result,
#             message=f"File '{delete_request.object_name}' deleted successfully",
#         )

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise BusinessLogicError(f"Failed to delete file: {str(e)}")


# @minio_router.delete("/delete-multiple", response_model=MultipleFileDeleteResponse)
# async def delete_multiple_files(
#     request: Request,
#     delete_request: DeleteMultipleFilesRequest,
#     minio_service: Annotated[MinIOService, Depends(get_minio_service)],
# ):
#     """
#     Delete multiple files from MinIO storage

#     - Requires list of object names in request body
#     - Processes all files and returns detailed results
#     - Continues processing even if some files fail or don't exist
#     """
#     try:
#         result = await minio_service.delete_multiple_files(delete_request.object_names)

#         message = (
#             f"Deleted {result['successful_deletions']} of {result['total_files']} files"
#         )
#         if result["failed_deletions"] > 0:
#             message += f" ({result['failed_deletions']} failed)"

#         return ResponseBuilder.success(request=request, data=result, message=message)

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise BusinessLogicError(f"Failed to delete files: {str(e)}")


# @minio_router.post("/presigned-url", response_model=PresignedUrlResponse)
# async def generate_presigned_url(
#     request: Request,
#     url_request: GenerateUrlRequest,
#     minio_service: Annotated[MinIOService, Depends(get_minio_service)],
# ):
#     """
#     Generate a presigned URL for accessing a file

#     - Requires object name and optional expiration time
#     - Returns publicly accessible URL that expires after specified time
#     - Default expiration is 24 hours, maximum is 7 days (168 hours)
#     - Returns 404 if file doesn't exist
#     """
#     try:
#         result = await minio_service.generate_presigned_url(
#             url_request.object_name, url_request.expires_in_hours
#         )

#         return ResponseBuilder.success(
#             request=request,
#             data=result,
#             message=f"Presigned URL generated for '{url_request.object_name}' (expires in {url_request.expires_in_hours} hours)",
#         )

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise BusinessLogicError(f"Failed to generate presigned URL: {str(e)}")


# @minio_router.post("/presigned-urls", response_model=MultiplePresignedUrlResponse)
# async def generate_multiple_presigned_urls(
#     request: Request,
#     urls_request: GenerateMultipleUrlsRequest,
#     minio_service: Annotated[MinIOService, Depends(get_minio_service)],
# ):
#     """
#     Generate presigned URLs for multiple files

#     - Requires list of object names and optional expiration time
#     - Returns publicly accessible URLs for all existing files
#     - Continues processing even if some files don't exist
#     - Default expiration is 24 hours, maximum is 7 days (168 hours)
#     """
#     try:
#         result = await minio_service.generate_multiple_presigned_urls(
#             urls_request.object_names, urls_request.expires_in_hours
#         )

#         message = f"Generated {result['successful_urls']} of {result['total_files']} presigned URLs"
#         if result["failed_urls"] > 0:
#             message += f" ({result['failed_urls']} failed)"

#         return ResponseBuilder.success(request=request, data=result, message=message)

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise BusinessLogicError(f"Failed to generate presigned URLs: {str(e)}")


# @minio_router.get("/list", response_model=FileListResponse)
# async def list_files(
#     request: Request,
#     minio_service: Annotated[MinIOService, Depends(get_minio_service)],
#     prefix: str = Query(default="", description="Prefix to filter files"),
#     limit: int = Query(
#         default=100, ge=1, le=1000, description="Maximum number of files to return"
#     ),
# ):
#     """
#     List files in the MinIO bucket

#     - Optional prefix parameter to filter files
#     - Configurable limit (1-1000 files, default 100)
#     - Returns file metadata including size, last modified, and ETag
#     """
#     try:
#         result = await minio_service.list_files(prefix=prefix, limit=limit)

#         message = f"Found {result['count']} files"
#         if prefix:
#             message += f" with prefix '{prefix}'"

#         return ResponseBuilder.success(request=request, data=result, message=message)

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise BusinessLogicError(f"Failed to list files: {str(e)}")


# @minio_router.get("/health")
# async def minio_health_check(
#     request: Request,
#     minio_service: Annotated[MinIOService, Depends(get_minio_service)],
# ):
#     """
#     Health check endpoint for MinIO service

#     - Verifies MinIO connection and bucket accessibility
#     - Returns service status and configuration info
#     """
#     try:
#         # Test basic connectivity by listing one object
#         result = await minio_service.list_files(limit=1)

#         return ResponseBuilder.success(
#             request=request,
#             data={
#                 "status": "healthy",
#                 "bucket_name": result["bucket_name"],
#                 "connection": "ok",
#             },
#             message="MinIO service is healthy",
#         )

#     except Exception as e:
#         return ResponseBuilder.error(
#             request=request,
#             message="MinIO service is unhealthy",
#             data={"error": str(e)},
#         )
