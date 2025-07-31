from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response model for file upload operations"""

    success: bool = Field(..., description="Whether the upload was successful")
    object_name: str = Field(..., description="Name of the uploaded object in MinIO")
    bucket_name: str = Field(..., description="Name of the MinIO bucket")
    size: int = Field(..., description="Size of the uploaded file in bytes")
    content_type: Optional[str] = Field(
        None, description="MIME type of the uploaded file"
    )
    etag: str = Field(..., description="ETag of the uploaded object")
    version_id: Optional[str] = Field(
        None, description="Version ID of the uploaded object"
    )
    upload_time: str = Field(..., description="Timestamp when the file was uploaded")


class FileDeleteResponse(BaseModel):
    """Response model for file deletion operations"""

    success: bool = Field(..., description="Whether the deletion was successful")
    object_name: str = Field(..., description="Name of the deleted object")
    bucket_name: str = Field(..., description="Name of the MinIO bucket")
    deleted_at: str = Field(..., description="Timestamp when the file was deleted")


class PresignedUrlResponse(BaseModel):
    """Response model for presigned URL generation"""

    success: bool = Field(..., description="Whether the URL generation was successful")
    object_name: str = Field(..., description="Name of the object")
    bucket_name: str = Field(..., description="Name of the MinIO bucket")
    presigned_url: str = Field(
        ..., description="The presigned URL for accessing the file"
    )
    expires_at: str = Field(..., description="Timestamp when the URL expires")
    expires_in_hours: int = Field(..., description="Number of hours until expiration")
    file_size: int = Field(..., description="Size of the file in bytes")
    content_type: Optional[str] = Field(None, description="MIME type of the file")
    last_modified: str = Field(
        ..., description="Timestamp when the file was last modified"
    )
    etag: str = Field(..., description="ETag of the object")


class FileInfo(BaseModel):
    """Model for file information"""

    object_name: str = Field(..., description="Name of the object in MinIO")
    size: int = Field(..., description="Size of the file in bytes")
    last_modified: str = Field(
        ..., description="Timestamp when the file was last modified"
    )
    etag: str = Field(..., description="ETag of the object")
    content_type: Optional[str] = Field(None, description="MIME type of the file")


class FileListResponse(BaseModel):
    """Response model for file listing operations"""

    success: bool = Field(..., description="Whether the listing was successful")
    bucket_name: str = Field(..., description="Name of the MinIO bucket")
    prefix: str = Field(..., description="Prefix used for filtering files")
    files: List[FileInfo] = Field(..., description="List of files in the bucket")
    count: int = Field(..., description="Number of files returned")
    limit: int = Field(..., description="Maximum number of files requested")


class DeleteFileRequest(BaseModel):
    """Request model for single file deletion"""

    object_name: str = Field(..., description="Name of the object to delete")


class GenerateUrlRequest(BaseModel):
    """Request model for presigned URL generation"""

    object_name: str = Field(..., description="Name of the object to generate URL for")
    expires_in_hours: int = Field(
        default=24, description="Number of hours until URL expires", ge=1, le=168
    )  # Max 7 days


class ListFilesRequest(BaseModel):
    """Request model for file listing"""

    prefix: str = Field(default="", description="Prefix to filter files")
    limit: int = Field(
        default=100, description="Maximum number of files to return", ge=1, le=1000
    )


class CitiAutomationRequest(BaseModel):
    """Request model for CITI automation"""

    url: str = Field(..., description="CITI Program verification URL")
    filename: Optional[str] = Field(
        default="citi_certificate.pdf",
        description="Custom filename for the certificate",
    )
    prefix: Optional[str] = Field(
        default="temp", description="Prefix for MinIO object name"
    )


class CitiAutomationResponse(BaseModel):
    """Response model for CITI automation"""

    success: bool = Field(..., description="Whether the automation was successful")
    certificate_downloaded: bool = Field(
        ..., description="Whether the certificate was downloaded"
    )
    minio_upload: Optional[FileUploadResponse] = Field(
        None, description="MinIO upload result"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if automation failed"
    )
