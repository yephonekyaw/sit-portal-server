import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from uuid import uuid4

from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile, HTTPException

from app.config.settings import settings


class MinIOService:
    """Service for MinIO object storage operations"""

    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to ensure bucket exists: {str(e)}"
            )

    async def upload_bytes(
        self,
        data: bytes,
        filename: str,
        prefix: Optional[str] = None,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        """
        Upload bytes data to MinIO storage.

        Args:
            data: Raw bytes data to upload
            filename: File name to use in MinIO
            prefix: Optional prefix to add to the object name
            content_type: MIME type of the file

        Returns:
            Dict containing upload information
        """
        from io import BytesIO

        try:
            # Add timestamp prefix to avoid naming conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = (
                f"{prefix}/{uuid4()}_{timestamp}_{filename}"
                if prefix
                else f"{uuid4()}_{timestamp}_{filename}"
            )

            file_size = len(data)
            data_stream = BytesIO(data)

            # Upload file in thread pool since MinIO client is synchronous
            def _upload_sync():
                return self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=data_stream,
                    length=file_size,
                    content_type=content_type,
                )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _upload_sync)

            return {
                "success": True,
                "object_name": object_name,
                "bucket_name": self.bucket_name,
                "size": file_size,
                "content_type": content_type,
                "etag": result.etag,
                "version_id": result.version_id,
                "upload_time": datetime.now().isoformat(),
            }

        except S3Error as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload bytes to MinIO: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during bytes upload: {str(e)}",
            )

    async def upload_file(
        self,
        file: UploadFile,
        prefix: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file to MinIO storage.

        Args:
            file: FastAPI UploadFile object
            filename: Optional custom file name to use in MinIO, defaults to original filename
            prefix: Optional prefix to add to the object name

        Returns:
            Dict containing upload information
        """
        try:
            # Use provided file name or original filename
            if filename is None:
                filename = file.filename

            # Add timestamp prefix to avoid naming conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = (
                f"{prefix}/{uuid4()}_{timestamp}_{filename}"
                if prefix
                else f"{uuid4()}_{timestamp}_{filename}"
            )

            # Get file size from FastAPI UploadFile
            if file.size is None:
                raise HTTPException(
                    status_code=400, detail="File size is required for upload"
                )

            file_size = file.size

            # Upload file in thread pool since MinIO client is synchronous
            def _upload_sync():
                return self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=file.file,
                    length=file_size,
                    content_type=file.content_type or "application/octet-stream",
                )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _upload_sync)

            return {
                "success": True,
                "object_name": object_name,
                "bucket_name": self.bucket_name,
                "size": file_size,
                "content_type": file.content_type,
                "etag": result.etag,
                "version_id": result.version_id,
                "upload_time": datetime.now().isoformat(),
            }

        except S3Error as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file to MinIO: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error during file upload: {str(e)}"
            )

    async def delete_file(self, object_name: str) -> Dict[str, Any]:
        """
        Delete a single file from MinIO storage.

        Args:
            object_name: Name of the object to delete

        Returns:
            Dict containing deletion result
        """
        try:

            def _delete_sync():
                self.client.remove_object(self.bucket_name, object_name)
                return True

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _delete_sync)

            return {
                "success": True,
                "object_name": object_name,
                "bucket_name": self.bucket_name,
                "deleted_at": datetime.now().isoformat(),
            }

        except S3Error as e:
            if e.code == "NoSuchKey":
                raise HTTPException(
                    status_code=404,
                    detail=f"File '{object_name}' not found in bucket '{self.bucket_name}'",
                )
            raise HTTPException(
                status_code=500, detail=f"Failed to delete file from MinIO: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during file deletion: {str(e)}",
            )

    async def generate_presigned_url(
        self, object_name: str, expires_in_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for accessing a file.

        Args:
            object_name: Name of the object to generate URL for
            expires_in_hours: URL expiration time in hours (default: 24 hours)

        Returns:
            Dict containing the presigned URL and metadata
        """
        try:
            # Check if object exists first
            def _check_object_sync():
                try:
                    return self.client.stat_object(self.bucket_name, object_name)
                except S3Error as e:
                    if e.code == "NoSuchKey":
                        raise HTTPException(
                            status_code=404,
                            detail=f"File '{object_name}' not found in bucket '{self.bucket_name}'",
                        )
                    raise e

            loop = asyncio.get_event_loop()
            object_stat = await loop.run_in_executor(None, _check_object_sync)

            # Generate presigned URL
            def _generate_url_sync():
                return self.client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    expires=timedelta(hours=expires_in_hours),
                )

            presigned_url = await loop.run_in_executor(None, _generate_url_sync)
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)

            return {
                "success": True,
                "object_name": object_name,
                "bucket_name": self.bucket_name,
                "presigned_url": presigned_url,
                "expires_at": expires_at.isoformat(),
                "expires_in_hours": expires_in_hours,
                "file_size": object_stat.size,
                "content_type": object_stat.content_type,
                "last_modified": (
                    object_stat.last_modified.isoformat()
                    if object_stat.last_modified
                    else None
                ),
                "etag": object_stat.etag,
            }

        except HTTPException:
            raise
        except S3Error as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to generate presigned URL: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error generating presigned URL: {str(e)}",
            )

    async def get_file(self, object_name: str) -> Dict[str, Any]:
        """
        Retrieve a file from MinIO storage.

        Args:
            object_name: Name of the object to retrieve

        Returns:
            Dict containing file data and metadata
        """
        try:

            def _get_object_sync():
                try:
                    # Get object metadata first
                    object_stat = self.client.stat_object(self.bucket_name, object_name)

                    # Get object data
                    response = self.client.get_object(self.bucket_name, object_name)
                    data = response.read()
                    response.close()
                    response.release_conn()

                    return data, object_stat
                except S3Error as e:
                    if e.code == "NoSuchKey":
                        raise HTTPException(
                            status_code=404,
                            detail=f"File '{object_name}' not found in bucket '{self.bucket_name}'",
                        )
                    raise e

            loop = asyncio.get_event_loop()
            file_data, object_stat = await loop.run_in_executor(None, _get_object_sync)

            return {
                "success": True,
                "object_name": object_name,
                "bucket_name": self.bucket_name,
                "data": file_data,
                "size": object_stat.size,
                "content_type": object_stat.content_type,
                "last_modified": (
                    object_stat.last_modified.isoformat()
                    if object_stat.last_modified
                    else None
                ),
                "etag": object_stat.etag,
            }

        except HTTPException:
            raise
        except S3Error as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve file from MinIO: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error retrieving file: {str(e)}"
            )

    async def list_files(self, prefix: str = "", limit: int = 100) -> Dict[str, Any]:
        """
        List files in the MinIO bucket.

        Args:
            prefix: Optional prefix to filter files
            limit: Maximum number of files to return

        Returns:
            Dict containing list of files and metadata
        """
        try:

            def _list_objects_sync():
                objects = []
                for obj in self.client.list_objects(
                    self.bucket_name, prefix=prefix, recursive=True
                ):
                    objects.append(
                        {
                            "object_name": obj.object_name,
                            "size": obj.size,
                            "last_modified": (
                                obj.last_modified.isoformat()
                                if obj.last_modified
                                else None
                            ),
                            "etag": obj.etag,
                            "content_type": getattr(obj, "content_type", None),
                        }
                    )
                    if len(objects) >= limit:
                        break
                return objects

            loop = asyncio.get_event_loop()
            objects = await loop.run_in_executor(None, _list_objects_sync)

            return {
                "success": True,
                "bucket_name": self.bucket_name,
                "prefix": prefix,
                "files": objects,
                "count": len(objects),
                "limit": limit,
            }

        except S3Error as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to list files: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error listing files: {str(e)}"
            )


def get_minio_service() -> MinIOService:
    """Dependency to get MinIO service instance"""
    return MinIOService()
