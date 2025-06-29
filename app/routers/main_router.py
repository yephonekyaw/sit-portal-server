from fastapi import APIRouter, HTTPException
from fastapi import UploadFile
from app.providers.text_extractor import TextExtractor

main_router = APIRouter()


from app.config.settings import settings
from pathlib import Path


@main_router.get("/")
async def root():
    try:
        # Read file content as bytes first
        file_content = Path("./files/mock_pic_1.png").resolve().read_bytes()

        # Pass bytes directly to extractor
        extractor = TextExtractor()
        result = await extractor.extract_text(file_content, "mock_pic_2.png")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
