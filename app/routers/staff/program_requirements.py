from datetime import date

from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.db.session import get_async_session
from app.db.models import (
    ProgramRequirement,
    Program,
    CertificateType,
    ScheduleCreationTrigger,
)
from app.schemas.staff.program_requirement_schemas import (
    CreateProgramRequirementRequest,
    ProgramRequirementResponse,
)
from app.utils.responses import ResponseBuilder
from app.utils.errors import BusinessLogicError
from app.utils.logging import get_logger

logger = get_logger()
program_requirements_router = APIRouter()


@program_requirements_router.post(
    "/",
    response_model=None,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new program requirement",
    description="Create a new program requirement with comprehensive validation including target year against program duration",
)
async def create_program_requirement(
    request: Request,
    requirement_data: CreateProgramRequirementRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new program requirement with validation"""
    try:
        # Validate that program exists and get duration for validation
        program_result = await db.execute(
            select(Program).where(Program.id == requirement_data.program_id)
        )
        program = program_result.scalar_one_or_none()
        if not program:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Program not found"
            )

        if not program.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create requirement for inactive program",
            )

        # Validate target_year against program duration
        if requirement_data.target_year > program.duration_years:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target year ({requirement_data.target_year}) cannot exceed program duration ({program.duration_years} years)",
            )

        # Validate that certificate type exists and is active
        cert_type_result = await db.execute(
            select(CertificateType).where(
                CertificateType.id == requirement_data.cert_type_id
            )
        )
        cert_type = cert_type_result.scalar_one_or_none()
        if not cert_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Certificate type not found",
            )

        if not cert_type.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create requirement for inactive certificate type",
            )

        # Create deadline date (using year 2000 as base as specified)
        deadline_date = date(
            2000, requirement_data.deadline_month, requirement_data.deadline_day
        )

        # Create custom trigger date if provided
        custom_trigger_date = None
        if (
            requirement_data.schedule_creation_trigger
            == ScheduleCreationTrigger.CUSTOM_DATE
            and requirement_data.custom_trigger_month is not None
            and requirement_data.custom_trigger_day is not None
        ):
            custom_trigger_date = date(
                2000,
                requirement_data.custom_trigger_month,
                requirement_data.custom_trigger_day,
            )

        # Create the program requirement
        new_requirement = ProgramRequirement(
            program_id=requirement_data.program_id,
            cert_type_id=requirement_data.cert_type_id,
            name=requirement_data.name,
            target_year=requirement_data.target_year,
            deadline_date=deadline_date,
            grace_period_days=requirement_data.grace_period_days or 7,
            notification_days_before_deadline=requirement_data.notification_days_before_deadline or 90,
            is_mandatory=requirement_data.is_mandatory,
            is_active=requirement_data.is_active,
            special_instruction=requirement_data.special_instruction,
            recurrence_type=requirement_data.recurrence_type,
            effective_from_year=requirement_data.effective_from_year,
            effective_until_year=requirement_data.effective_until_year,
            schedule_creation_trigger=requirement_data.schedule_creation_trigger,
            custom_trigger_date=custom_trigger_date,
            months_before_target_year=requirement_data.months_before_target_year,
        )

        db.add(new_requirement)
        await db.commit()
        await db.refresh(new_requirement)

        logger.info(
            f"Created program requirement: {new_requirement.name} for program {program.program_code}"
        )

        # Create minimal response data
        response_data = {
            "id": str(new_requirement.id),
            "name": new_requirement.name,
            "target_year": new_requirement.target_year,
        }

        return ResponseBuilder.success(
            request=request,
            data=response_data,
            message="Program requirement created successfully",
            status_code=status.HTTP_201_CREATED,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"Integrity error creating program requirement: {str(e)}")

        # Check for specific constraint violations
        error_msg = str(e.orig).lower()
        if "unique" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A requirement with similar constraints already exists",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint violation",
            )
    except ValueError as e:
        await db.rollback()
        logger.warning(f"Validation error creating program requirement: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create program requirement: {str(e)}", exc_info=True)
        raise BusinessLogicError(
            message="Failed to create program requirement",
            error_code="PROGRAM_REQUIREMENT_CREATION_FAILED",
        )
