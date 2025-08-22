import pytest
import asyncio
import uuid
from datetime import datetime, timezone, date
from typing import AsyncGenerator, Generator
from unittest.mock import Mock

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Program, CertificateType, ProgramRequirement, AcademicYear, ProgramRequirementSchedule
from app.db.models import ProgReqRecurrenceType


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for each test."""
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing retry behavior."""
    mock_task = Mock()
    mock_task.request.retries = 0
    mock_task.max_retries = 3
    mock_task.retry = Mock(side_effect=Exception("Retry called"))
    return mock_task


# Test data factories
@pytest_asyncio.fixture
async def sample_program(db_session: AsyncSession) -> Program:
    """Create a sample program for testing."""
    program = Program(
        id=uuid.uuid4(),
        program_code="CS",
        program_name="Computer Science",
        description="Computer Science Program",
        duration_years=4,
        is_active=True
    )
    db_session.add(program)
    await db_session.commit()
    await db_session.refresh(program)
    return program


@pytest_asyncio.fixture
async def sample_certificate_type(db_session: AsyncSession) -> CertificateType:
    """Create a sample certificate type for testing."""
    cert_type = CertificateType(
        id=uuid.uuid4(),
        code="CITI_CERT",
        name="CITI Program Certificate",
        description="CITI Program Research Ethics Certificate",
        verification_template="Test template",
        has_expiration=False,
        is_active=True
    )
    db_session.add(cert_type)
    await db_session.commit()
    await db_session.refresh(cert_type)
    return cert_type


@pytest_asyncio.fixture
async def sample_academic_year_2024(db_session: AsyncSession) -> AcademicYear:
    """Create academic year 2024 for testing."""
    academic_year = AcademicYear(
        id=uuid.uuid4(),
        year_code=2024,
        start_date=datetime(2024, 8, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 5, 31, 23, 59, 59, tzinfo=timezone.utc),
        is_current=True
    )
    db_session.add(academic_year)
    await db_session.commit()
    await db_session.refresh(academic_year)
    return academic_year


@pytest_asyncio.fixture
async def sample_academic_year_2025(db_session: AsyncSession) -> AcademicYear:
    """Create academic year 2025 for testing."""
    academic_year = AcademicYear(
        id=uuid.uuid4(),
        year_code=2025,
        start_date=datetime(2025, 8, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 5, 31, 23, 59, 59, tzinfo=timezone.utc),
        is_current=False
    )
    db_session.add(academic_year)
    await db_session.commit()
    await db_session.refresh(academic_year)
    return academic_year


@pytest_asyncio.fixture
async def active_program_requirement(
    db_session: AsyncSession,
    sample_program: Program,
    sample_certificate_type: CertificateType
) -> ProgramRequirement:
    """Create an active program requirement for testing."""
    requirement = ProgramRequirement(
        id=uuid.uuid4(),
        program_id=sample_program.id,
        cert_type_id=sample_certificate_type.id,
        name="CITI Program Research Ethics Training",
        target_year=4,
        deadline_date=date(2000, 3, 15),  # March 15
        grace_period_days=7,
        is_mandatory=True,
        special_instruction=None,
        is_active=True,
        recurrence_type=ProgReqRecurrenceType.ANNUAL,
        last_recurrence_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        notification_days_before_deadline=90,
        effective_from_year=2020,
        effective_until_year=2030,
        months_before_deadline=3  # Create schedule 3 months before deadline
    )
    db_session.add(requirement)
    await db_session.commit()
    await db_session.refresh(requirement)
    return requirement


@pytest_asyncio.fixture
async def inactive_program_requirement(
    db_session: AsyncSession,
    sample_program: Program,
    sample_certificate_type: CertificateType
) -> ProgramRequirement:
    """Create an inactive program requirement for testing."""
    requirement = ProgramRequirement(
        id=uuid.uuid4(),
        program_id=sample_program.id,
        cert_type_id=sample_certificate_type.id,
        name="Inactive Requirement",
        target_year=2,
        deadline_date=date(2000, 6, 1),
        grace_period_days=7,
        is_mandatory=True,
        is_active=False,  # Inactive
        recurrence_type=ProgReqRecurrenceType.ANNUAL,
        notification_days_before_deadline=60,
        effective_from_year=2020,
        effective_until_year=2030,
        months_before_deadline=2
    )
    db_session.add(requirement)
    await db_session.commit()
    await db_session.refresh(requirement)
    return requirement


@pytest_asyncio.fixture
async def existing_program_requirement_schedule(
    db_session: AsyncSession,
    active_program_requirement: ProgramRequirement,
    sample_academic_year_2024: AcademicYear
) -> ProgramRequirementSchedule:
    """Create an existing program requirement schedule for testing deduplication."""
    schedule = ProgramRequirementSchedule(
        id=uuid.uuid4(),
        program_requirement_id=active_program_requirement.id,
        academic_year_id=sample_academic_year_2024.id,
        submission_deadline=datetime(2024, 3, 15, 23, 59, 59, tzinfo=timezone.utc),
        grace_period_deadline=datetime(2024, 3, 22, 23, 59, 59, tzinfo=timezone.utc),
        start_notify_at=datetime(2023, 12, 15, tzinfo=timezone.utc),
        last_notified_at=None
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule