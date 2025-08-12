from typing import Optional, Dict, Any
from datetime import date
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, desc, func

from app.utils.logging import get_logger
from app.db.models import (
    ProgramRequirement,
    Program,
    CertificateType,
    ProgramRequirementSchedule,
    AcademicYear,
)
from app.db.session import get_async_session
from app.schemas.staff.program_requirement_schemas import (
    CreateProgramRequirementRequest,
    UpdateProgramRequirementRequest,
    ProgramRequirementDetailResponse,
)

logger = get_logger()


class ProgramRequirementServiceProvider:
    """Service provider for program requirement-related business logic and database operations"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # Core CRUD Operations
    async def get_requirement_by_id(self, requirement_id: uuid.UUID) -> Optional[ProgramRequirement]:
        """Get program requirement by ID or return None if not found"""
        result = await self.db.execute(
            select(ProgramRequirement).where(ProgramRequirement.id == requirement_id)
        )
        return result.scalar_one_or_none()

    async def create_requirement(
        self, requirement_data: CreateProgramRequirementRequest
    ) -> Dict[str, Any]:
        """Create a new program requirement with comprehensive validation"""
        # Validate program exists and is active
        program = await self._validate_program_exists_and_active(
            requirement_data.program_id
        )

        # Validate target year against program duration
        if requirement_data.target_year > program.duration_years:
            raise ValueError(
                f"TARGET_YEAR_EXCEEDS_PROGRAM_DURATION: Target year ({requirement_data.target_year}) cannot exceed program duration ({program.duration_years} years)"
            )

        # Validate certificate type exists and is active
        await self._validate_certificate_type_exists_and_active(
            requirement_data.cert_type_id
        )

        try:
            # Create deadline date (using year 2000 as base)
            deadline_date = date(
                2000, requirement_data.deadline_month, requirement_data.deadline_day
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
                months_before_deadline=requirement_data.months_before_deadline,
            )

            self.db.add(new_requirement)
            await self.db.commit()
            await self.db.refresh(new_requirement)

            logger.info(
                f"Created program requirement: {new_requirement.name} for program {program.program_code}"
            )

            return {
                "id": str(new_requirement.id),
                "name": new_requirement.name,
                "target_year": new_requirement.target_year,
            }

        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(f"Integrity error creating program requirement: {str(e)}")

            # Check for specific constraint violations
            error_msg = str(e.orig).lower()
            if "unique" in error_msg:
                raise ValueError("REQUIREMENT_ALREADY_EXISTS")
            else:
                raise ValueError("DATABASE_CONSTRAINT_VIOLATION")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create program requirement: {str(e)}", exc_info=True)
            raise RuntimeError("PROGRAM_REQUIREMENT_CREATION_FAILED")

    async def archive_requirement(self, requirement_id: uuid.UUID) -> Dict[str, Any]:
        """Archive a program requirement with proper effective_until_year handling"""
        # Get the requirement to archive
        requirement = await self.get_requirement_by_id(requirement_id)
        if not requirement:
            raise ValueError("PROGRAM_REQUIREMENT_NOT_FOUND")

        if not requirement.is_active:
            raise ValueError("PROGRAM_REQUIREMENT_ALREADY_ARCHIVED")

        try:
            # Find the latest academic year for which we have created a schedule
            latest_academic_year = await self._get_latest_schedule_academic_year(
                requirement_id
            )

            # Update the requirement
            requirement.is_active = False

            # Update effective_until_year if needed
            if latest_academic_year:
                if (requirement.effective_until_year is None or 
                    requirement.effective_until_year > latest_academic_year):
                    requirement.effective_until_year = latest_academic_year
                    logger.info(
                        f"Updated effective_until_year to {latest_academic_year} for requirement {requirement.name}"
                    )

            await self.db.commit()
            await self.db.refresh(requirement)

            logger.info(f"Archived program requirement: {requirement.name}")

            return {
                "id": str(requirement.id),
                "name": requirement.name,
                "is_active": requirement.is_active,
                "effective_until_year": requirement.effective_until_year,
                "latest_schedule_academic_year": latest_academic_year,
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to archive program requirement: {str(e)}", exc_info=True)
            raise RuntimeError("PROGRAM_REQUIREMENT_ARCHIVE_FAILED")

    async def update_requirement(
        self, requirement_id: uuid.UUID, requirement_data: UpdateProgramRequirementRequest
    ) -> Dict[str, Any]:
        """Update an existing program requirement with comprehensive validation"""
        # Get the existing requirement
        requirement = await self.get_requirement_by_id(requirement_id)
        if not requirement:
            raise ValueError("PROGRAM_REQUIREMENT_NOT_FOUND")

        # Validate that the program still exists and is active
        program = await self._validate_program_exists_and_active(requirement.program_id)

        # Validate target_year against program duration
        if requirement_data.target_year > program.duration_years:
            raise ValueError(
                f"TARGET_YEAR_EXCEEDS_PROGRAM_DURATION: Target year ({requirement_data.target_year}) cannot exceed program duration ({program.duration_years} years)"
            )

        # Get academic year boundaries for validation
        oldest_academic_year = await self._get_oldest_academic_year()
        latest_schedule_academic_year = await self._get_latest_schedule_academic_year(
            requirement_id
        )

        # Validate effective_from_year
        if (requirement_data.effective_from_year and oldest_academic_year and
            requirement_data.effective_from_year < oldest_academic_year):
            raise ValueError(
                f"EFFECTIVE_FROM_YEAR_TOO_EARLY: effective_from_year ({requirement_data.effective_from_year}) cannot be earlier than the oldest academic year ({oldest_academic_year})"
            )

        # Validate effective_until_year
        if (requirement_data.effective_until_year and latest_schedule_academic_year and
            requirement_data.effective_until_year > latest_schedule_academic_year):
            raise ValueError(
                f"EFFECTIVE_UNTIL_YEAR_TOO_LATE: effective_until_year ({requirement_data.effective_until_year}) cannot be later than the latest academic year with created schedules ({latest_schedule_academic_year})"
            )

        try:
            # Create new deadline date (using year 2000 as base)
            deadline_date = date(
                2000, requirement_data.deadline_month, requirement_data.deadline_day
            )

            # Update the requirement with new values
            requirement.name = requirement_data.name
            requirement.target_year = requirement_data.target_year
            requirement.deadline_date = deadline_date
            requirement.grace_period_days = requirement_data.grace_period_days or 7
            requirement.notification_days_before_deadline = requirement_data.notification_days_before_deadline or 90
            requirement.is_mandatory = requirement_data.is_mandatory
            requirement.special_instruction = requirement_data.special_instruction
            requirement.recurrence_type = requirement_data.recurrence_type
            requirement.effective_from_year = requirement_data.effective_from_year
            requirement.effective_until_year = requirement_data.effective_until_year
            requirement.months_before_deadline = requirement_data.months_before_deadline

            await self.db.commit()
            await self.db.refresh(requirement)

            logger.info(f"Updated program requirement: {requirement.name}")

            return {
                "id": str(requirement.id),
                "name": requirement.name,
                "target_year": requirement.target_year,
                "effective_from_year": requirement.effective_from_year,
                "effective_until_year": requirement.effective_until_year,
                "oldest_academic_year": oldest_academic_year,
                "latest_schedule_academic_year": latest_schedule_academic_year,
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update program requirement: {str(e)}", exc_info=True)
            raise RuntimeError("PROGRAM_REQUIREMENT_UPDATE_FAILED")

    async def get_requirement_details(self, requirement_id: uuid.UUID) -> Dict[str, Any]:
        """Get comprehensive program requirement details with related data"""
        # Build complex query to get all required data
        schedule_stats_subquery = (
            select(
                ProgramRequirementSchedule.program_requirement_id,
                func.count(ProgramRequirementSchedule.id).label("schedules_count"),
                func.max(ProgramRequirementSchedule.submission_deadline).label("latest_schedule_deadline")
            )
            .where(ProgramRequirementSchedule.program_requirement_id == requirement_id)
            .group_by(ProgramRequirementSchedule.program_requirement_id)
            .subquery()
        )
        
        # Main query joining all required tables
        main_query = (
            select(
                # Program requirement fields
                ProgramRequirement.id,
                ProgramRequirement.name,
                ProgramRequirement.target_year,
                ProgramRequirement.deadline_date,
                ProgramRequirement.grace_period_days,
                ProgramRequirement.notification_days_before_deadline,
                ProgramRequirement.is_mandatory,
                ProgramRequirement.is_active,
                ProgramRequirement.special_instruction,
                ProgramRequirement.recurrence_type,
                ProgramRequirement.last_recurrence_at,
                ProgramRequirement.effective_from_year,
                ProgramRequirement.effective_until_year,
                ProgramRequirement.months_before_deadline,
                ProgramRequirement.created_at,
                ProgramRequirement.updated_at,
                
                # Program fields
                ProgramRequirement.program_id,
                Program.program_code,
                Program.program_name,
                
                # Certificate type fields
                ProgramRequirement.cert_type_id,
                CertificateType.code.label("cert_code"),
                CertificateType.name.label("cert_name"),
                
                # Schedule statistics
                func.coalesce(schedule_stats_subquery.c.schedules_count, 0).label("schedules_count"),
                schedule_stats_subquery.c.latest_schedule_deadline
            )
            .join(Program, ProgramRequirement.program_id == Program.id)
            .join(CertificateType, ProgramRequirement.cert_type_id == CertificateType.id)
            .outerjoin(
                schedule_stats_subquery, 
                ProgramRequirement.id == schedule_stats_subquery.c.program_requirement_id
            )
            .where(ProgramRequirement.id == requirement_id)
        )
        
        try:
            # Execute the query
            result = await self.db.execute(main_query)
            requirement_data = result.first()
            
            if not requirement_data:
                raise ValueError("PROGRAM_REQUIREMENT_NOT_FOUND")
            
            # Create response using the comprehensive schema
            response_data = ProgramRequirementDetailResponse(
                # Program requirement fields
                id=requirement_data.id,
                name=requirement_data.name,
                target_year=requirement_data.target_year,
                deadline_date=requirement_data.deadline_date,
                grace_period_days=requirement_data.grace_period_days,
                notification_days_before_deadline=requirement_data.notification_days_before_deadline,
                is_mandatory=requirement_data.is_mandatory,
                is_active=requirement_data.is_active,
                special_instruction=requirement_data.special_instruction,
                recurrence_type=requirement_data.recurrence_type,
                last_recurrence_at=requirement_data.last_recurrence_at,
                effective_from_year=requirement_data.effective_from_year,
                effective_until_year=requirement_data.effective_until_year,
                months_before_deadline=requirement_data.months_before_deadline,
                created_at=requirement_data.created_at,
                updated_at=requirement_data.updated_at,
                
                # Program information
                program_id=requirement_data.program_id,
                program_code=requirement_data.program_code,
                program_name=requirement_data.program_name,
                
                # Certificate type information
                cert_type_id=requirement_data.cert_type_id,
                cert_code=requirement_data.cert_code,
                cert_name=requirement_data.cert_name,
                
                # Schedule statistics
                schedules_count=requirement_data.schedules_count,
                latest_schedule_deadline=requirement_data.latest_schedule_deadline
            )
            
            logger.info(f"Retrieved program requirement details: {requirement_data.name}")
            
            return response_data.model_dump()

        except Exception as e:
            logger.error(f"Failed to retrieve program requirement details: {str(e)}", exc_info=True)
            raise RuntimeError("PROGRAM_REQUIREMENT_RETRIEVAL_FAILED")

    # Helper Methods
    async def _validate_program_exists_and_active(self, program_id: uuid.UUID) -> Program:
        """Validate that program exists and is active"""
        result = await self.db.execute(select(Program).where(Program.id == program_id))
        program = result.scalar_one_or_none()
        
        if not program:
            raise ValueError("PROGRAM_NOT_FOUND")
        
        if not program.is_active:
            raise ValueError("PROGRAM_NOT_ACTIVE")
        
        return program

    async def _validate_certificate_type_exists_and_active(self, cert_type_id: uuid.UUID):
        """Validate that certificate type exists and is active"""
        result = await self.db.execute(
            select(CertificateType).where(CertificateType.id == cert_type_id)
        )
        cert_type = result.scalar_one_or_none()
        
        if not cert_type:
            raise ValueError("CERTIFICATE_TYPE_NOT_FOUND")
        
        if not cert_type.is_active:
            raise ValueError("CERTIFICATE_TYPE_NOT_ACTIVE")

    async def _get_oldest_academic_year(self) -> Optional[str]:
        """Get the oldest academic year from the system"""
        result = await self.db.execute(
            select(AcademicYear.year_code)
            .order_by(AcademicYear.year_code.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_latest_schedule_academic_year(self, requirement_id: uuid.UUID) -> Optional[str]:
        """Get the latest academic year for which schedules have been created"""
        result = await self.db.execute(
            select(AcademicYear.year_code)
            .join(ProgramRequirementSchedule, AcademicYear.id == ProgramRequirementSchedule.academic_year_id)
            .where(ProgramRequirementSchedule.program_requirement_id == requirement_id)
            .order_by(desc(AcademicYear.year_code))
            .limit(1)
        )
        return result.scalar_one_or_none()


# Dependency injection for service provider
def get_program_requirement_service(
    db: AsyncSession = Depends(get_async_session),
) -> ProgramRequirementServiceProvider:
    """Dependency to provide ProgramRequirementServiceProvider instance"""
    return ProgramRequirementServiceProvider(db)