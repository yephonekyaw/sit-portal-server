from fastapi import APIRouter

from app.routers.staff_router import staff_router
from app.routers.student_router import student_router

main_router = APIRouter()
main_router.include_router(staff_router, prefix="/staff", tags=["staff"])
main_router.include_router(student_router, prefix="/student", tags=["student"])


# from app.config.settings import settings
# from pathlib import Path


# @main_router.get("/")
# async def root():
#     try:
#         # Read file content as bytes first
#         file_content = Path("./files/mock_pic_1.png").resolve().read_bytes()

#         # Pass bytes directly to extractor
#         extractor = TextExtractionProvider()
#         result = await extractor.extract_text(file_content, "mock_pic_2.png")

#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
