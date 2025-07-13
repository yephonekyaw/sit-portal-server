import uuid
from sqlalchemy import select
from typing import Dict, Tuple
import logging

from app.db.models import AcademicYear, DashboardStats, Program
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


class DashboardStatsProvider:
    def __init__(self):
        self.academic_years = {}
        self.programs = {}

    async def _load_lookup_tables(self):
        """Loads AcademicYears and Programs into memory for quick lookup."""
        async with AsyncSessionLocal.begin() as db:
            # Load academic years
            academic_years_result = await db.execute(select(AcademicYear))
            academic_years = academic_years_result.scalars().all()
            self.academic_years = {ay.year_code: ay.id for ay in academic_years}

            # Load programs
            programs_result = await db.execute(select(Program))
            programs = programs_result.scalars().all()
            self.programs = {p.program_code: p.id for p in programs}

    async def create_or_update_stats(self, student_counts: Dict[Tuple[str, str], int]):
        """Updates or creates dashboard stats."""
        if not student_counts:
            return

        # Ensure lookup tables are loaded
        if not self.academic_years or not self.programs:
            await self._load_lookup_tables()

        async with AsyncSessionLocal.begin() as db:
            # Get all existing stats in one query
            existing_stats_result = await db.execute(select(DashboardStats))
            existing_stats_list = existing_stats_result.scalars().all()

            existing_stats = {}
            for stats in existing_stats_list:
                key = (stats.academic_year_id, stats.program_id)
                existing_stats[key] = stats

            # Process updates
            skipped_count = 0
            for (academic_year_code, program_code), count in student_counts.items():
                academic_year_id = self.academic_years.get(academic_year_code)
                program_id = self.programs.get(program_code)

                if not academic_year_id or not program_id:
                    skipped_count += 1
                    continue

                key = (academic_year_id, program_id)
                if key in existing_stats:
                    existing_stats[key].total_students += count
                else:
                    stats_row = DashboardStats(
                        academic_year_id=academic_year_id,
                        program_id=program_id,
                        total_students=count,
                    )
                    db.add(stats_row)

            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} entries due to invalid codes")

    async def update_count(
        self,
        academic_year_id: uuid.UUID,
        program_id: uuid.UUID,
        field: str,
        value: int,
    ):
        """Updates a specific count field in the DashboardStats table."""
        # Validate field name more robustly
        if not hasattr(DashboardStats, field):
            raise ValueError(f"Field '{field}' does not exist on DashboardStats")

        protected_fields = {"id", "academic_year_id", "program_id"}
        if field in protected_fields:
            raise ValueError(f"Cannot update protected field: {field}")

        async with AsyncSessionLocal.begin() as db:
            # Use get_or_create pattern
            stmt = select(DashboardStats).where(
                DashboardStats.academic_year_id == academic_year_id,
                DashboardStats.program_id == program_id,
            )
            result = await db.execute(stmt)
            stats_row = result.scalar_one_or_none()

            if stats_row:
                current_value = getattr(stats_row, field, 0)
                setattr(stats_row, field, current_value + value)
            else:
                stats_row = DashboardStats(
                    academic_year_id=academic_year_id,
                    program_id=program_id,
                    **{field: value},
                )
                db.add(stats_row)

    async def get_stats(self, academic_year_id: uuid.UUID, program_id: uuid.UUID):
        """Retrieves dashboard stats with optional filtering."""
        async with AsyncSessionLocal.begin() as db:
            stmt = select(DashboardStats).where(
                DashboardStats.academic_year_id == academic_year_id,
                DashboardStats.program_id == program_id,
            )
            result = await db.execute(stmt)
            return result.scalars().all()

    def clear_cache(self):
        """Clears the cached lookup tables."""
        self.academic_years.clear()
        self.programs.clear()
