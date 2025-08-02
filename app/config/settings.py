from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    ENVIRONMENT: str = "development"
    NAME: str = "<your-app-name>"
    VERSION: str = "<your-app-version>"
    API_PREFIX: str = "<your-api-prefix>"
    WEB_SOCKET_PREFIX: str = "<your-web-sockets-prefix>"
    """Pydantic v2 doesn't support parsing List[str] from a plain comma-separated string by default anymore."""
    ALLOWED_HOSTS: Union[str, List[str]] = "<your-allowed-host-1,<your-allowed-host-2>>"
    LOG_LEVEL: str = "<your-log-level>"

    # Google Cloud
    GEMINI_API_KEY: str = "<your-gemini-api-key>"
    GEMINI_MODEL: str = "<your-gemini-model-name>"
    GOOGLE_APPLICATION_CREDENTIALS: str = (
        "<path-to-your-google-application-credentials-json>"
    )
    GOOGLE_CLOUD_PROJECT_ID: str = "<your-google-cloud-project-id>"
    DOCUMENT_AI_PROCESSOR_ID: str = "<your-document-ai-processor-id>"
    DOCUMENT_AI_LOCATION: str = "<your-document-ai-location>"

    # Database
    DATABASE_URL: str = "<your-database-url>"

    # LangChain & LangSmith
    LANGSMITH_TRACING: bool = True
    LANGSMITH_ENDPOINT: str = "<your-langsith-endpoint>"
    LANGSMITH_API_KEY: str = "<your-langsith-api-key>"
    LANGSMITH_PROJECT: str = "<your-langsith-project>"

    # Authentication & Security
    JWT_SECRET_KEY: str = "<your-jwt-secret-key>"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # MinIO Object Storage
    MINIO_ENDPOINT: str = "<your-minio-endpoint>"
    MINIO_ACCESS_KEY: str = "<your-minio-access-key>"
    MINIO_SECRET_KEY: str = "<your-minio-secret-key>"
    MINIO_BUCKET_NAME: str = "<your-minio-bucket-name>"
    MINIO_SECURE: bool = False

    # CITI Program Automation
    CITI_USERNAME: str = "<your-citi-username>"
    CITI_PASSWORD: str = "<your-citi-password>"
    CITI_HEADLESS: bool = True
    CITI_TIMEOUT: int = 30000

    # Redis & Celery
    REDIS_PASSWORD: str = "<your-redis-password>"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: str = "redis://:your-redis-password@localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://:your-redis-password@localhost:6379/0"

    @field_validator("ALLOWED_HOSTS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if not v:
            return []
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
