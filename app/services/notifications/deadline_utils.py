from typing import Optional
from datetime import datetime, date


class DeadlineCalculator:
    """Utility class for deadline-related calculations"""

    @staticmethod
    def calculate_days_remaining(deadline_date: Optional[date]) -> int:
        """Calculate days remaining until deadline"""
        if not deadline_date:
            return 0

        now = datetime.now().date()
        diff = (deadline_date - now).days
        return max(0, diff)

    @staticmethod
    def calculate_days_late(deadline_date: Optional[date]) -> int:
        """Calculate days late past deadline and in grace period"""
        if not deadline_date:
            return 0

        now = datetime.now().date()
        diff = (now - deadline_date).days
        return max(0, diff)

    @staticmethod
    def calculate_days_overdue(grace_period_date: Optional[date]) -> int:
        """Calculate days overdue past grace period"""
        if not grace_period_date:
            return 0

        now = datetime.now().date()
        diff = (now - grace_period_date).days
        return max(0, diff)  # Return positive number of days overdue

    @staticmethod
    def is_deadline_passed(deadline_date: Optional[date]) -> bool:
        """Check if deadline has passed"""
        if not deadline_date:
            return False

        return datetime.now().date() > deadline_date
