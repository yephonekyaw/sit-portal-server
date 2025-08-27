import asyncio
import pymupdf
import re
from pathlib import Path
from typing import Dict, Any, Optional
from google.cloud import documentai_v1

from app.config.settings import settings


class DocumentService:
    """Service for extracting text and verification URLs from documents"""

    def __init__(self):
        self.supported_image_extensions = {
            "png",
            "jpg",
            "jpeg",
            "tiff",
            "tif",
            "bmp",
            "webp",
        }
        self.client = (
            documentai_v1.DocumentProcessorServiceClient.from_service_account_json(
                settings.GOOGLE_APPLICATION_CREDENTIALS
            )
        )
        self.processor_name = (
            f"projects/{settings.GOOGLE_CLOUD_PROJECT_ID}/"
            f"locations/{settings.DOCUMENT_AI_LOCATION}/"
            f"processors/{settings.DOCUMENT_AI_PROCESSOR_ID}"
        )

    async def extract_text(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract text from file content asynchronously."""
        file_extension = Path(filename).suffix.lower().lstrip(".")

        try:
            if file_extension in self.supported_image_extensions:
                result = await self._extract_with_document_ai(file_content, filename)
            elif file_extension == "pdf":
                result = await self._extract_from_pdf(file_content, filename)
            else:
                return self._error_response(
                    f"Unsupported file format: .{file_extension}"
                )

            # Clean the extracted text and extract verification URL
            if result["success"]:
                result["text"] = self._clean_text(result["text"])
                result["verification_url"] = self._extract_verification_url(
                    result["text"]
                )

            return result

        except Exception as e:
            return self._error_response(str(e))

    def _clean_text(self, text: str) -> str:
        """Clean and normalize the OCR text."""
        # Remove extra whitespace and normalize line breaks
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    def _extract_verification_url(self, text: str) -> Optional[str]:
        """Extract verification url from certificate text."""
        patterns = [
            # Pattern for: Verify at www.citiprogram.org/verify/?...
            r"Verify at\s*((?:https?://)?[^\s]+citiprogram\.org[^\s]*)",
            # Pattern for: verify at followed by URL
            r"verify.*?at\s*((?:https?://)?[^\s]+citiprogram\.org[^\s]*)",
            # Direct URL pattern
            r"((?:https?://)?(?:www\.)?citiprogram\.org/verify/[^\s]*)",
            # More flexible verification URL pattern
            r"((?:https?://)?[^\s]*citiprogram\.org[^\s]*verify[^\s]*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url = match.group(1)

                # Clean up the URL
                url = re.sub(r"[.,;!?\)\]]+$", "", url)  # Remove trailing punctuation

                # Add https:// if missing
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url

                # Validate it contains the key components
                if "citiprogram.org" in url and ("verify" in url or "?" in url):
                    return url

        return None

    async def _extract_from_pdf(self, pdf_data: bytes, filename: str) -> Dict[str, Any]:
        """Try PyMuPDF first, Document AI if no meaningful text."""
        # Try PyMuPDF first (run in thread pool since it's CPU-bound)
        result = await self._extract_with_pymupdf(pdf_data)

        # Use Document AI if PyMuPDF failed or text is poor quality
        if not result["success"] or len(result["text"].strip()) < 50:
            return await self._extract_with_document_ai(pdf_data, filename)

        result["method"] = "pymupdf"
        return result

    async def _extract_with_pymupdf(self, pdf_data: bytes) -> Dict[str, Any]:
        """Extract text using PyMuPDF in thread pool."""

        def _pymupdf_sync(pdf_data: bytes) -> Dict[str, Any]:
            try:
                doc = pymupdf.open(stream=pdf_data, filetype="pdf")
                all_text = []
                page_count = len(doc)

                for page_num in range(page_count):
                    page = doc.load_page(page_num)
                    text = page.get_textpage().extractTEXT()
                    if text.strip():
                        all_text.append(text.strip())

                full_text = "\n\n".join(all_text)
                doc.close()

                return {
                    "text": full_text,
                    "success": len(full_text.strip()) > 0,
                    "pages": page_count,
                    "confidence": 99 if full_text.strip() else 0,
                }

            except Exception as e:
                return {
                    "text": "",
                    "success": False,
                    "pages": 0,
                    "confidence": 0,
                    "error": f"PyMuPDF failed: {str(e)}",
                }

        # Run PyMuPDF in thread pool since it's CPU-bound
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _pymupdf_sync, pdf_data)

    async def _extract_with_document_ai(
        self, file_data: bytes, filename: str
    ) -> Dict[str, Any]:
        """Extract text using Document AI asynchronously."""

        def _document_ai_sync(file_data: bytes, filename: str) -> Dict[str, Any]:
            try:
                mime_type = self._get_mime_type(filename)

                request = documentai_v1.ProcessRequest(
                    name=self.processor_name,
                    raw_document=documentai_v1.RawDocument(
                        content=file_data, mime_type=mime_type
                    ),
                )

                result = self.client.process_document(request=request)
                document = result.document

                return {
                    "text": document.text,
                    "success": len(document.text.strip()) > 0,
                    "method": "document_ai",
                    "pages": len(document.pages),
                    "confidence": 85,
                }

            except Exception as e:
                return {
                    "text": "",
                    "success": False,
                    "method": "error",
                    "pages": 0,
                    "confidence": 0,
                    "error": f"Document AI failed: {str(e)}",
                }

        # Run Document AI in thread pool since it's I/O-bound but blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _document_ai_sync, file_data, filename)

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename."""
        file_ext = Path(filename).suffix.lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }
        return mime_types.get(file_ext, "application/octet-stream")

    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            "text": "",
            "success": False,
            "method": "error",
            "pages": 0,
            "confidence": 0,
            "error": error_message,
        }


def get_document_service() -> DocumentService:
    """Dependency to get Document service instance."""
    return DocumentService()
