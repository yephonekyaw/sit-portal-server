from fastapi import APIRouter

from .requirements import requirement_router

student_router = APIRouter()

# Include sub-routers
student_router.include_router(
    requirement_router, prefix="/requirements", tags=["Student - Requirements"]
)
