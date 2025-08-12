from fastapi import APIRouter

from .auth import auth_router
from .health import health_router

shared_router = APIRouter()

# Include sub-routers
shared_router.include_router(
    auth_router, prefix="/auth", tags=["Shared - Authentication"]
)
shared_router.include_router(
    health_router, prefix="/health", tags=["Shared - Health Checks"]
)
