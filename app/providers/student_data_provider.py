from datetime import datetime
from typing import List, Dict, Tuple
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AcademicYear,
    Program,
    User,
    Student,
    UserType,
    EnrollmentStatus,
)
from app.models.staff_models import ParsedStudentRecord
from app.db.session import AsyncSessionLocal


class StudentDataProvider:
    def __init__(self, student_data: List[ParsedStudentRecord]):
        self.raw_student_data = student_data
        self.student_data: List[ParsedStudentRecord] = []
        self.programs_cache: Dict[str, Program] = {}
        self._is_initialized = False

    async def initialize(self):
        """Initialize and pre-process student data"""
        if self._is_initialized:
            return

        async with AsyncSessionLocal.begin() as db:
            await self._load_existing_data(db)
            self.student_data = self._get_valid_students()
            self._is_initialized = True

    def _get_valid_students(self) -> List[ParsedStudentRecord]:
        """Get unique students that don't already exist in database"""
        seen = set()
        valid_students = []

        for student in self.raw_student_data:
            # Create unique identifier
            student_key = (student.email.lower(), student.studentId)

            # Skip if duplicate or already exists
            if student_key in seen or student_key in self.existing_students:
                continue

            seen.add(student_key)
            valid_students.append(student)

        return valid_students

    async def count_students_by_academic_year_and_program(
        self,
    ) -> Dict[Tuple[str, str], int]:
        """Count students by academic year and program code"""
        await self.initialize()

        counts = defaultdict(int)
        for student in self.student_data:
            key = (student.academicYear, student.programCode)
            counts[key] += 1

        return dict(counts)

    async def process_imported_student_data(self) -> Dict[str, int]:
        """Process student data and create user and student records"""
        await self.initialize()

        stats = {"processed": 0, "skipped": 0, "created": 0}

        async with AsyncSessionLocal.begin() as db:
            try:
                for student in self.student_data:
                    try:
                        await self._create_student_record(db, student)
                        stats["created"] += 1
                        stats["processed"] += 1
                    except Exception:
                        stats["skipped"] += 1
                return stats

            except Exception:
                await db.rollback()
                raise

    async def _load_existing_data(self, db: AsyncSession) -> None:
        """Load existing students and programs"""
        # Load existing students as set of tuples for fast lookup
        student_stmt = select(Student.sit_email, Student.roll_number)
        result = await db.execute(student_stmt)
        self.existing_students = {
            (email.lower(), roll_number)
            for email, roll_number in result.fetchall()
            if email and roll_number
        }

        # Load programs cache
        programs_stmt = select(Program).where(Program.is_active == True)
        programs = await db.execute(programs_stmt)
        self.programs_cache = {
            program.program_code: program for program in programs.scalars().all()
        }

    async def _create_student_record(
        self, db: AsyncSession, student: ParsedStudentRecord
    ) -> None:
        """Create user and student records"""
        # Get program (will raise KeyError if not found)
        program = self.programs_cache[student.programCode]

        # Get or create academic year
        academic_year = await self._get_or_create_academic_year(
            db, student.academicYear
        )

        # Create user and student in one go
        user_id = uuid.uuid4()
        email = student.email.lower()

        user = User(
            id=user_id,
            first_name=student.firstName.strip(),
            last_name=student.lastName.strip(),
            email=email,
            user_type=UserType.STUDENT,
        )

        student_record = Student(
            user_id=user_id,
            sit_email=email,
            roll_number=student.studentId,
            program_id=program.id,
            academic_year_id=academic_year.id,
            enrollment_status=EnrollmentStatus.ACTIVE,
        )

        db.add_all([user, student_record])

    async def _get_or_create_academic_year(
        self, db: AsyncSession, year_code: str
    ) -> AcademicYear:
        """Get or create academic year"""
        if not year_code:
            raise ValueError("Academic year cannot be empty")

        # Try to get existing
        stmt = select(AcademicYear).where(AcademicYear.year_code == year_code)
        result = await db.execute(stmt)
        academic_year = result.scalar_one_or_none()

        if academic_year:
            return academic_year

        # Create new one
        start_year, end_year = int(year_code), int(year_code) + 4

        academic_year = AcademicYear(
            year_code=year_code,
            start_date=datetime(start_year, 8, 1),
            end_date=datetime(end_year, 6, 30),
            is_current=True,
        )
        db.add(academic_year)
        await db.flush()
        return academic_year

    def get_processed_count(self) -> int:
        """Get count of processed student records"""
        if not self._is_initialized:
            raise RuntimeError("Call initialize() first")
        return len(self.student_data)
