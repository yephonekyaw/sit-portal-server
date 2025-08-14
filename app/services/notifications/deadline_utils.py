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
    def calculate_days_overdue(deadline_date: Optional[date]) -> int:
        """Calculate days overdue past deadline"""
        if not deadline_date:
            return 0
        
        now = datetime.now().date()
        diff = (deadline_date - now).days
        return abs(min(0, diff))
    
    @staticmethod
    def is_deadline_passed(deadline_date: Optional[date]) -> bool:
        """Check if deadline has passed"""
        if not deadline_date:
            return False
        
        return datetime.now().date() > deadline_date
    
    @staticmethod
    def get_deadline_status(deadline_date: Optional[date]) -> str:
        """Get human-readable deadline status"""
        if not deadline_date:
            return "No deadline set"
        
        if DeadlineCalculator.is_deadline_passed(deadline_date):
            days_overdue = DeadlineCalculator.calculate_days_overdue(deadline_date)
            if days_overdue == 1:
                return "Overdue by 1 day"
            else:
                return f"Overdue by {days_overdue} days"
        else:
            days_remaining = DeadlineCalculator.calculate_days_remaining(deadline_date)
            if days_remaining == 0:
                return "Due today"
            elif days_remaining == 1:
                return "Due tomorrow"
            else:
                return f"{days_remaining} days remaining"