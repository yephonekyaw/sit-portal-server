from fastapi import APIRouter

from app.routers.staff import staff_router
from app.routers.student import student_router

main_router = APIRouter()
main_router.include_router(staff_router, prefix="/staff", tags=["Staff"])
main_router.include_router(student_router, prefix="/student", tags=["Student"])
