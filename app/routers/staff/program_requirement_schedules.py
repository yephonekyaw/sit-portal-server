from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Request, status, Path

from app.services.staff.program_requirement_schedule_service import (
    ProgramRequirementScheduleService,
    get_program_requirement_schedule_service,
)
from app.schemas.staff.program_requirement_schedule_schemas import (
    CreateProgramRequirementScheduleRequest,
    UpdateProgramRequirementScheduleRequest,
)
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError
from app.middlewares.auth_middleware import require_staff

program_requirement_schedules_router = APIRouter(dependencies=[Depends(require_staff)])


def handle_service_error(request: Request, error: Exception):
    """Handle service errors and return appropriate error response"""
    error_message = str(error)

    # Map error codes to status codes
    error_status_mapping = {
        "PROGRAM_REQUIREMENT_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PROGRAM_REQUIREMENT_NOT_ACTIVE": status.HTTP_400_BAD_REQUEST,
        "ACADEMIC_YEAR_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "SCHEDULE_ALREADY_EXISTS": status.HTTP_409_CONFLICT,
        "SCHEDULE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "INVALID_DEADLINE": status.HTTP_400_BAD_REQUEST,
        "DEADLINE_OUTSIDE_ACADEMIC_YEAR": status.HTTP_400_BAD_REQUEST,
        "INVALID_PROGRAM_REQUIREMENT_MODIFICATION": status.HTTP_400_BAD_REQUEST,
        "DATABASE_CONSTRAINT_VIOLATION": status.HTTP_400_BAD_REQUEST,
    }

    status_code = error_status_mapping.get(
        error_message, status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    # Map error codes to user-friendly messages
    error_messages = {
        "PROGRAM_REQUIREMENT_NOT_FOUND": "Program requirement not found",
        "PROGRAM_REQUIREMENT_NOT_ACTIVE": "Cannot create schedule for inactive program requirement",
        "ACADEMIC_YEAR_NOT_FOUND": "Academic year not found",
        "SCHEDULE_ALREADY_EXISTS": "A schedule already exists for this program requirement and academic year",
        "SCHEDULE_NOT_FOUND": "Program requirement schedule not found",
        "INVALID_DEADLINE": "Invalid deadline specified",
        "DEADLINE_OUTSIDE_ACADEMIC_YEAR": "Submission deadline must be within the academic year period",
        "INVALID_PROGRAM_REQUIREMENT_MODIFICATION": "Program requirement ID cannot be modified",
        "DATABASE_CONSTRAINT_VIOLATION": "Database constraint violation",
        "SCHEDULE_CREATION_FAILED": "Failed to create program requirement schedule",
        "SCHEDULE_UPDATE_FAILED": "Failed to update program requirement schedule",
        "SCHEDULES_RETRIEVAL_FAILED": "Failed to retrieve program requirement schedules",
    }

    message = error_messages.get(error_message, "An unexpected error occurred")

    return ResponseBuilder.error(
        request=request,
        message=message,
        error_code=error_message,
        status_code=status_code,
    )


# API Endpoints
@program_requirement_schedules_router.get(
    "/",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Get all program requirement schedules with comprehensive data",
    description="Retrieve all program requirement schedules with program, certificate type, academic year, and dashboard statistics data.",
)
async def get_all_program_requirement_schedules(
    request: Request,
    schedule_service: ProgramRequirementScheduleService = Depends(
        get_program_requirement_schedule_service
    ),
):
    """Get all program requirement schedules with comprehensive related data"""
    try:
        response_data = await schedule_service.get_all_schedules_with_details()
        schedules_count = len(response_data)
        message = ProgramRequirementScheduleService.build_success_message(
            schedules_count
        )

        return ResponseBuilder.success(
            request=request,
            data=response_data,
            message=message,
            status_code=status.HTTP_200_OK,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception:
        raise BusinessLogicError(
            message="Failed to retrieve program requirement schedules",
            error_code="SCHEDULES_RETRIEVAL_FAILED",
        )


@program_requirement_schedules_router.post(
    "/",
    response_model=None,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new program requirement schedule",
    description="Create a new program requirement schedule for a specific academic year. Validates that the program requirement is active and no duplicate schedule exists.",
)
async def create_program_requirement_schedule(
    request: Request,
    schedule_data: CreateProgramRequirementScheduleRequest,
    schedule_service: ProgramRequirementScheduleService = Depends(
        get_program_requirement_schedule_service
    ),
):
    """Create a new program requirement schedule with validation"""
    try:
        response_data = await schedule_service.create_schedule(schedule_data)

        return ResponseBuilder.success(
            request=request,
            data=response_data,
            message="Program requirement schedule created successfully",
            status_code=status.HTTP_201_CREATED,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception:
        raise BusinessLogicError(
            message="Failed to create program requirement schedule",
            error_code="SCHEDULE_CREATION_FAILED",
        )


@program_requirement_schedules_router.put(
    "/{schedule_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Update an existing program requirement schedule",
    description="Update an existing program requirement schedule. Validates that the program requirement is active, academic year exists, and deadline is within academic year period.",
)
async def update_program_requirement_schedule(
    request: Request,
    schedule_id: Annotated[uuid.UUID, Path(description="Schedule ID to update")],
    schedule_data: UpdateProgramRequirementScheduleRequest,
    schedule_service: ProgramRequirementScheduleService = Depends(
        get_program_requirement_schedule_service
    ),
):
    """Update an existing program requirement schedule with validation"""
    try:
        response_data = await schedule_service.update_schedule(
            schedule_id, schedule_data
        )

        return ResponseBuilder.success(
            request=request,
            data=response_data,
            message="Program requirement schedule updated successfully",
            status_code=status.HTTP_200_OK,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception:
        raise BusinessLogicError(
            message="Failed to update program requirement schedule",
            error_code="SCHEDULE_UPDATE_FAILED",
        )
