from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Request, status, Path

from app.services.program_service import ProgramServiceProvider, get_program_service
from app.schemas.staff.program_schemas import (
    CreateProgramRequest,
    UpdateProgramRequest,
    ProgramListQueryParams,
)
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError

programs_router = APIRouter()


def handle_service_error(request: Request, error: Exception):
    """Handle service errors and return appropriate error response"""
    error_message = str(error)

    # Handle duration conflicts with requirements (special case)
    if error_message.startswith("DURATION_CONFLICTS_WITH_REQUIREMENTS:"):
        requirement_details = error_message.split(": ", 1)[1]
        return ResponseBuilder.error(
            request=request,
            message=f"Cannot reduce program duration. Active requirements exist with target years beyond the new duration: {requirement_details}. Please update these requirements first.",
            error_code="DURATION_CONFLICTS_WITH_REQUIREMENTS",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Handle program with active requirements (special case)
    if error_message.startswith("PROGRAM_HAS_ACTIVE_REQUIREMENTS:"):
        requirement_details = error_message.split(": ", 1)[1]
        return ResponseBuilder.error(
            request=request,
            message=f"Cannot archive program. {requirement_details}. Please archive these requirements individually first.",
            error_code="PROGRAM_HAS_ACTIVE_REQUIREMENTS",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # For standard error codes, map to appropriate status codes
    error_status_mapping = {
        "PROGRAM_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PROGRAM_CODE_EXISTS": status.HTTP_409_CONFLICT,
        "PROGRAM_ALREADY_ARCHIVED": status.HTTP_400_BAD_REQUEST,
    }

    status_code = error_status_mapping.get(
        error_message, status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    # Map error codes to user-friendly messages
    error_messages = {
        "PROGRAM_NOT_FOUND": "Program not found",
        "PROGRAM_CODE_EXISTS": "Program with this code already exists",
        "PROGRAM_ALREADY_ARCHIVED": "Program is already archived",
        "PROGRAM_CREATION_FAILED": "Failed to create program",
        "PROGRAM_UPDATE_FAILED": "Failed to update program",
        "PROGRAM_ARCHIVE_FAILED": "Failed to archive program",
        "PROGRAMS_RETRIEVAL_FAILED": "Failed to retrieve programs",
    }

    message = error_messages.get(error_message, "An unexpected error occurred")

    return ResponseBuilder.error(
        request=request,
        message=message,
        error_code=error_message,
        status_code=status_code,
    )


# API Endpoints
@programs_router.get(
    "/",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Get all programs with requirement counts",
    description="Retrieve all programs with their basic information and counts of active/archived requirements. Supports filtering and sorting.",
)
async def get_all_programs(
    request: Request,
    query_params: Annotated[ProgramListQueryParams, Depends()],
    program_service: ProgramServiceProvider = Depends(get_program_service),
):
    """Get all programs with filtering and sorting capabilities"""
    try:
        programs_list = await program_service.get_all_programs_with_counts(query_params)
        message = ProgramServiceProvider.build_success_message(
            len(programs_list), query_params
        )

        return ResponseBuilder.success(
            request=request,
            data=programs_list,
            message=message,
            status_code=status.HTTP_200_OK,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception:
        raise BusinessLogicError(
            message="Failed to retrieve programs",
            error_code="PROGRAMS_RETRIEVAL_FAILED",
        )


@programs_router.post(
    "/",
    response_model=None,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new program",
    description="Create a new academic program with the provided details",
)
async def create_program(
    request: Request,
    program_data: CreateProgramRequest,
    program_service: ProgramServiceProvider = Depends(get_program_service),
):
    """Create a new academic program"""
    try:
        program_response = await program_service.create_program(program_data)

        return ResponseBuilder.success(
            request=request,
            data=program_response,
            message="Program created successfully",
            status_code=status.HTTP_201_CREATED,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception:
        raise BusinessLogicError(
            message="Failed to create program", error_code="PROGRAM_CREATION_FAILED"
        )


@programs_router.put(
    "/{program_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Update an existing program",
    description="Update an existing academic program. Validates that duration changes don't conflict with active requirements.",
)
async def update_program(
    request: Request,
    program_data: UpdateProgramRequest,
    program_id: Annotated[uuid.UUID, Path(description="Program ID to update")],
    program_service: ProgramServiceProvider = Depends(get_program_service),
):
    """Update an existing academic program with validation"""
    try:
        program_response = await program_service.update_program(
            program_id, program_data
        )

        return ResponseBuilder.success(
            request=request,
            data=program_response,
            message="Program updated successfully",
            status_code=status.HTTP_200_OK,
        )

    except (ValueError, RuntimeError) as e:
        return handle_service_error(request, e)
    except Exception:
        raise BusinessLogicError(
            message="Failed to update program", error_code="PROGRAM_UPDATE_FAILED"
        )


@programs_router.patch(
    "/{program_id}/archive",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Archive an existing program",
    description="Archive an existing program and all its active requirements. Returns count of archived requirements.",
)
async def archive_program(
    request: Request,
    program_id: Annotated[uuid.UUID, Path(description="Program ID to archive")],
    program_service: ProgramServiceProvider = Depends(get_program_service),
):
    """Archive a program and all its active requirements"""
    try:
        response_data = await program_service.archive_program(program_id)
        archived_count = response_data["archived_requirements_count"]
        message = ProgramServiceProvider.build_archive_message(archived_count)

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
            message="Failed to archive program", error_code="PROGRAM_ARCHIVE_FAILED"
        )
