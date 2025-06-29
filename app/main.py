from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.utils.logging import get_logger
from app.routers.main_router import main_router

# Initialize the logger
logger = get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Jubi Bot is starting up...")
    yield
    logger.info("Jubi Bot is shutting down...")


def create_application() -> FastAPI:
    """Initialize the FastAPI application with settings and lifespan events."""
    application = FastAPI(
        title=settings.NAME, version=settings.VERSION, lifespan=lifespan
    )

    # Add CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(main_router, prefix=settings.API_PREFIX)

    return application


app = create_application()


@app.get("/")
async def root():
    """Root endpoint to check if the server is running."""
    return {"message": "Welcome to Jubi Bot!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,
        log_level=None,
    )
