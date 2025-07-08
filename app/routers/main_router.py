from fastapi import APIRouter

from app.providers.text_extraction_provider import TextExtractionProvider
from app.routers.staff_router import staff_router
from app.routers.student_router import student_router

main_router = APIRouter()
main_router.include_router(staff_router, prefix="/staff", tags=["staff"])
main_router.include_router(student_router, prefix="/student", tags=["student"])
