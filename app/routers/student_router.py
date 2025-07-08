from fastapi import APIRouter, UploadFile, Request
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.providers.text_extraction_provider import TextExtractionProvider
from app.utils.responses import ResponseBuilder
from app.utils.responses import ApiResponse


student_router = APIRouter()


@student_router.post("/extract-text", response_model=ApiResponse)
async def extract_text(file: UploadFile, request: Request):
    try:
        file_content = await file.read()
        extractor = TextExtractionProvider()
        result = await extractor.extract_text(file_content, str(file.filename))
        return ResponseBuilder.success(
            request=request,
            data=result,
            message="Text extraction completed successfully.",
        )
    except Exception as e:
        raise StarletteHTTPException(status_code=500, detail=str(e))
