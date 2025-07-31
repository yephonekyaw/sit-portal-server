from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.schemas.staff.staff_schemas import (
    ImportStudentsRequest,
    ImportStudentsResponse,
)
from app.services.student_service import StudentService

# from app.middlewares.auth_middleware import require_user_type
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError

students_router = APIRouter()


@students_router.post("/import", response_model=ImportStudentsResponse)
async def import_students(
    data: ImportStudentsRequest,
    request: Request,
    # current_user: Annotated[dict, Depends(require_user_type("staff"))],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Import student records with duplicate handling and validation

    - Handles duplicates in sent data and existing database records
    - Creates academic years if they don't exist
    - Validates program codes (throws error if not found)
    - Returns detailed import statistics
    """
    try:
        # Initialize student service with the provided data
        student_service = StudentService(db, data.students)

        # Process the student data
        result = await student_service.process_imported_student_data()

        # Check if there were critical errors (like invalid program codes)
        if result["errors"] and result["created"] == 0:
            raise BusinessLogicError(
                f"Import failed: {'; '.join(result['errors'][:3])}"
                + ("..." if len(result["errors"]) > 3 else "")
            )

        # Prepare response data
        response_data = ImportStudentsResponse(
            total_received=len(data.students),
            processed=result["processed"],
            created=result["created"],
            skipped=result["skipped"],
            errors=result["errors"],
        )

        return ResponseBuilder.success(
            request=request,
            data=response_data.model_dump(),
            message=f"Successfully imported {result['created']} students. {result['skipped']} skipped.",
        )

    except BusinessLogicError:
        raise
    except Exception as e:
        raise BusinessLogicError(f"Failed to import students: {str(e)}")
