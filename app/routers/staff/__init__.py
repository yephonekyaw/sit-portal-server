from fastapi import APIRouter

from .students import students_router
from .submissions import submissions_router
from .programs import programs_router
from .certificates import certificates_router
from .program_requirements import program_requirements_router
from .program_requirement_schedules import program_requirement_schedules_router

staff_router = APIRouter()

# Include sub-routers
staff_router.include_router(students_router, prefix="/students", tags=["Staff - Student Management"])
staff_router.include_router(submissions_router, prefix="/submissions", tags=["Staff - Submission Management"])
staff_router.include_router(programs_router, prefix="/programs", tags=["Staff - Program Management"])
staff_router.include_router(certificates_router, prefix="/certificates", tags=["Staff - Certificate Management"])
staff_router.include_router(program_requirements_router, prefix="/program-requirements", tags=["Staff - Program Requirements Management"])
staff_router.include_router(program_requirement_schedules_router, prefix="/program-requirement-schedules", tags=["Staff - Program Requirement Schedules Management"])