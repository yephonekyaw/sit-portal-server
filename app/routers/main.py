from fastapi import APIRouter

from app.routers.staff import staff_router
from app.routers.student import student_router
from app.routers.shared import shared_router

main_router = APIRouter()

# Include domain-based routers
main_router.include_router(staff_router, prefix="/staff", tags=["Staff"])
main_router.include_router(student_router, prefix="/student", tags=["Student"])
main_router.include_router(shared_router, prefix="/shared", tags=["Shared Services"])
