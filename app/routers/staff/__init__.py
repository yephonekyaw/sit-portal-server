from fastapi import APIRouter

from .students import students_router
from .submissions import submissions_router

staff_router = APIRouter()

# Include sub-routers
staff_router.include_router(students_router, prefix="/students", tags=["Staff - Student Management"])
staff_router.include_router(submissions_router, prefix="/submissions", tags=["Staff - Submission Management"])