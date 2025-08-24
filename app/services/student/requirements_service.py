from datetime import datetime, timezone
from uuid import UUID
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import UploadFile

from app.db.models import (
    CertificateSubmission,
    CertificateType,
    ProgramRequirementSchedule,
    ProgramRequirement,
    Program,
    Student,
    SubmissionStatus,
    SubmissionTiming,
)
from app.schemas.student.requirement_schemas import (
    RequirementSubmissionRequest,
    RequirementSubmissionResponse,
    StudentRequirementWithSubmissionResponse,
)
from app.services.minio_service import MinIOService
from app.utils.errors import BusinessLogicError
from app.utils.logging import get_logger

logger = get_logger()


class StudentRequirementsService:
    """Service for managing student certificate requirements and submissions"""

    def __init__(self, db_session: AsyncSession, minio_service: MinIOService):
        self.db = db_session
        self.minio = minio_service

    async def get_student_by_user_id(self, user_id: str) -> Student:
        """Get student record by user ID with validation"""
        student_stmt = select(Student).where(Student.user_id == UUID(user_id))
        student_result = await self.db.execute(student_stmt)
        student = student_result.scalar_one_or_none()

        if not student:
            raise BusinessLogicError("Student not found")

        return student

    async def get_student_requirements_with_submissions(
        self, student: Student
    ) -> List[StudentRequirementWithSubmissionResponse]:
        """Get all requirements for student with submission status"""
        # Get all requirement schedules for the student's program and academic year
        schedules_stmt = (
            select(ProgramRequirementSchedule)
            .join(ProgramRequirement)
            .join(Program)
            .join(CertificateType)
            .where(
                ProgramRequirement.program_id == student.program_id,
                ProgramRequirementSchedule.academic_year_id == student.academic_year_id,
            )
            .options(
                selectinload(
                    ProgramRequirementSchedule.program_requirement
                ).selectinload(ProgramRequirement.program),
                selectinload(
                    ProgramRequirementSchedule.program_requirement
                ).selectinload(ProgramRequirement.certificate_type),
                selectinload(
                    ProgramRequirementSchedule.certificate_submissions.and_(
                        CertificateSubmission.student_id == student.id
                    )
                ),
            )
        )

        schedules_result = await self.db.execute(schedules_stmt)
        schedules = schedules_result.scalars().all()

        # Build response data
        requirements_data: List[StudentRequirementWithSubmissionResponse] = []
        for schedule in schedules:
            requirement = schedule.program_requirement
            program = requirement.program
            cert_type = requirement.certificate_type

            # Find existing submission for this student and requirement schedule
            submission = None
            for sub in schedule.certificate_submissions:
                if sub.student_id == student.id:
                    submission = sub
                    break

            requirement_data = StudentRequirementWithSubmissionResponse(
                # Schedule data
                schedule_id=str(schedule.id),
                submission_deadline=schedule.submission_deadline.isoformat(),
                # Requirement data
                requirement_id=str(requirement.id),
                requirement_name=requirement.name,
                target_year=requirement.target_year,
                is_mandatory=requirement.is_mandatory,
                special_instruction=requirement.special_instruction,
                # Program data
                program_id=str(program.id),
                program_code=program.program_code,
                program_name=program.program_name,
                # Certificate type data
                cert_type_id=str(cert_type.id),
                cert_code=cert_type.cert_code,
                cert_name=cert_type.cert_name,
                cert_description=cert_type.description,
                # Submission data (empty if not submitted)
                submission_id=str(submission.id) if submission else None,
                file_object_name=submission.file_object_name if submission else None,
                filename=submission.filename if submission else None,
                file_size=submission.file_size if submission else None,
                mime_type=submission.mime_type if submission else None,
                submission_status=(
                    submission.submission_status.value if submission else None
                ),
                agent_confidence_score=(
                    submission.agent_confidence_score if submission else None
                ),
                submission_timing=(
                    submission.submission_timing.value if submission else None
                ),
                submitted_at=(
                    submission.submitted_at.isoformat() if submission else None
                ),
                expired_at=(
                    submission.expired_at.isoformat()
                    if submission and submission.expired_at
                    else None
                ),
            )

            requirements_data.append(requirement_data)

        return requirements_data

    async def submit_certificate(
        self,
        student: Student,
        submission_data: RequirementSubmissionRequest,
        file: UploadFile,
    ) -> RequirementSubmissionResponse:
        """Submit or update a certificate for verification"""

        # Validate and parse UUIDs
        try:
            schedule_uuid = UUID(submission_data.schedule_id)
            requirement_uuid = UUID(submission_data.requirement_id)
            cert_type_uuid = UUID(submission_data.cert_type_id)
            program_uuid = UUID(submission_data.program_id)
        except ValueError:
            raise BusinessLogicError("Invalid request data format")

        # Validate certificate type exists
        cert_type = await self._get_certificate_type(cert_type_uuid)

        # Validate requirement schedule and relationships
        schedule = await self._validate_requirement_schedule(
            schedule_uuid, requirement_uuid, cert_type_uuid, program_uuid
        )

        # Validate student permissions
        self._validate_student_permissions(student, program_uuid, schedule)

        # Handle submission logic (new vs edit)
        is_edit = bool(submission_data.submission_id)
        existing_submission = None

        if is_edit:
            existing_submission = await self._validate_existing_submission(
                submission_data.submission_id, student.id, schedule_uuid
            )
        else:
            await self._check_duplicate_submission(student.id, schedule_uuid)

        # Validate and upload file
        file_size = await self._validate_file_constraints(file)
        upload_result = await self._upload_file_to_storage(file, cert_type.cert_code)

        # Create or update submission
        submission = await self._process_submission(
            is_edit,
            existing_submission,
            student,
            schedule_uuid,
            cert_type_uuid,
            upload_result,
            file,
            file_size,
            schedule.submission_deadline,
        )

        return RequirementSubmissionResponse(submission_id=str(submission.id))

    async def _get_certificate_type(self, cert_type_uuid: UUID) -> CertificateType:
        """Get and validate certificate type"""
        cert_type_stmt = select(CertificateType).where(
            CertificateType.id == cert_type_uuid
        )
        cert_type_result = await self.db.execute(cert_type_stmt)
        cert_type = cert_type_result.scalar_one_or_none()

        if not cert_type:
            raise BusinessLogicError("Certificate type not found")

        return cert_type

    async def _validate_requirement_schedule(
        self,
        schedule_uuid: UUID,
        requirement_uuid: UUID,
        cert_type_uuid: UUID,
        program_uuid: UUID,
    ) -> ProgramRequirementSchedule:
        """Validate requirement schedule and all relationships"""
        schedule_stmt = (
            select(ProgramRequirementSchedule)
            .join(ProgramRequirement)
            .join(Program)
            .where(
                ProgramRequirementSchedule.id == schedule_uuid,
                ProgramRequirement.id == requirement_uuid,
                ProgramRequirement.cert_type_id == cert_type_uuid,
                Program.id == program_uuid,
            )
            .options(
                selectinload(
                    ProgramRequirementSchedule.program_requirement
                ).selectinload(ProgramRequirement.program),
                selectinload(
                    ProgramRequirementSchedule.program_requirement
                ).selectinload(ProgramRequirement.certificate_type),
            )
        )
        schedule_result = await self.db.execute(schedule_stmt)
        schedule = schedule_result.scalar_one_or_none()

        if not schedule:
            raise BusinessLogicError("Invalid requirement data")

        return schedule

    def _validate_student_permissions(
        self, student: Student, program_uuid: UUID, schedule: ProgramRequirementSchedule
    ):
        """Validate student belongs to correct program and academic year"""
        if (
            student.program_id != program_uuid
            or student.academic_year_id != schedule.academic_year_id
        ):
            raise BusinessLogicError("Not enrolled in this program")

    async def _validate_existing_submission(
        self, submission_id: str | None, student_id: UUID, schedule_uuid: UUID
    ) -> CertificateSubmission:
        """Validate existing submission for editing"""
        try:
            submission_uuid = UUID(submission_id)
        except (ValueError, TypeError):
            raise BusinessLogicError("Invalid submission ID")

        existing_submission_stmt = select(CertificateSubmission).where(
            CertificateSubmission.id == submission_uuid,
            CertificateSubmission.student_id == student_id,
            CertificateSubmission.requirement_schedule_id == schedule_uuid,
        )
        existing_submission_result = await self.db.execute(existing_submission_stmt)
        existing_submission = existing_submission_result.scalar_one_or_none()

        if not existing_submission:
            raise BusinessLogicError("Submission not found")

        # Check if submission can be edited
        if existing_submission.submission_status == SubmissionStatus.PENDING:
            raise BusinessLogicError("Submission under review - cannot edit")

        if existing_submission.submission_status == SubmissionStatus.APPROVED:
            raise BusinessLogicError("Approved submission cannot be edited")

        return existing_submission

    async def _check_duplicate_submission(self, student_id: UUID, schedule_uuid: UUID):
        """Check for duplicate submissions in new mode"""
        duplicate_check_stmt = select(CertificateSubmission).where(
            CertificateSubmission.student_id == student_id,
            CertificateSubmission.requirement_schedule_id == schedule_uuid,
        )
        duplicate_result = await self.db.execute(duplicate_check_stmt)
        duplicate_submission = duplicate_result.scalar_one_or_none()

        if duplicate_submission:
            raise BusinessLogicError("Submission already exists for this requirement")

    async def _validate_file_constraints(self, file: UploadFile) -> int:
        """Validate file constraints and return file size"""
        if not file.filename:
            raise BusinessLogicError("File must have a valid name")

        # Get file size
        file_content = await file.read()
        file_size = len(file_content)
        await file.seek(0)  # Reset file pointer

        # Validate file size (10MB limit)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if file_size > MAX_FILE_SIZE:
            raise BusinessLogicError("File too large (max 10MB)")

        # Validate file type
        SUPPORTED_MIME_TYPES = {
            "application/pdf",
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/webp",
        }

        if file.content_type not in SUPPORTED_MIME_TYPES:
            raise BusinessLogicError("File type not supported")

        return file_size

    async def _upload_file_to_storage(self, file: UploadFile, cert_code: str) -> dict:
        """Upload file to MinIO storage"""
        upload_result = await self.minio.upload_file(
            file=file, prefix=cert_code, filename=file.filename
        )

        if not upload_result["success"]:
            raise BusinessLogicError("File upload failed")

        return upload_result

    async def _process_submission(
        self,
        is_edit: bool,
        existing_submission: Optional[CertificateSubmission],
        student: Student,
        schedule_uuid: UUID,
        cert_type_uuid: UUID,
        upload_result: dict,
        file: UploadFile,
        file_size: int,
        submission_deadline: datetime,
    ) -> CertificateSubmission:
        """Create new submission or update existing one"""

        if is_edit and existing_submission:
            # Update existing submission
            old_file_object_name = existing_submission.file_object_name

            # Update submission record
            existing_submission.file_object_name = upload_result["object_name"]
            existing_submission.filename = file.filename or "unknown"
            existing_submission.file_size = file_size
            existing_submission.mime_type = (
                file.content_type or "application/octet-stream"
            )

            # Reset verification fields for re-processing
            existing_submission.submission_status = SubmissionStatus.PENDING
            existing_submission.agent_confidence_score = 0.0
            existing_submission.submitted_at = datetime.now(timezone.utc)

            # Update timing
            current_time = datetime.now(timezone.utc)
            if current_time <= submission_deadline:
                existing_submission.submission_timing = SubmissionTiming.ON_TIME
            else:
                existing_submission.submission_timing = SubmissionTiming.LATE

            await self.db.commit()
            await self.db.refresh(existing_submission)

            # Clean up old file
            try:
                await self.minio.delete_file(old_file_object_name)
            except Exception as e:
                logger.info(f"Old file cleanup failed: {old_file_object_name}")

            return existing_submission

        else:
            # Create new submission
            current_time = datetime.now(timezone.utc)
            if current_time <= submission_deadline:
                timing = SubmissionTiming.ON_TIME
            else:
                timing = SubmissionTiming.LATE

            submission = CertificateSubmission(
                student_id=student.id,
                cert_type_id=cert_type_uuid,
                requirement_schedule_id=schedule_uuid,
                file_object_name=upload_result["object_name"],
                filename=file.filename,
                file_size=file_size,
                mime_type=file.content_type or "application/octet-stream",
                agent_confidence_score=0.0,
                submission_timing=timing,
            )

            self.db.add(submission)
            await self.db.commit()
            await self.db.refresh(submission)

            return submission
