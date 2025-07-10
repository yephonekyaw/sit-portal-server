from datetime import datetime
from typing import List, Dict, Set
import uuid

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
        self.student_data = student_data
        self.existing_emails: Set[str] = set()
        self.existing_student_ids: Set[str] = set()
        self.programs_cache: Dict[str, Program] = {}

    async def process_imported_student_data(self) -> Dict[str, int]:
        """Process student data and create user and student records"""
        stats = {"processed": 0, "skipped": 0, "created": 0}

        async with AsyncSessionLocal() as db:
            try:
                # Load existing data
                await self._load_existing_data(db)

                # Remove duplicates from input
                unique_students = self._remove_duplicates()

                # Process each student
                for student in unique_students:
                    try:
                        if self._should_skip_student(student):
                            stats["skipped"] += 1
                            continue

                        await self._create_student_record(db, student)
                        stats["processed"] += 1
                        stats["created"] += 1

                    except Exception as e:
                        stats["skipped"] += 1

                await db.commit()
                return stats

            except Exception as e:
                await db.rollback()
                raise

    async def _load_existing_data(self, db: AsyncSession) -> None:
        """Load existing emails, student IDs, and programs"""
        # Load existing emails
        email_stmt = select(User.email)
        email_result = await db.execute(email_stmt)
        self.existing_emails = {email for email, in email_result.fetchall()}

        # Load existing student IDs
        student_id_stmt = select(Student.roll_number)
        student_id_result = await db.execute(student_id_stmt)
        self.existing_student_ids = {sid for sid, in student_id_result.fetchall()}

        # Load programs cache
        programs_stmt = select(Program).where(Program.is_active == True)
        programs_result = await db.execute(programs_stmt)
        programs = programs_result.scalars().all()
        self.programs_cache = {program.program_code: program for program in programs}

    def _remove_duplicates(self) -> List[ParsedStudentRecord]:
        """Remove duplicates from input data"""
        seen_emails = set()
        seen_student_ids = set()
        unique_students = []

        for student in self.student_data:
            if student.email in seen_emails or student.studentId in seen_student_ids:
                continue

            seen_emails.add(student.email)
            seen_student_ids.add(student.studentId)
            unique_students.append(student)

        return unique_students

    def _should_skip_student(self, student: ParsedStudentRecord) -> bool:
        """Check if student should be skipped"""
        return (
            student.email in self.existing_emails
            or student.studentId in self.existing_student_ids
        )

    async def _create_student_record(
        self, db: AsyncSession, student: ParsedStudentRecord
    ) -> None:
        """Create user and student records"""
        # Get or create academic year
        academic_year = await self._get_or_create_academic_year(
            db, student.academicYear
        )

        # Get program
        program = self.programs_cache.get(student.programCode)
        if not program:
            raise ValueError(f"Program {student.programCode} not found")

        # Create user
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            first_name=student.firstName.strip(),
            last_name=student.lastName.strip(),
            email=student.email.lower(),
            user_type=UserType.STUDENT,
        )
        db.add(user)

        # Create student
        student_record = Student(
            user_id=user_id,
            sit_email=student.email.lower(),
            roll_number=student.studentId,
            program_id=program.id,
            academic_year_id=academic_year.id,
            enrollment_status=EnrollmentStatus.ACTIVE,
        )
        db.add(student_record)

        # Update tracking sets
        self.existing_emails.add(user.email)
        self.existing_student_ids.add(student_record.roll_number)

    async def _get_or_create_academic_year(
        self, db: AsyncSession, year_code: str
    ) -> AcademicYear:
        """Get or create academic year"""
        if not year_code:
            raise ValueError("Academic year cannot be empty")

        # Check if exists
        stmt = select(AcademicYear).where(AcademicYear.year_code == year_code)
        result = await db.execute(stmt)
        academic_year = result.scalar_one_or_none()

        if academic_year:
            return academic_year

        # Create new one
        try:
            start_year_str, end_year_str = year_code.split("-")
            start_year = int(start_year_str)
            end_year = int(end_year_str)

            if end_year != start_year + 1:
                raise ValueError("End year must be start year + 1")

            academic_year = AcademicYear(
                year_code=year_code,
                start_date=datetime(start_year, 8, 1),
                end_date=datetime(end_year, 6, 30),
                is_current=True,
            )
            db.add(academic_year)
            await db.flush()
            return academic_year

        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid academic year format '{year_code}': {e}")
