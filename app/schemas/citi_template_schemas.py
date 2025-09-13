from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ValidationDecision(str, Enum):
    APPROVE = "APPROVE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REJECT = "REJECT"


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SecurityFlag(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"


class OverallScore(BaseModel):
    value: int = Field(..., ge=0, le=100)
    explanation: str


class CriticalFields(BaseModel):
    student_name: str
    record_id: str
    completion_date: str = Field(..., description="Date in YYYY-MM-DD format")
    course_title: str
    curriculum_group: str
    course_learner_group: str
    stage_information: str
    institution_name: str
    verification_url: Optional[str] = None
    expiration_date: Optional[str] = Field(
        None, description="Date in YYYY-MM-DD format or null"
    )


class SecurityChecks(BaseModel):
    tampering_evidence: SecurityFlag
    forgery_indicators: SecurityFlag
    suspicious_modifications: SecurityFlag
    formatting_anomalies: SecurityFlag
    notes: List[str] = Field(default_factory=list)


class DecisionFactors(BaseModel):
    positive_factors: List[str] = Field(default_factory=list)
    negative_factors: List[str] = Field(default_factory=list)
    neutral_factors: List[str] = Field(default_factory=list)


class FinalAssessment(BaseModel):
    decision: ValidationDecision
    anomalies_detected: List[str] = Field(default_factory=list)
    reasons_for_rejection: Optional[str] = None
    reasons_for_manual_review: Optional[str] = None
    comments: Optional[str] = None


class CitiValidationResponse(BaseModel):
    """CITI Certificate Validation Response"""

    validation_decision: ValidationDecision
    confidence_level: ConfidenceLevel
    overall_score: OverallScore
    fields_values: CriticalFields
    security_checks: SecurityChecks
    decision_factors: DecisionFactors
    final_assessment: FinalAssessment
    recommendation: Optional[str] = None
