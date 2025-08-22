import pytest
import uuid
from datetime import datetime, timezone, date
from unittest.mock import patch, Mock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.annual_requirement_archiver import (
    annual_requirement_archiver_task,
    _calculate_current_academic_year,
    _get_expired_requirements,
    _archive_expired_requirements,
)
from app.db.models import (
    ProgramRequirement,
    ProgReqRecurrenceType
)


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


class TestExpiredRequirementsQuery:
    """Test finding expired requirements."""
    
    @pytest.mark.asyncio
    async def test_get_expired_requirements_with_expired(
        self,
        db_session: AsyncSession,
        sample_program,
        sample_certificate_type
    ):
        """Test finding requirements that have expired."""
        # Create expired requirement (effective_until_year = 2020, current = 2024)
        expired_requirement = ProgramRequirement(
            id=uuid.uuid4(),
            program_id=sample_program.id,
            cert_type_id=sample_certificate_type.id,
            name="Expired Requirement",
            target_year=2,
            deadline_date=date(2000, 6, 1),
            grace_period_days=7,
            is_mandatory=True,
            is_active=True,  # Still active, should be archived
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=60,
            effective_from_year=2015,
            effective_until_year=2020,  # Expired
            months_before_deadline=2
        )
        db_session.add(expired_requirement)
        await db_session.commit()
        
        # Test with current academic year 2024
        expired_requirements = await _get_expired_requirements(db_session, 2024)
        
        # Should find the expired requirement
        assert len(expired_requirements) == 1
        assert expired_requirements[0].id == expired_requirement.id
        assert expired_requirements[0].effective_until_year == 2020
        
    @pytest.mark.asyncio
    async def test_get_expired_requirements_no_expired(
        self,
        db_session: AsyncSession,
        sample_program,
        sample_certificate_type
    ):
        """Test when no requirements have expired."""
        # Create current requirement (effective_until_year = 2030, current = 2024)
        current_requirement = ProgramRequirement(
            id=uuid.uuid4(),
            program_id=sample_program.id,
            cert_type_id=sample_certificate_type.id,
            name="Current Requirement",
            target_year=3,
            deadline_date=date(2000, 5, 15),
            grace_period_days=7,
            is_mandatory=True,
            is_active=True,
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=90,
            effective_from_year=2020,
            effective_until_year=2030,  # Still valid
            months_before_deadline=3
        )
        db_session.add(current_requirement)
        await db_session.commit()
        
        # Test with current academic year 2024
        expired_requirements = await _get_expired_requirements(db_session, 2024)
        
        # Should find no expired requirements
        assert len(expired_requirements) == 0
        
    @pytest.mark.asyncio
    async def test_get_expired_requirements_ignores_inactive(
        self,
        db_session: AsyncSession,
        sample_program,
        sample_certificate_type
    ):
        """Test that inactive requirements are ignored."""
        # Create expired but inactive requirement
        inactive_expired_requirement = ProgramRequirement(
            id=uuid.uuid4(),
            program_id=sample_program.id,
            cert_type_id=sample_certificate_type.id,
            name="Inactive Expired Requirement",
            target_year=1,
            deadline_date=date(2000, 4, 1),
            grace_period_days=7,
            is_mandatory=True,
            is_active=False,  # Already inactive
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=30,
            effective_from_year=2015,
            effective_until_year=2020,  # Expired
            months_before_deadline=1
        )
        db_session.add(inactive_expired_requirement)
        await db_session.commit()
        
        # Test with current academic year 2024
        expired_requirements = await _get_expired_requirements(db_session, 2024)
        
        # Should find no requirements (inactive is ignored)
        assert len(expired_requirements) == 0
        
    @pytest.mark.asyncio
    async def test_get_expired_requirements_ignores_no_until_year(
        self,
        db_session: AsyncSession,
        sample_program,
        sample_certificate_type
    ):
        """Test that requirements with no effective_until_year are ignored."""
        # Create requirement with no effective_until_year
        no_until_requirement = ProgramRequirement(
            id=uuid.uuid4(),
            program_id=sample_program.id,
            cert_type_id=sample_certificate_type.id,
            name="No Until Year Requirement",
            target_year=4,
            deadline_date=date(2000, 3, 15),
            grace_period_days=7,
            is_mandatory=True,
            is_active=True,
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=90,
            effective_from_year=2020,
            effective_until_year=None,  # No end date
            months_before_deadline=6
        )
        db_session.add(no_until_requirement)
        await db_session.commit()
        
        # Test with current academic year 2024
        expired_requirements = await _get_expired_requirements(db_session, 2024)
        
        # Should find no requirements (no until year means never expires)
        assert len(expired_requirements) == 0


