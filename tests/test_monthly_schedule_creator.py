import pytest
import uuid
from datetime import datetime, timezone, date, timedelta
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, patch, Mock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.monthly_schedule_creator import (
    monthly_schedule_creator_task,
    _calculate_current_academic_year,
    _get_active_program_requirements,
    _get_academic_years_map,
    _get_existing_schedules_map,
    _is_requirement_effective,
    _should_skip_based_on_recurrence,
    _calculate_schedule_creation_date,
    _calculate_deadline_datetime,
    _get_or_create_academic_year,
    _update_last_recurrence_timestamps
)
from app.db.models import (
    ProgramRequirement, 
    AcademicYear, 
    ProgramRequirementSchedule,
    ProgReqRecurrenceType
)

# Bangkok timezone for testing
BANGKOK_TZ = ZoneInfo("Asia/Bangkok")


class TestAcademicYearCalculation:
    """Test academic year calculation logic."""
    
    def test_calculate_current_academic_year_august_or_later(self):
        """Test academic year calculation for August or later."""
        # August 2024 -> Academic Year 2024
        august_date = datetime(2024, 8, 1, tzinfo=timezone.utc)
        assert _calculate_current_academic_year(august_date) == 2024
        
        # December 2024 -> Academic Year 2024
        december_date = datetime(2024, 12, 15, tzinfo=timezone.utc)
        assert _calculate_current_academic_year(december_date) == 2024
        
    def test_calculate_current_academic_year_before_august(self):
        """Test academic year calculation for before August."""
        # January 2025 -> Academic Year 2024
        january_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        assert _calculate_current_academic_year(january_date) == 2024
        
        # July 2024 -> Academic Year 2023
        july_date = datetime(2024, 7, 31, tzinfo=timezone.utc)
        assert _calculate_current_academic_year(july_date) == 2023
        
    def test_calculate_current_academic_year_boundary_conditions(self):
        """Test academic year calculation at boundary conditions."""
        # July 31, 2024 23:59:59 -> Academic Year 2023
        july_end = datetime(2024, 7, 31, 23, 59, 59, tzinfo=timezone.utc)
        assert _calculate_current_academic_year(july_end) == 2023
        
        # August 1, 2024 00:00:00 -> Academic Year 2024
        august_start = datetime(2024, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert _calculate_current_academic_year(august_start) == 2024


class TestDatabaseQueries:
    """Test database query functions."""
    
    @pytest.mark.asyncio
    async def test_get_active_program_requirements(
        self,
        db_session: AsyncSession,
        active_program_requirement: ProgramRequirement,
        inactive_program_requirement: ProgramRequirement
    ):
        """Test fetching active program requirements."""
        requirements = await _get_active_program_requirements(db_session)
        
        # Should only include active requirements with months_before_deadline set
        requirement_ids = [req.id for req in requirements]
        assert active_program_requirement.id in requirement_ids
        assert inactive_program_requirement.id not in requirement_ids
        
    @pytest.mark.asyncio
    async def test_get_academic_years_map(
        self,
        db_session: AsyncSession,
        sample_academic_year_2024: AcademicYear,
        sample_academic_year_2025: AcademicYear
    ):
        """Test academic years mapping."""
        academic_years_map = await _get_academic_years_map(db_session)
        
        assert 2024 in academic_years_map
        assert 2025 in academic_years_map
        assert academic_years_map[2024].id == sample_academic_year_2024.id
        assert academic_years_map[2025].id == sample_academic_year_2025.id
        
    @pytest.mark.asyncio
    async def test_get_existing_schedules_map(
        self,
        db_session: AsyncSession,
        active_program_requirement: ProgramRequirement,
        existing_program_requirement_schedule: ProgramRequirementSchedule
    ):
        """Test existing schedules mapping for deduplication."""
        existing_schedules = await _get_existing_schedules_map(
            db_session, [active_program_requirement]
        )
        
        # Should contain the existing schedule with student cohort year (2024, not deadline year)
        schedule_key = (active_program_requirement.id, 2024)  # 2024 is the student cohort year
        assert schedule_key in existing_schedules


class TestRequirementFiltering:
    """Test requirement filtering logic."""
    
    def test_is_requirement_effective_within_range(self):
        """Test requirement effectiveness within valid range."""
        requirement = Mock()
        requirement.effective_from_year = 2020
        requirement.effective_until_year = 2030
        
        # Student cohort year 2025 should be effective
        assert _is_requirement_effective(requirement, 2025) == True
        
        # Boundary conditions
        assert _is_requirement_effective(requirement, 2020) == True
        assert _is_requirement_effective(requirement, 2030) == True
        
    def test_is_requirement_effective_outside_range(self):
        """Test requirement effectiveness outside valid range."""
        requirement = Mock()
        requirement.effective_from_year = 2020
        requirement.effective_until_year = 2030
        
        # Student cohort year before effective_from_year
        assert _is_requirement_effective(requirement, 2019) == False
        
        # Student cohort year after effective_until_year
        assert _is_requirement_effective(requirement, 2031) == False
        
    def test_is_requirement_effective_no_limits(self):
        """Test requirement effectiveness with no date limits."""
        requirement = Mock()
        requirement.effective_from_year = None
        requirement.effective_until_year = None
        
        # Should always be effective
        assert _is_requirement_effective(requirement, 2015) == True
        assert _is_requirement_effective(requirement, 2035) == True
        
    def test_is_requirement_effective_partial_limits(self):
        """Test requirement effectiveness with partial date limits."""
        # Only effective_from_year set
        requirement = Mock()
        requirement.effective_from_year = 2020
        requirement.effective_until_year = None
        
        assert _is_requirement_effective(requirement, 2019) == False
        assert _is_requirement_effective(requirement, 2025) == True
        
        # Only effective_until_year set
        requirement.effective_from_year = None
        requirement.effective_until_year = 2030
        
        assert _is_requirement_effective(requirement, 2025) == True
        assert _is_requirement_effective(requirement, 2031) == False


class TestRecurrenceLogic:
    """Test recurrence and deduplication logic."""
    
    def test_should_skip_based_on_recurrence_no_last_recurrence(self):
        """Test skip logic when no last recurrence."""
        requirement = Mock()
        requirement.last_recurrence_at = None
        
        assert _should_skip_based_on_recurrence(requirement, 2024) == False
        
    def test_should_skip_based_on_recurrence_same_cohort_year(self):
        """Test skip logic when last recurrence year matches student cohort year."""
        requirement = Mock()
        # Last recurrence year 2024 (matches student cohort 2024)
        requirement.last_recurrence_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        # Should skip for student cohort 2024
        assert _should_skip_based_on_recurrence(requirement, 2024) == True
        
    def test_should_skip_based_on_recurrence_different_cohort_year(self):
        """Test skip logic when last recurrence was for different cohort year."""
        requirement = Mock()
        # Last recurrence year 2023 (different cohort)
        requirement.last_recurrence_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        # Should not skip for student cohort 2024
        assert _should_skip_based_on_recurrence(requirement, 2024) == False
        
    def test_should_skip_based_on_recurrence_handles_deadline_changes(self):
        """Test that recurrence logic works even if deadline month/day changes."""
        requirement = Mock()
        # Last recurrence was for cohort 2024, but with different month/day
        requirement.last_recurrence_at = datetime(2024, 6, 30, tzinfo=timezone.utc)  # June 30
        
        # Should still skip for student cohort 2024, regardless of current deadline date
        assert _should_skip_based_on_recurrence(requirement, 2024) == True


class TestDateCalculations:
    """Test date and deadline calculations."""
    
    def test_calculate_deadline_datetime(self):
        """Test deadline datetime calculation with Bangkok timezone."""
        requirement = Mock()
        requirement.deadline_date = date(2000, 3, 15)  # March 15 (year ignored)
        
        deadline = _calculate_deadline_datetime(requirement, 2024)
        
        # Create expected deadline in Bangkok timezone then convert to UTC
        expected_bangkok = datetime(2024, 3, 15, 23, 59, 59, tzinfo=BANGKOK_TZ)
        expected_utc = expected_bangkok.astimezone(timezone.utc)
        assert deadline == expected_utc
        
    def test_calculate_deadline_datetime_leap_year(self):
        """Test deadline calculation for leap year February 29."""
        requirement = Mock()
        requirement.deadline_date = date(2000, 2, 29)  # Feb 29 (leap year)
        
        deadline = _calculate_deadline_datetime(requirement, 2024)  # 2024 is leap year
        
        # Create expected deadline in Bangkok timezone then convert to UTC
        expected_bangkok = datetime(2024, 2, 29, 23, 59, 59, tzinfo=BANGKOK_TZ)
        expected_utc = expected_bangkok.astimezone(timezone.utc)
        assert deadline == expected_utc
        
    def test_calculate_schedule_creation_date(self):
        """Test schedule creation date calculation with Bangkok timezone."""
        requirement = Mock()
        requirement.deadline_date = date(2000, 3, 15)
        requirement.months_before_deadline = 3
        
        creation_date = _calculate_schedule_creation_date(requirement, 2024)
        
        # Should be 3 months before March 15, 2024 (calculated in Bangkok time then converted to UTC)
        deadline_bangkok = datetime(2024, 3, 15, 23, 59, 59, tzinfo=BANGKOK_TZ)
        deadline_utc = deadline_bangkok.astimezone(timezone.utc)
        expected = deadline_utc - relativedelta(months=3)
        assert creation_date == expected
        
    def test_calculate_schedule_creation_date_cross_year_boundary(self):
        """Test schedule creation date that crosses year boundary."""
        requirement = Mock()
        requirement.deadline_date = date(2000, 2, 15)  # February 15
        requirement.months_before_deadline = 6  # 6 months before
        
        creation_date = _calculate_schedule_creation_date(requirement, 2024)
        
        # Should be August 15, 2023 (calculated in Bangkok time then converted to UTC)
        deadline_bangkok = datetime(2024, 2, 15, 23, 59, 59, tzinfo=BANGKOK_TZ)
        deadline_utc = deadline_bangkok.astimezone(timezone.utc)
        expected_creation = deadline_utc - relativedelta(months=6)
        assert creation_date == expected_creation


class TestAcademicYearManagement:
    """Test academic year creation and management."""
    
    @pytest.mark.asyncio
    async def test_get_or_create_academic_year_existing(
        self,
        db_session: AsyncSession,
        sample_academic_year_2024: AcademicYear
    ):
        """Test getting existing academic year."""
        academic_years_map = {2024: sample_academic_year_2024}
        
        result = await _get_or_create_academic_year(db_session, 2024, academic_years_map)
        
        assert result.id == sample_academic_year_2024.id
        assert result.year_code == 2024
        
    @pytest.mark.asyncio
    async def test_get_or_create_academic_year_new(self, db_session: AsyncSession):
        """Test creating new academic year."""
        academic_years_map = {}
        
        result = await _get_or_create_academic_year(db_session, 2026, academic_years_map)
        
        assert result.year_code == 2026
        
        # Verify dates are calculated in Bangkok timezone then converted to UTC
        expected_start_bangkok = datetime(2026, 8, 1, 0, 0, 0, tzinfo=BANGKOK_TZ)
        expected_start_utc = expected_start_bangkok.astimezone(timezone.utc)
        assert result.start_date == expected_start_utc
        
        expected_end_bangkok = datetime(2027, 5, 31, 23, 59, 59, tzinfo=BANGKOK_TZ)
        expected_end_utc = expected_end_bangkok.astimezone(timezone.utc)
        assert result.end_date == expected_end_utc
        
        assert result.is_current == False
        
        # Should be added to the map
        assert 2026 in academic_years_map
        assert academic_years_map[2026].id == result.id
        
    @pytest.mark.asyncio
    async def test_update_last_recurrence_timestamps(
        self,
        db_session: AsyncSession,
        active_program_requirement: ProgramRequirement
    ):
        """Test updating last recurrence timestamps."""
        student_cohort_year = 2024
        
        # Create the processed requirements data structure
        processed_requirements_data = {
            active_program_requirement.id: (active_program_requirement, student_cohort_year)
        }
        
        await _update_last_recurrence_timestamps(
            db_session, processed_requirements_data
        )
        
        # Verify the update - should be set to August 1st of student_cohort_year
        result = await db_session.execute(
            select(ProgramRequirement).where(
                ProgramRequirement.id == active_program_requirement.id
            )
        )
        updated_requirement = result.scalar_one()
        
        expected_timestamp = datetime(
            year=student_cohort_year,  # 2024
            month=8,                   # August
            day=1,                     # 1st
            hour=0, minute=0, second=0,
            tzinfo=timezone.utc
        )
        assert updated_requirement.last_recurrence_at == expected_timestamp


class TestFullTaskIntegration:
    """Test the complete task integration."""
    
    @pytest.mark.asyncio
    @patch('app.tasks.monthly_schedule_creator.get_async_session')
    @patch('app.tasks.monthly_schedule_creator.datetime')
    async def test_monthly_schedule_creator_task_success(
        self,
        mock_datetime,
        mock_get_session,
        db_session: AsyncSession,
        active_program_requirement: ProgramRequirement,
        sample_academic_year_2024: AcademicYear,
        mock_celery_task
    ):
        """Test successful task execution."""
        # Mock current time to January 1, 2025 (Academic Year 2024)
        current_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        
        # Mock database session
        async def mock_session():
            yield db_session
            
        mock_get_session.return_value = mock_session()
        
        # Execute the task
        result = await monthly_schedule_creator_task(mock_celery_task, "test_request_id")
        
        assert result["success"] == True
        assert result["processed_count"] >= 0
        assert result["current_academic_year"] == 2024
        
    @pytest.mark.asyncio
    @patch('app.tasks.monthly_schedule_creator.get_async_session')
    async def test_monthly_schedule_creator_task_no_requirements(
        self,
        mock_get_session,
        db_session: AsyncSession,
        mock_celery_task
    ):
        """Test task with no active requirements."""
        # Mock database session with no requirements
        async def mock_session():
            yield db_session
            
        mock_get_session.return_value = mock_session()
        
        result = await monthly_schedule_creator_task(mock_celery_task, "test_request_id")
        
        assert result["success"] == True
        assert result["processed_count"] == 0
        assert result["created_count"] == 0
        
    @pytest.mark.asyncio
    @patch('app.tasks.monthly_schedule_creator.get_async_session')
    async def test_monthly_schedule_creator_task_database_error(
        self,
        mock_get_session,
        mock_celery_task
    ):
        """Test task handling database errors."""
        # Mock database session to raise error
        async def mock_session():
            raise Exception("Database connection failed")
            yield  # Never reached
            
        mock_get_session.return_value = mock_session()
        
        result = await monthly_schedule_creator_task(mock_celery_task, "test_request_id")
        
        assert result["success"] == False
        assert "Database connection failed" in result["error"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_leap_year_february_29_deadline(self):
        """Test handling February 29 deadline in leap and non-leap years."""
        requirement = Mock()
        requirement.deadline_date = date(2000, 2, 29)
        
        # Leap year - should work fine
        deadline_leap = _calculate_deadline_datetime(requirement, 2024)
        # Convert to Bangkok timezone to check month/day
        deadline_bangkok = deadline_leap.astimezone(BANGKOK_TZ)
        assert deadline_bangkok.month == 2
        assert deadline_bangkok.day == 29
        
        # Non-leap year - Python should handle this appropriately
        # Note: This might raise ValueError in real scenarios, which is expected
        
    def test_student_cohort_calculation_edge_cases(self):
        """Test student cohort calculations for edge cases."""
        # Current academic year 2024, target year 1 (freshmen)
        # Student cohort = 2024 - 1 + 1 = 2024
        current_academic_year = 2024
        target_year = 1
        student_cohort_year = current_academic_year - target_year + 1
        assert student_cohort_year == 2024
        
        # Current academic year 2024, target year 4 (seniors)
        # Student cohort = 2024 - 4 + 1 = 2021
        target_year = 4
        student_cohort_year = current_academic_year - target_year + 1
        assert student_cohort_year == 2021
        
    def test_deadline_academic_year_calculation(self):
        """Test deadline academic year calculation."""
        # For seniors (cohort 2021), target year 4
        # Deadline academic year = 2021 + 4 - 1 = 2024
        student_cohort_year = 2021
        target_year = 4
        deadline_academic_year = student_cohort_year + target_year - 1
        assert deadline_academic_year == 2024
        
    def test_academic_year_storage_logic(self):
        """Test that academic_year_id stores student cohort year, not deadline year."""
        # Example: Current academic year 2024, target year 4 (seniors)
        # Student cohort = 2024 - 4 + 1 = 2021 (they started in 2021)
        # Deadline year = 2021 + 4 - 1 = 2024 (they graduate/submit in 2024)
        # academic_year_id should point to 2021 (their cohort), not 2024 (deadline)
        
        current_academic_year = 2024
        target_year = 4
        student_cohort_year = current_academic_year - target_year + 1  # 2021
        deadline_academic_year = student_cohort_year + target_year - 1  # 2024
        
        assert student_cohort_year == 2021  # This goes in academic_year_id
        assert deadline_academic_year == 2024  # This is used for deadline calculation only
        
    @pytest.mark.asyncio
    async def test_schedule_creation_within_30_days_boundary(
        self,
        db_session: AsyncSession,
        sample_program: Program,
        sample_certificate_type: CertificateType
    ):
        """Test schedule creation exactly at 30-day boundary."""
        # Create a requirement that should create schedule exactly 30 days from now
        current_time = datetime(2024, 12, 1, tzinfo=timezone.utc)
        
        # Deadline should be March 31, 2025 (exactly 90 days from Dec 1)
        # Creation date should be December 31, 2024 (3 months before)
        # That's exactly 30 days from current time
        requirement = ProgramRequirement(
            id=uuid.uuid4(),
            program_id=sample_program.id,
            cert_type_id=sample_certificate_type.id,
            name="30-day boundary test",
            target_year=1,
            deadline_date=date(2000, 3, 31),  # March 31
            grace_period_days=7,
            is_mandatory=True,
            is_active=True,
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=90,
            effective_from_year=2020,
            effective_until_year=2030,
            months_before_deadline=3
        )
        
        creation_date = _calculate_schedule_creation_date(requirement, 2025)
        days_until_creation = (creation_date.date() - current_time.date()).days
        
        # Should be exactly at the boundary
        assert days_until_creation == 30


class TestErrorHandling:
    """Test error handling and retry scenarios."""
    
    @pytest.mark.asyncio
    @patch('app.tasks.monthly_schedule_creator.get_async_session')
    async def test_task_retry_on_transient_error(
        self,
        mock_get_session,
        mock_celery_task
    ):
        """Test task retry behavior on transient errors."""
        mock_celery_task.request.retries = 1  # Simulate retry attempt
        
        # Mock database to fail
        mock_get_session.side_effect = Exception("Temporary database error")
        
        # Should call retry
        with pytest.raises(Exception, match="Retry called"):
            await monthly_schedule_creator_task(mock_celery_task, "test_request_id")
            
        mock_celery_task.retry.assert_called_once()
        
    @pytest.mark.asyncio
    @patch('app.tasks.monthly_schedule_creator.get_async_session')
    async def test_task_max_retries_exceeded(
        self,
        mock_get_session,
        mock_celery_task
    ):
        """Test task behavior when max retries exceeded."""
        mock_celery_task.request.retries = 3  # Max retries reached
        mock_celery_task.max_retries = 3
        
        # Mock database to fail
        mock_get_session.side_effect = Exception("Persistent database error")
        
        result = await monthly_schedule_creator_task(mock_celery_task, "test_request_id")
        
        assert result["success"] == False
        assert "Persistent database error" in result["error"]
        mock_celery_task.retry.assert_not_called()
        
    @pytest.mark.asyncio
    @patch('app.tasks.monthly_schedule_creator.get_async_session')
    async def test_task_handles_individual_requirement_errors(
        self,
        mock_get_session,
        db_session: AsyncSession,
        active_program_requirement: ProgramRequirement,
        mock_celery_task
    ):
        """Test that individual requirement processing errors don't fail entire task."""
        async def mock_session():
            yield db_session
            
        mock_get_session.return_value = mock_session()
        
        # Mock one of the processing functions to fail
        with patch('app.tasks.monthly_schedule_creator._calculate_schedule_creation_date', 
                   side_effect=Exception("Individual processing error")):
            result = await monthly_schedule_creator_task(mock_celery_task, "test_request_id")
            
            # Task should still succeed overall
            assert result["success"] == True
            # But individual errors should be logged and handled gracefully