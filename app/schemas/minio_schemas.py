from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response model for file upload operations"""
    
    success: bool = Field(..., description="Whether the upload was successful")
    object_name: str = Field(..., description="Name of the uploaded object in MinIO")
    bucket_name: str = Field(..., description="Name of the MinIO bucket")
    size: int = Field(..., description="Size of the uploaded file in bytes")
    content_type: Optional[str] = Field(None, description="MIME type of the uploaded file")
    etag: str = Field(..., description="ETag of the uploaded object")
    version_id: Optional[str] = Field(None, description="Version ID of the uploaded object")
    upload_time: str = Field(..., description="Timestamp when the file was uploaded")


class MultipleFileUploadResponse(BaseModel):
    """Response model for multiple file upload operations"""
    
    success: bool = Field(..., description="Whether all uploads were successful")
    uploaded_files: List[FileUploadResponse] = Field(..., description="List of successfully uploaded files")
    errors: List[Dict[str, Any]] = Field(..., description="List of upload errors")
    total_files: int = Field(..., description="Total number of files attempted to upload")
    successful_uploads: int = Field(..., description="Number of successful uploads")
    failed_uploads: int = Field(..., description="Number of failed uploads")


class FileDeleteResponse(BaseModel):
    """Response model for file deletion operations"""
    
    success: bool = Field(..., description="Whether the deletion was successful")
    object_name: str = Field(..., description="Name of the deleted object")
    bucket_name: str = Field(..., description="Name of the MinIO bucket")
    deleted_at: str = Field(..., description="Timestamp when the file was deleted")


class MultipleFileDeleteResponse(BaseModel):
    """Response model for multiple file deletion operations"""
    
    success: bool = Field(..., description="Whether all deletions were successful")
    deleted_files: List[FileDeleteResponse] = Field(..., description="List of successfully deleted files")
    errors: List[Dict[str, Any]] = Field(..., description="List of deletion errors")
    total_files: int = Field(..., description="Total number of files attempted to delete")
    successful_deletions: int = Field(..., description="Number of successful deletions")
    failed_deletions: int = Field(..., description="Number of failed deletions")


class PresignedUrlResponse(BaseModel):
    """Response model for presigned URL generation"""
    
    success: bool = Field(..., description="Whether the URL generation was successful")
    object_name: str = Field(..., description="Name of the object")
    bucket_name: str = Field(..., description="Name of the MinIO bucket")
    presigned_url: str = Field(..., description="The presigned URL for accessing the file")
    expires_at: str = Field(..., description="Timestamp when the URL expires")
    expires_in_hours: int = Field(..., description="Number of hours until expiration")
    file_size: int = Field(..., description="Size of the file in bytes")
    content_type: Optional[str] = Field(None, description="MIME type of the file")
    last_modified: str = Field(..., description="Timestamp when the file was last modified")
    etag: str = Field(..., description="ETag of the object")


class MultiplePresignedUrlResponse(BaseModel):
    """Response model for multiple presigned URL generation"""
    
    success: bool = Field(..., description="Whether all URL generations were successful")
    presigned_urls: List[PresignedUrlResponse] = Field(..., description="List of successfully generated URLs")
    errors: List[Dict[str, Any]] = Field(..., description="List of URL generation errors")
    total_files: int = Field(..., description="Total number of files attempted to generate URLs for")
    successful_urls: int = Field(..., description="Number of successful URL generations")
    failed_urls: int = Field(..., description="Number of failed URL generations")
    expires_in_hours: int = Field(..., description="Number of hours until expiration")


class FileInfo(BaseModel):
    """Model for file information"""
    
    object_name: str = Field(..., description="Name of the object in MinIO")
    size: int = Field(..., description="Size of the file in bytes")
    last_modified: str = Field(..., description="Timestamp when the file was last modified")
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


class DeleteMultipleFilesRequest(BaseModel):
    """Request model for multiple file deletion"""
    
    object_names: List[str] = Field(..., description="List of object names to delete", min_length=1)


class GenerateUrlRequest(BaseModel):
    """Request model for presigned URL generation"""
    
    object_name: str = Field(..., description="Name of the object to generate URL for")
    expires_in_hours: int = Field(default=24, description="Number of hours until URL expires", ge=1, le=168)  # Max 7 days


class GenerateMultipleUrlsRequest(BaseModel):
    """Request model for multiple presigned URL generation"""
    
    object_names: List[str] = Field(..., description="List of object names to generate URLs for", min_length=1)
    expires_in_hours: int = Field(default=24, description="Number of hours until URLs expire", ge=1, le=168)  # Max 7 days


class ListFilesRequest(BaseModel):
    """Request model for file listing"""
    
    prefix: str = Field(default="", description="Prefix to filter files")
    limit: int = Field(default=100, description="Maximum number of files to return", ge=1, le=1000)