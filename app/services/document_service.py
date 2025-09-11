import re
import pymupdf
import pytesseract
from PIL import Image
from PIL.ImageFile import ImageFile
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional


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
        self.tesseract_config = r"--oem 1 --psm 3"

    async def extract_text(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract text from file content asynchronously."""
        file_extension = Path(filename).suffix.lower().lstrip(".")

        try:
            if file_extension in self.supported_image_extensions:
                result = await self._extract_with_tesseract(file_content, filename)
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
        result = await self._extract_with_pymupdf(pdf_data)

        # Use Tesseract OCR if PyMuPDF failed or text is poor quality
        if not result["success"] or len(result["text"].strip()) < 50:
            return await self._extract_with_tesseract(pdf_data, filename)

        result["method"] = "pymupdf"
        return result

    async def _extract_with_pymupdf(self, pdf_data: bytes) -> Dict[str, Any]:
        """Extract text using PyMuPDF in thread pool."""

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
                "method": "pymupdf",
                "pages": page_count,
                "confidence": 99.00 if full_text.strip() else 0.00,
            }

        except Exception as e:
            return {
                "text": "",
                "success": False,
                "method": "pymupdf",
                "pages": 0,
                "confidence": 0,
                "error": f"PyMuPDF failed: {str(e)}",
            }

    async def _extract_with_tesseract(
        self, file_data: bytes, filename: str
    ) -> Dict[str, Any]:
        try:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

            mime_type = self._get_mime_type(filename)

            pil_img_data: None | ImageFile = None

            if mime_type == "application/pdf":
                # If it's a PDF, convert first page to a Pillow image
                doc = pymupdf.open(stream=file_data, filetype="pdf")
                pdf_page = doc.load_page(0)
                pixmap = pdf_page.get_pixmap(dpi=300)  # type: ignore
                pixmap = pymupdf.Pixmap(pixmap, 0) if pixmap.alpha else pixmap

                img_data = pixmap.pil_tobytes(format="png")
                pil_img_data = Image.open(BytesIO(img_data))
                doc.close()
                pdf_page = None  # Free memory
                pixmap = None  # Free memory
            else:
                # If it's an image, open directly with Pillow
                pil_img_data = Image.open(BytesIO(file_data))

            # Get OCR results as a DataFrame
            df = pytesseract.image_to_data(
                pil_img_data,
                output_type=pytesseract.Output.DATAFRAME,
                config=self.tesseract_config,
            )
            df = df.loc[df["conf"] > 70, ["text", "conf"]]
            text = " ".join(df["text"].fillna("").str.strip())
            confidence = df["conf"].mean()

            return {
                "text": text,
                "success": len(text.strip()) > 0,
                "method": "tesseract",
                "pages": 1,
                "confidence": confidence.round(2),
            }

        except Exception as e:
            return {
                "text": "",
                "success": False,
                "method": "tesseract",
                "pages": 0,
                "confidence": 0,
                "error": f"Tesseract OCR failed: {str(e)}",
            }

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
            "method": "unknown",
            "pages": 0,
            "confidence": 0,
            "error": error_message,
        }


def get_document_service() -> DocumentService:
    """Dependency to get Document service instance."""
    return DocumentService()