class TestArchiveRequirements:
    """Test archiving expired requirements."""
    
    @pytest.mark.asyncio
    async def test_archive_expired_requirements_success(
        self,
        db_session: AsyncSession,
        sample_program,
        sample_certificate_type
    ):
        """Test successfully archiving expired requirements."""
        # Create multiple expired requirements
        expired_req_1 = ProgramRequirement(
            id=uuid.uuid4(),
            program_id=sample_program.id,
            cert_type_id=sample_certificate_type.id,
            name="Expired Requirement 1",
            target_year=1,
            deadline_date=date(2000, 6, 1),
            grace_period_days=7,
            is_mandatory=True,
            is_active=True,
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=60,
            effective_from_year=2015,
            effective_until_year=2020,
            months_before_deadline=2
        )
        
        expired_req_2 = ProgramRequirement(
            id=uuid.uuid4(),
            program_id=sample_program.id,
            cert_type_id=sample_certificate_type.id,
            name="Expired Requirement 2",
            target_year=2,
            deadline_date=date(2000, 7, 15),
            grace_period_days=14,
            is_mandatory=False,
            is_active=True,
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=45,
            effective_from_year=2018,
            effective_until_year=2021,
            months_before_deadline=3
        )
        
        db_session.add_all([expired_req_1, expired_req_2])
        await db_session.commit()
        
        # Archive the requirements
        archived_count = await _archive_expired_requirements(
            db_session, [expired_req_1, expired_req_2]
        )
        
        # Verify the count
        assert archived_count == 2
        
        # Verify requirements are now inactive
        result_1 = await db_session.get(ProgramRequirement, expired_req_1.id)
        result_2 = await db_session.get(ProgramRequirement, expired_req_2.id)
        
        assert result_1.is_active == False
        assert result_2.is_active == False
        
    @pytest.mark.asyncio
    async def test_archive_expired_requirements_empty_list(self, db_session: AsyncSession):
        """Test archiving with empty list."""
        archived_count = await _archive_expired_requirements(db_session, [])
        assert archived_count == 0


