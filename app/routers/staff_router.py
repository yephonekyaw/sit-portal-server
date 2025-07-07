from fastapi import APIRouter
from typing import List
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models.staff_models import ParsedStudentRecord
from app.providers.student_data_provider import StudentDataProvider
from app.utils.responses import ResponseBuilder

staff_router = APIRouter()


@staff_router.post("/student-data")
async def upload_student_data(data: List[ParsedStudentRecord]):
    provider = StudentDataProvider(data)
    try:
        stats = provider.process()
        return ResponseBuilder.success(
            stats,
            message=f"Student data processed successfully. Created {stats['created']} students, skipped {stats['skipped']}.",
        )
    except ValueError as e:
        raise StarletteHTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise StarletteHTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise StarletteHTTPException(status_code=500, detail=str(e))
