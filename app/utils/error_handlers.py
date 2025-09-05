from fastapi import Request, status

from app.utils.responses import ResponseBuilder


def handle_service_error(request: Request, error: Exception):
    """Centralized service error handler for all staff routers"""
    error_message = str(error)

    # Handle certificate-specific errors with detailed messages
    if error_message.startswith("CERTIFICATE_TYPE_HAS_ACTIVE_REQUIREMENTS:"):
        requirement_details = error_message.split(": ", 1)[1]
        return ResponseBuilder.error(
            request=request,
            message=f"Cannot archive certificate type. {requirement_details}. Please archive these requirements individually first.",
            error_code="CERTIFICATE_TYPE_HAS_ACTIVE_REQUIREMENTS",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Handle program requirement-specific validation errors
    if error_message.startswith("TARGET_YEAR_EXCEEDS_PROGRAM_DURATION:"):
        details = error_message.split(": ", 1)[1]
        return ResponseBuilder.error(
            request=request,
            message=details,
            error_code="TARGET_YEAR_EXCEEDS_PROGRAM_DURATION",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if error_message.startswith("EFFECTIVE_FROM_YEAR_TOO_EARLY:"):
        details = error_message.split(": ", 1)[1]
        return ResponseBuilder.error(
            request=request,
            message=details,
            error_code="EFFECTIVE_FROM_YEAR_TOO_EARLY",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Handle program-specific errors with detailed messages
    if error_message.startswith("DURATION_CONFLICTS_WITH_REQUIREMENTS:"):
        requirement_details = error_message.split(": ", 1)[1]
        return ResponseBuilder.error(
            request=request,
            message=f"Cannot reduce program duration. Active requirements exist with target years beyond the new duration: {requirement_details}.",
            error_code="DURATION_CONFLICTS_WITH_REQUIREMENTS",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if error_message.startswith("PROGRAM_HAS_ACTIVE_REQUIREMENTS:"):
        requirement_details = error_message.split(": ", 1)[1]
        return ResponseBuilder.error(
            request=request,
            message=f"Cannot archive program. {requirement_details}. Please archive these requirements individually first.",
            error_code="PROGRAM_HAS_ACTIVE_REQUIREMENTS",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Extract error code for submissions (format: "ERROR_CODE: message")
    if ":" in error_message:
        error_code = error_message.split(":", 1)[0]
    else:
        error_code = error_message

    # Comprehensive error code to status code mapping
    error_status_mapping = {
        # Certificate errors
        "CERTIFICATE_TYPE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CERTIFICATE_CODE_EXISTS": status.HTTP_409_CONFLICT,
        "CERTIFICATE_TYPE_ALREADY_ARCHIVED": status.HTTP_400_BAD_REQUEST,
        # Program requirement schedule errors
        "PROGRAM_REQUIREMENT_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PROGRAM_REQUIREMENT_NOT_ACTIVE": status.HTTP_400_BAD_REQUEST,
        "ACADEMIC_YEAR_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "SCHEDULE_ALREADY_EXISTS": status.HTTP_409_CONFLICT,
        "SCHEDULE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "INVALID_DEADLINE": status.HTTP_400_BAD_REQUEST,
        "DEADLINE_OUTSIDE_ACADEMIC_YEAR": status.HTTP_400_BAD_REQUEST,
        "INVALID_PROGRAM_REQUIREMENT_MODIFICATION": status.HTTP_400_BAD_REQUEST,
        "DATABASE_CONSTRAINT_VIOLATION": status.HTTP_400_BAD_REQUEST,
        # Program errors
        "PROGRAM_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PROGRAM_CODE_EXISTS": status.HTTP_409_CONFLICT,
        "PROGRAM_ALREADY_ARCHIVED": status.HTTP_400_BAD_REQUEST,
        "PROGRAM_NOT_ACTIVE": status.HTTP_400_BAD_REQUEST,
        # Certificate type errors
        "CERTIFICATE_TYPE_NOT_ACTIVE": status.HTTP_400_BAD_REQUEST,
        # General requirement errors
        "REQUIREMENT_ALREADY_EXISTS": status.HTTP_409_CONFLICT,
        "PROGRAM_REQUIREMENT_ALREADY_ARCHIVED": status.HTTP_400_BAD_REQUEST,
        # Submission errors
        "SUBMISSIONS_RETRIEVAL_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "VERIFICATION_HISTORY_RETRIEVAL_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "CERTIFICATE_SUBMISSION_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    }

    status_code = error_status_mapping.get(
        error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    # Comprehensive error code to user-friendly message mapping
    error_messages = {
        # Certificate errors
        "CERTIFICATE_TYPE_NOT_FOUND": "Certificate type not found",
        "CERTIFICATE_CODE_EXISTS": "Certificate type with this code already exists",
        "CERTIFICATE_TYPE_ALREADY_ARCHIVED": "Certificate type is already archived",
        "CERTIFICATE_TYPE_UPDATE_FAILED": "Failed to update certificate type",
        "CERTIFICATE_TYPE_ARCHIVE_FAILED": "Failed to archive certificate type",
        "CERTIFICATE_TYPES_RETRIEVAL_FAILED": "Failed to retrieve certificate types",
        # Program requirement schedule errors
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
        # Program errors
        "PROGRAM_NOT_FOUND": "Program not found",
        "PROGRAM_CODE_EXISTS": "Program with this code already exists",
        "PROGRAM_ALREADY_ARCHIVED": "Program is already archived",
        "PROGRAM_NOT_ACTIVE": "Cannot create requirement for inactive program",
        "PROGRAM_CREATION_FAILED": "Failed to create program",
        "PROGRAM_UPDATE_FAILED": "Failed to update program",
        "PROGRAM_ARCHIVE_FAILED": "Failed to archive program",
        "PROGRAMS_RETRIEVAL_FAILED": "Failed to retrieve programs",
        # Certificate type errors
        "CERTIFICATE_TYPE_NOT_ACTIVE": "Cannot create requirement for inactive certificate type",
        # General requirement errors
        "REQUIREMENT_ALREADY_EXISTS": "A requirement with similar constraints already exists",
        "PROGRAM_REQUIREMENT_ALREADY_ARCHIVED": "Program requirement is already archived",
        "PROGRAM_REQUIREMENT_CREATION_FAILED": "Failed to create program requirement",
        "PROGRAM_REQUIREMENT_UPDATE_FAILED": "Failed to update program requirement",
        "PROGRAM_REQUIREMENT_ARCHIVE_FAILED": "Failed to archive program requirement",
        "PROGRAM_REQUIREMENT_RETRIEVAL_FAILED": "Failed to retrieve program requirement details",
        # Submission errors
        "SUBMISSIONS_RETRIEVAL_FAILED": "Failed to retrieve certificate submissions",
        "VERIFICATION_HISTORY_RETRIEVAL_FAILED": "Failed to retrieve verification history",
        "CERTIFICATE_SUBMISSION_NOT_FOUND": "Certificate submission not found",
    }

    message = error_messages.get(error_code, "An unexpected error occurred")

    return ResponseBuilder.error(
        request=request,
        message=message,
        error_code=error_code,
        status_code=status_code,
    )
