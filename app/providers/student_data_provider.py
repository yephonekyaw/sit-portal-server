from datetime import datetime
from typing import List
import uuid

from app.db.models import (
    AcademicYear,
    Program,
    User,
    Student,
    UserType,
    EnrollmentStatus,
)
from app.utils.logging import get_logger
from app.models.staff_models import ParsedStudentRecord
from app.db.session import SessionLocal

logger = get_logger()


class StudentDataProvider:
    def __init__(self, student_data: List[ParsedStudentRecord]):
        self.db = SessionLocal()
        self.student_data = student_data
        self.processed_emails = set()
        self.processed_student_ids = set()
        self.new_users: List[User] = []
        self.new_students: List[Student] = []

    def process(self) -> None:
        self._load_existing_identifiers()

        for student in self.student_data:
            if self._is_duplicate(student):
                continue

            academic_year = self._get_or_create_academic_year(student.academicYear)
            program = self._get_program(student.programCode)

            if not program:
                raise ValueError(f"{student.programCode} not found in database.")

            self._create_user_and_student(student, program, academic_year)

        self._commit_changes()

    def _load_existing_identifiers(self) -> None:
        existing_emails = self.db.query(User.email).all()
        self.processed_emails.update(email for email, in existing_emails)

        existing_student_ids = self.db.query(Student.roll_number).all()
        self.processed_student_ids.update(sid for sid, in existing_student_ids)

    def _is_duplicate(self, student: ParsedStudentRecord) -> bool:
        email = student.email
        student_id = student.studentId
        if email in self.processed_emails or student_id in self.processed_student_ids:
            return True
        return False

    def _get_or_create_academic_year(self, year_code: str) -> AcademicYear:
        if not year_code:
            raise ValueError("Academic year cannot be empty.")

        academic_year = (
            self.db.query(AcademicYear).filter_by(year_code=year_code).first()
        )

        if not academic_year:
            try:
                start_year = int(year_code.split("-")[0])
                academic_year = AcademicYear(
                    year_code=year_code,
                    start_date=datetime(start_year, 8, 1),
                    end_date=datetime(start_year + 1, 6, 1),
                    is_current=True,
                )
                self.db.add(academic_year)
                self.db.flush()
            except (ValueError, IndexError):
                raise ValueError(
                    "Invalid academic year format. Expected format: YYYY-YYYY."
                )
        return academic_year

    def _get_program(self, program_code: str) -> Program:
        program = self.db.query(Program).filter_by(program_code=program_code).first()
        if not program:
            raise KeyError("Program code cannot be found in database.")
        return program

    def _create_user_and_student(
        self,
        student: ParsedStudentRecord,
        program: Program,
        academic_year: AcademicYear,
    ) -> None:
        user_id = uuid.uuid4()
        new_user = User(
            id=user_id,
            first_name=student.firstName,
            last_name=student.lastName,
            email=student.email,
            user_type=UserType.STUDENT,
        )
        self.new_users.append(new_user)

        new_student = Student(
            user_id=user_id,
            sit_email=student.email,
            roll_number=student.studentId,
            program_id=program.id,
            academic_year_id=academic_year.id,
            enrollment_status=EnrollmentStatus.ACTIVE,
        )
        self.new_students.append(new_student)
        self.processed_emails.add(new_user.email)
        self.processed_student_ids.add(new_student.roll_number)

    def _commit_changes(self) -> None:
        if not self.new_users and not self.new_students:
            return

        try:
            self.db.add_all(self.new_users)
            self.db.add_all(self.new_students)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        finally:
            self.db.close()


def handle_student_data(student_data: List[ParsedStudentRecord]) -> None:
    handler = StudentDataProvider(student_data)
    handler.process()
