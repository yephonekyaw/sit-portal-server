from datetime import datetime

from app.schemas.camel_base_model import CamelCaseBaseModel as BaseModel


class DashboardStatsResponse(BaseModel):
    """Response schema for dashboard statistics."""

    id: str
    requirement_schedule_id: str
    program_id: str
    academic_year_id: str
    cert_type_id: str
    total_submissions_required: int
    submitted_count: int
    approved_count: int
    rejected_count: int
    pending_count: int
    manual_review_count: int
    not_submitted_count: int
    on_time_submissions: int
    late_submissions: int
    overdue_count: int
    manual_verification_count: int
    agent_verification_count: int
    last_calculated_at: datetime
    created_at: datetime
    updated_at: datetime