class TestFullTaskIntegration:
    """Test the complete task integration."""
    
    @pytest.mark.asyncio
    @patch('app.tasks.annual_requirement_archiver.get_async_session')
    @patch('app.tasks.annual_requirement_archiver.datetime')
    async def test_annual_requirement_archiver_task_success(
        self,
        mock_datetime,
        mock_get_session,
        db_session: AsyncSession,
        sample_program,
        sample_certificate_type,
        mock_celery_task
    ):
        """Test successful task execution with expired requirements."""
        # Mock current time to August 15, 2024 (Academic Year 2024)
        current_time = datetime(2024, 8, 15, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        
        # Mock database session
        async def mock_session():
            yield db_session
            
        mock_get_session.return_value = mock_session()
        
        # Create expired requirement
        expired_requirement = ProgramRequirement(
            id=uuid.uuid4(),
            program_id=sample_program.id,
            cert_type_id=sample_certificate_type.id,
            name="Test Expired Requirement",
            target_year=3,
            deadline_date=date(2000, 5, 1),
            grace_period_days=7,
            is_mandatory=True,
            is_active=True,
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=60,
            effective_from_year=2018,
            effective_until_year=2022,  # Expired (2022 < 2024)
            months_before_deadline=2
        )
        db_session.add(expired_requirement)
        await db_session.commit()
        
        # Execute the task
        result = await annual_requirement_archiver_task(mock_celery_task, "test_request_id")
        
        assert result["success"] == True
        assert result["archived_count"] == 1
        assert result["current_academic_year"] == 2024
        
        # Verify requirement was archived
        updated_requirement = await db_session.get(ProgramRequirement, expired_requirement.id)
        assert updated_requirement.is_active == False
        
    @pytest.mark.asyncio
    @patch('app.tasks.annual_requirement_archiver.get_async_session')
    @patch('app.tasks.annual_requirement_archiver.datetime')
    async def test_annual_requirement_archiver_task_no_expired(
        self,
        mock_datetime,
        mock_get_session,
        db_session: AsyncSession,
        mock_celery_task
    ):
        """Test task with no expired requirements."""
        # Mock current time to August 15, 2024
        current_time = datetime(2024, 8, 15, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        
        # Mock database session
        async def mock_session():
            yield db_session
            
        mock_get_session.return_value = mock_session()
        
        result = await annual_requirement_archiver_task(mock_celery_task, "test_request_id")
        
        assert result["success"] == True
        assert result["archived_count"] == 0
        assert result["current_academic_year"] == 2024
        
    @pytest.mark.asyncio
    @patch('app.tasks.annual_requirement_archiver.get_async_session')
    async def test_annual_requirement_archiver_task_database_error(
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
        
        result = await annual_requirement_archiver_task(mock_celery_task, "test_request_id")
        
        assert result["success"] == False
        assert "Database connection failed" in result["error"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_boundary_academic_year_exactly_equal(
        self,
        db_session: AsyncSession,
        sample_program,
        sample_certificate_type
    ):
        """Test requirement where effective_until_year equals current academic year."""
        # Create requirement where effective_until_year = current academic year
        boundary_requirement = ProgramRequirement(
            id=uuid.uuid4(),
            program_id=sample_program.id,
            cert_type_id=sample_certificate_type.id,
            name="Boundary Requirement",
            target_year=2,
            deadline_date=date(2000, 6, 1),
            grace_period_days=7,
            is_mandatory=True,
            is_active=True,
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=60,
            effective_from_year=2020,
            effective_until_year=2024,  # Equals current year (2024)
            months_before_deadline=2
        )
        db_session.add(boundary_requirement)
        await db_session.commit()
        
        # Test with current academic year 2024
        expired_requirements = await _get_expired_requirements(db_session, 2024)
        
        # Should NOT be considered expired (effective_until_year = current year is still valid)
        assert len(expired_requirements) == 0
        
    def test_academic_year_calculation_edge_cases(self):
        """Test academic year calculation at exact boundaries."""
        # July 31, 2024 23:59:59 -> Academic Year 2023
        july_end = datetime(2024, 7, 31, 23, 59, 59, tzinfo=timezone.utc)
        assert _calculate_current_academic_year(july_end) == 2023
        
        # August 1, 2024 00:00:00 -> Academic Year 2024
        august_start = datetime(2024, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert _calculate_current_academic_year(august_start) == 2024
        
    @pytest.mark.asyncio
    async def test_multiple_years_expired(
        self,
        db_session: AsyncSession,
        sample_program,
        sample_certificate_type
    ):
        """Test requirements expired by multiple years."""
        # Create requirement expired by many years
        very_old_requirement = ProgramRequirement(
            id=uuid.uuid4(),
            program_id=sample_program.id,
            cert_type_id=sample_certificate_type.id,
            name="Very Old Requirement",
            target_year=1,
            deadline_date=date(2000, 4, 1),
            grace_period_days=7,
            is_mandatory=True,
            is_active=True,
            recurrence_type=ProgReqRecurrenceType.ANNUAL,
            notification_days_before_deadline=30,
            effective_from_year=2010,
            effective_until_year=2015,  # Expired by 9 years (2015 < 2024)
            months_before_deadline=1
        )
        db_session.add(very_old_requirement)
        await db_session.commit()
        
        # Test with current academic year 2024
        expired_requirements = await _get_expired_requirements(db_session, 2024)
        
        # Should still find it (any requirement where until_year < current_year)
        assert len(expired_requirements) == 1
        assert expired_requirements[0].effective_until_year == 2015


class TestErrorHandling:
    """Test error handling and retry scenarios."""
    
    @pytest.mark.asyncio
    @patch('app.tasks.annual_requirement_archiver.get_async_session')
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
            await annual_requirement_archiver_task(mock_celery_task, "test_request_id")
            
        mock_celery_task.retry.assert_called_once()
        
    @pytest.mark.asyncio
    @patch('app.tasks.annual_requirement_archiver.get_async_session')
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
        
        result = await annual_requirement_archiver_task(mock_celery_task, "test_request_id")
        
        assert result["success"] == False
        assert "Persistent database error" in result["error"]
        mock_celery_task.retry.assert_not_called()