from fastapi import FastAPI, Request, status
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
import traceback
from .logging import get_logger
from .responses import ResponseBuilder

logger = get_logger()


class DatabaseError(Exception):
    """Custom exception for database-related errors."""

    def __init__(self, message: str, error_code: str = "DB_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class BusinessLogicError(Exception):
    """Custom exception for business logic errors."""

    def __init__(self, message: str, error_code: str = "BLOC_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""

    def __init__(
        self, message: str = "Authentication failed", error_code: str = "AUTH_ERROR"
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class AuthorizationError(Exception):
    """Custom exception for authorization errors."""

    def __init__(self, message: str = "Access denied", error_code: str = "AUTHZ_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class NotFoundError(Exception):
    """Custom exception for resource not found errors."""

    def __init__(
        self, message: str = "Resource not found", error_code: str = "NOT_FOUND"
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class LineApplicationError(Exception):
    """Custom exception for LINE application errors."""

    def __init__(self, message: str, error_code: str = "LINE_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def setup_error_handlers(app: FastAPI):
    """Setup custom error handlers."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        return ResponseBuilder.error(
            request=request,
            message=str(exc.detail),
            error_code="HTTP_ERROR",
            status_code=exc.status_code,
            meta={"http_status": exc.status_code},
        )

    """
    RequestValidationError is a sub-class of Pydantic's ValidationError.
    """

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.error(f"Request Validation Error: {exc.errors()}")

        # Format validation errors for better readability
        formatted_errors = []
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            formatted_errors.append(
                {
                    "field": field_path,
                    "message": error["msg"],
                    "type": error["type"],
                    "input": error.get("input"),
                }
            )

        return ResponseBuilder.error(
            request=request,
            message="Request validation failed",
            errors=formatted_errors,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    """
    If you use a Pydantic model in response_model, and your data has an error, you will see the error in your log.
    """

    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(
        request: Request, exc: ValidationError
    ):
        logger.error(f"Pydantic Validation Error: {exc.errors()}")

        # Format Pydantic validation errors
        formatted_errors = []
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            formatted_errors.append(
                {
                    "field": field_path,
                    "message": error["msg"],
                    "type": error["type"],
                    "input": error.get("input"),
                }
            )

        return ResponseBuilder.error(
            request=request,
            message="Data validation failed",
            error_code="INTERNAL_VALIDATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @app.exception_handler(DatabaseError)
    async def database_exception_handler(request: Request, exc: DatabaseError):
        logger.error(f"Database Error: {exc.message}")

        return ResponseBuilder.error(
            request=request,
            message=exc.message,
            error_code=exc.error_code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            meta={"error_type": "DATABASE_ERROR"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"SQLAlchemy Error: {str(exc)}")

        # Don't expose internal database errors to users
        return ResponseBuilder.error(
            request=request,
            message="A database error occurred",
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            meta={"error_type": "SQLALCHEMY_ERROR"},
        )

    @app.exception_handler(BusinessLogicError)
    async def business_logic_exception_handler(
        request: Request, exc: BusinessLogicError
    ):
        logger.error(f"Business Logic Error: {exc.message}")

        return ResponseBuilder.error(
            request=request,
            message=exc.message,
            error_code=exc.error_code,
            status_code=status.HTTP_400_BAD_REQUEST,
            meta={"error_type": "BUSINESS_ERROR"},
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_exception_handler(
        request: Request, exc: AuthenticationError
    ):
        logger.error(f"Authentication Error: {exc.message}")

        return ResponseBuilder.error(
            request=request,
            message=exc.message,
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            meta={"error_type": "AUTHENTICATION_ERROR"},
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_exception_handler(
        request: Request, exc: AuthorizationError
    ):
        logger.error(f"Authorization Error: {exc.message}")

        return ResponseBuilder.error(
            request=request,
            message=exc.message,
            error_code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            meta={"error_type": "AUTHORIZATION_ERROR"},
        )

    @app.exception_handler(NotFoundError)
    async def not_found_exception_handler(request: Request, exc: NotFoundError):
        logger.error(f"Not Found Error: {exc.message}")

        return ResponseBuilder.error(
            request=request,
            message=exc.message,
            error_code=exc.error_code,
            status_code=status.HTTP_404_NOT_FOUND,
            meta={"error_type": "NOT_FOUND_ERROR"},
        )

    @app.exception_handler(LineApplicationError)
    async def line_application_exception_handler(
        request: Request, exc: LineApplicationError
    ):
        logger.error(f"LINE Application Error: {exc.message}")

        return ResponseBuilder.error(
            request=request,
            message=exc.message,
            error_code=exc.error_code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            meta={"error_type": "LINE_APPLICATION_ERROR"},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.error(f"Value Error: {str(exc)}")

        return ResponseBuilder.error(
            request=request,
            message=str(exc),
            error_code="VALUE_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            meta={"error_type": "VALUE_ERROR"},
        )

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        logger.error(f"Key Error: {str(exc)}")

        return ResponseBuilder.error(
            request=request,
            message=f"Required key not found: {str(exc)}",
            error_code="KEY_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            meta={"error_type": "KEY_ERROR", "missing_key": str(exc)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other unhandled exceptions"""
        logger.error(f"Unhandled Exception: {str(exc)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        return ResponseBuilder.error(
            request=request,
            message="An internal server error occurred",
            error_code="INTERNAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            meta={"error_type": "INTERNAL_ERROR"},
        )
