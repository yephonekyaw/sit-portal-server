from typing import List, Dict, Any, Optional, Sequence
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.utils.logging import get_logger
from app.db.models import (
    CertificateSubmission,
    Student,
    User,
    Program,
    CertificateType,
    ProgramRequirement,
    ProgramRequirementSchedule,
    AcademicYear,
    VerificationHistory,
)
from app.db.session import get_async_session
from app.schemas.staff.certificate_submission_schemas import (
    CertificateSubmissionResponse,
    CertificateSubmissionsListResponse,
    VerificationHistoryResponse,
    VerificationHistoryListResponse,
    CreateVerificationHistoryRequest,
    CertificateSubmissionDataResponse,
    UserInfo,
    StudentInfo,
    ProgramInfo,
    CertificateInfo,
    ProgramRequirementInfo,
    ProgramRequirementScheduleInfo,
)

logger = get_logger()


class SubmissionServiceProvider:
    """Service provider for submission-related business logic and database operations"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ========== PUBLIC API METHODS ==========

    async def get_certificate_submissions_by_year(
        self, year_code: int, is_submitted: bool = True
    ) -> CertificateSubmissionsListResponse:
        """Get certificate submissions for a specific year with all related information"""
        try:
            if is_submitted:
                return await self._get_submitted_certificates_by_year(year_code)
            else:
                return await self._get_non_submitted_certificates_by_year(year_code)
        except Exception as e:
            logger.error(f"Failed to get certificate submissions for year {year_code}: {str(e)}")
            raise RuntimeError(f"CERTIFICATE_SUBMISSIONS_RETRIEVAL_FAILED: {str(e)}")

    async def get_verification_history_by_submission_id(
        self, submission_id: uuid.UUID
    ) -> VerificationHistoryListResponse:
        """Get verification history for a specific certificate submission"""
        try:
            # Validate submission exists
            await self._validate_submission_exists(submission_id)

            # Get verification history
            history_records = await self._fetch_verification_history(submission_id)

            # Transform to response format
            history_responses = [
                self._transform_verification_history_to_response(record)
                for record in history_records
            ]

            return VerificationHistoryListResponse(
                verification_history=history_responses,
                total_count=len(history_responses),
                submission_id=submission_id,
            )

        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to get verification history for submission {submission_id}: {str(e)}")
            raise RuntimeError(f"VERIFICATION_HISTORY_RETRIEVAL_FAILED: {str(e)}")

    async def get_certificate_submission_by_id(
        self, submission_id: uuid.UUID
    ) -> Optional[CertificateSubmissionResponse]:
        """Get complete certificate submission data by ID with all related information"""
        try:
            submission = await self._fetch_submission_with_relations(submission_id)

            if not submission:
                return None

            return self._transform_submission_to_response(submission)

        except Exception as e:
            logger.error(f"Failed to get certificate submission by ID {submission_id}: {str(e)}")
            raise RuntimeError(f"CERTIFICATE_SUBMISSION_RETRIEVAL_FAILED: {str(e)}")

    async def create_verification_history(
        self,
        submission_id: uuid.UUID,
        verification_data: CreateVerificationHistoryRequest,
    ) -> VerificationHistoryResponse:
        """Create a new verification history record for a certificate submission"""
        try:
            # Validate submission exists
            await self._validate_submission_exists(submission_id)

            # Validate status change
            self._validate_status_change(
                verification_data.old_status, verification_data.new_status
            )

            # Create and persist verification history
            new_verification = await self._create_and_persist_verification_history(
                submission_id, verification_data
            )

            return self._transform_verification_history_to_response(new_verification)

        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to create verification history for submission {submission_id}: {str(e)}")
            raise RuntimeError(f"VERIFICATION_HISTORY_CREATION_FAILED: {str(e)}")

    # ========== PRIVATE HELPER METHODS ==========

    async def _get_submitted_certificates_by_year(
        self, year_code: int
    ) -> CertificateSubmissionsListResponse:
        """Get submitted certificates with all related information"""
        query = (
            select(CertificateSubmission)
            .options(
                selectinload(CertificateSubmission.student).selectinload(Student.user),
                selectinload(CertificateSubmission.student).selectinload(
                    Student.program
                ),
                selectinload(CertificateSubmission.certificate_type),
                selectinload(CertificateSubmission.requirement_schedule).selectinload(
                    ProgramRequirementSchedule.program_requirement
                ),
                selectinload(CertificateSubmission.requirement_schedule).selectinload(
                    ProgramRequirementSchedule.academic_year
                ),
            )
            .join(CertificateSubmission.requirement_schedule)
            .join(ProgramRequirementSchedule.academic_year)
            .where(AcademicYear.year_code == year_code)
            .order_by(CertificateSubmission.submitted_at.desc())
        )

        result = await self.db.execute(query)
        submissions = result.scalars().all()

        submission_responses = [
            self._transform_submission_to_response(submission)
            for submission in submissions
        ]

        return CertificateSubmissionsListResponse(
            submissions=submission_responses,
            total_count=len(submission_responses),
            year_code=year_code,
            is_submitted_filter=True,
        )

    async def _get_non_submitted_certificates_by_year(
        self, year_code: int
    ) -> CertificateSubmissionsListResponse:
        """Get students who haven't submitted certificates for the year"""
        # Get all program requirement schedules for the year
        schedules = await self._fetch_program_requirement_schedules_by_year(year_code)

        not_submitted_responses = []

        for schedule in schedules:
            students = await self._fetch_students_for_schedule(schedule)

            for student in students:
                if not await self._has_student_submitted_for_schedule(
                    student.id, schedule
                ):
                    response_data = self._create_non_submitted_response(
                        student, schedule
                    )
                    not_submitted_responses.append(response_data)

        return CertificateSubmissionsListResponse(
            submissions=not_submitted_responses,
            total_count=len(not_submitted_responses),
            year_code=year_code,
            is_submitted_filter=False,
        )

    async def _fetch_program_requirement_schedules_by_year(
        self, year_code: int
    ) -> Sequence[ProgramRequirementSchedule]:
        """Fetch program requirement schedules for a given year"""
        schedule_query = (
            select(ProgramRequirementSchedule)
            .options(
                selectinload(
                    ProgramRequirementSchedule.program_requirement
                ).selectinload(ProgramRequirement.program),
                selectinload(
                    ProgramRequirementSchedule.program_requirement
                ).selectinload(ProgramRequirement.certificate_type),
                selectinload(ProgramRequirementSchedule.academic_year),
            )
            .join(ProgramRequirementSchedule.academic_year)
            .where(AcademicYear.year_code == year_code)
        )

        result = await self.db.execute(schedule_query)
        return result.scalars().all()

    async def _fetch_students_for_schedule(
        self, schedule: ProgramRequirementSchedule
    ) -> Sequence[Student]:
        """Fetch students who should submit for a given schedule"""
        students_query = (
            select(Student)
            .options(selectinload(Student.user), selectinload(Student.program))
            .where(Student.program_id == schedule.program_requirement.program_id)
            .where(Student.academic_year_id == schedule.academic_year_id)
        )

        result = await self.db.execute(students_query)
        return result.scalars().all()

    async def _has_student_submitted_for_schedule(
        self, student_id: uuid.UUID, schedule: ProgramRequirementSchedule
    ) -> bool:
        """Check if student has already submitted for a schedule"""
        existing_submission_query = select(CertificateSubmission).where(
            and_(
                CertificateSubmission.student_id == student_id,
                CertificateSubmission.requirement_schedule_id == schedule.id,
                CertificateSubmission.cert_type_id
                == schedule.program_requirement.cert_type_id,
            )
        )

        result = await self.db.execute(existing_submission_query)
        return result.scalar_one_or_none() is not None

    async def _validate_submission_exists(
        self, submission_id: uuid.UUID
    ) -> CertificateSubmission:
        """Validate that a submission exists"""
        submission_query = select(CertificateSubmission).where(
            CertificateSubmission.id == submission_id
        )
        submission_result = await self.db.execute(submission_query)
        submission = submission_result.scalar_one_or_none()

        if not submission:
            raise ValueError("CERTIFICATE_SUBMISSION_NOT_FOUND")

        return submission

    async def _fetch_verification_history(
        self, submission_id: uuid.UUID
    ) -> Sequence[VerificationHistory]:
        """Fetch verification history for a submission"""
        history_query = (
            select(VerificationHistory)
            .where(VerificationHistory.submission_id == submission_id)
            .order_by(VerificationHistory.created_at.desc())
        )

        history_result = await self.db.execute(history_query)
        return history_result.scalars().all()

    async def _fetch_submission_with_relations(
        self, submission_id: uuid.UUID
    ) -> Optional[CertificateSubmission]:
        """Fetch submission with all related information loaded"""
        query = (
            select(CertificateSubmission)
            .options(
                selectinload(CertificateSubmission.student).selectinload(Student.user),
                selectinload(CertificateSubmission.student).selectinload(
                    Student.program
                ),
                selectinload(CertificateSubmission.certificate_type),
                selectinload(CertificateSubmission.requirement_schedule).selectinload(
                    ProgramRequirementSchedule.program_requirement
                ),
                selectinload(CertificateSubmission.requirement_schedule).selectinload(
                    ProgramRequirementSchedule.academic_year
                ),
                selectinload(CertificateSubmission.verification_history),
            )
            .where(CertificateSubmission.id == submission_id)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _validate_status_change(self, old_status, new_status):
        """Validate that status change is valid"""
        if old_status == new_status:
            raise ValueError("OLD_STATUS_SAME_AS_NEW_STATUS")

    async def _create_and_persist_verification_history(
        self,
        submission_id: uuid.UUID,
        verification_data: CreateVerificationHistoryRequest,
    ) -> VerificationHistory:
        """Create and persist verification history record"""
        new_verification = VerificationHistory(
            submission_id=submission_id,
            verifier_id=verification_data.verifier_id,
            verification_type=verification_data.verification_type,
            old_status=verification_data.old_status,
            new_status=verification_data.new_status,
            comments=verification_data.comments,
            reasons=verification_data.reasons,
            agent_analysis_result=verification_data.agent_analysis_result,
        )

        self.db.add(new_verification)
        await self.db.flush()  # Flush to get the ID
        await self.db.refresh(new_verification)  # Refresh to get all fields

        return new_verification

    # ========== TRANSFORMATION METHODS ==========

    def _transform_submission_to_response(
        self, submission: CertificateSubmission
    ) -> CertificateSubmissionResponse:
        """Transform submission ORM object to response schema"""
        return CertificateSubmissionResponse(
            # Certificate submission fields
            id=submission.id,
            file_object_name=submission.file_object_name,
            filename=submission.filename,
            file_size=submission.file_size,
            mime_type=submission.mime_type,
            submission_status=submission.submission_status,
            agent_confidence_score=submission.agent_confidence_score,
            submission_timing=submission.submission_timing,
            submitted_at=submission.submitted_at,
            expired_at=submission.expired_at,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            # Related information
            user=UserInfo(
                first_name=submission.student.user.first_name,
                last_name=submission.student.user.last_name,
            ),
            student=StudentInfo(
                sit_email=submission.student.sit_email,
                roll_number=submission.student.roll_number,
            ),
            program=ProgramInfo(
                program_code=submission.student.program.program_code,
                program_name=submission.student.program.program_name,
            ),
            certificate=CertificateInfo(
                cert_code=submission.certificate_type.cert_code,
                cert_name=submission.certificate_type.cert_name,
            ),
            program_requirement=ProgramRequirementInfo(
                target_year=submission.requirement_schedule.program_requirement.target_year,
                is_mandatory=submission.requirement_schedule.program_requirement.is_mandatory,
            ),
            program_requirement_schedule=ProgramRequirementScheduleInfo(
                submission_deadline=submission.requirement_schedule.submission_deadline,
                grace_period_deadline=submission.requirement_schedule.grace_period_deadline,
            ),
        )

    def _transform_verification_history_to_response(
        self, record: VerificationHistory
    ) -> VerificationHistoryResponse:
        """Transform verification history ORM object to response schema"""
        return VerificationHistoryResponse(
            id=record.id,
            verification_type=record.verification_type,
            old_status=record.old_status,
            new_status=record.new_status,
            comments=record.comments,
            reasons=record.reasons,
            agent_analysis_result=record.agent_analysis_result,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _create_non_submitted_response(
        self, student: Student, schedule: ProgramRequirementSchedule
    ) -> Dict[str, Any]:
        """Create response data for non-submitted students"""
        return {
            # Null certificate submission fields
            "id": None,
            "file_object_name": None,
            "filename": None,
            "file_size": None,
            "mime_type": None,
            "submission_status": None,
            "agent_confidence_score": None,
            "submission_timing": None,
            "submitted_at": None,
            "expired_at": None,
            "created_at": None,
            "updated_at": None,
            # Related information
            "user": UserInfo(
                first_name=student.user.first_name,
                last_name=student.user.last_name,
            ),
            "student": StudentInfo(
                sit_email=student.sit_email,
                roll_number=student.roll_number,
            ),
            "program": ProgramInfo(
                program_code=student.program.program_code,
                program_name=student.program.program_name,
            ),
            "certificate": CertificateInfo(
                cert_code=schedule.program_requirement.certificate_type.cert_code,
                cert_name=schedule.program_requirement.certificate_type.cert_name,
            ),
            "program_requirement": ProgramRequirementInfo(
                target_year=schedule.program_requirement.target_year,
                is_mandatory=schedule.program_requirement.is_mandatory,
            ),
            "program_requirement_schedule": ProgramRequirementScheduleInfo(
                submission_deadline=schedule.submission_deadline,
                grace_period_deadline=schedule.grace_period_deadline,
            ),
        }


def get_submission_service(
    db_session: AsyncSession = Depends(get_async_session),
) -> SubmissionServiceProvider:
    """Dependency function to get SubmissionServiceProvider instance"""
    return SubmissionServiceProvider(db_session)
