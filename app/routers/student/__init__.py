from fastapi import APIRouter

from .submissions import submissions_router

student_router = APIRouter()

# Include sub-routers
student_router.include_router(
    submissions_router, prefix="/submissions", tags=["Student - Submissions"]
)
