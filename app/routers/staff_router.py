from fastapi import APIRouter, Request
from typing import List
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models.staff_models import ParsedStudentRecord
from app.providers.student_data_provider import StudentDataProvider
from app.utils.responses import ResponseBuilder, ApiResponse

staff_router = APIRouter()


@staff_router.post("/import-student-data", response_model=ApiResponse)
async def upload_student_data(data: List[ParsedStudentRecord], request: Request):
    provider = StudentDataProvider(data)
    try:
        stats = provider.process_imported_student_data()
        return ResponseBuilder.success(
            request=request,
            data=stats,
            message=f"Student data processed successfully. Created {stats['created']} students, skipped {stats['skipped']}.",
        )
    except ValueError as e:
        raise StarletteHTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise StarletteHTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise StarletteHTTPException(status_code=500, detail=str(e))
