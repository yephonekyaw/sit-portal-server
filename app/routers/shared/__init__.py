from fastapi import APIRouter

from .storage import storage_router
from .auth import auth_router
from .health import health_router

shared_router = APIRouter()

# Include sub-routers
shared_router.include_router(storage_router, prefix="/storage", tags=["File Storage"])
shared_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
shared_router.include_router(health_router, prefix="/health", tags=["Health Checks"])