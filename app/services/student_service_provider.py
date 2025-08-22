from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Student, Program, AcademicYear, EnrollmentStatus
from app.utils.logging import get_logger

logger = get_logger()


class StudentServiceProvider:
    """Service provider for student-related operations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_active_student_count_by_program_and_year(
        self, program_code: str, academic_year_code: int
    ) -> int:
        """
        Get the count of active students for a specific program and academic year.

        Args:
            program_code: The program code (e.g., "CS", "ENG")
            academic_year_code: The academic year code (e.g., 2024)

        Returns:
            Number of active students matching the criteria
        """
        result = await self.db.execute(
            select(func.count(Student.id))
            .join(Program, Student.program_id == Program.id)
            .join(AcademicYear, Student.academic_year_id == AcademicYear.id)
            .where(
                and_(
                    Program.program_code == program_code,
                    AcademicYear.year_code == academic_year_code,
                    Student.enrollment_status == EnrollmentStatus.ACTIVE,
                )
            )
        )

        count = result.scalar_one()

        logger.info(
            "Retrieved active student count",
            program_code=program_code,
            academic_year_code=academic_year_code,
            count=count,
        )

        return count
