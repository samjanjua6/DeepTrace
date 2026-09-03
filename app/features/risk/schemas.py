"""Risk schemas."""
from pydantic import BaseModel
from datetime import datetime


class RiskSignalResponse(BaseModel):
    signal_category: str
    raw_score: float
    normalized_weight: float
    weighted_score: float
    max_possible_points: int
    is_deterministic: bool
    evidence_count: int


class RiskAssessmentResponse(BaseModel):
    id: str
    investigation_id: str
    overall_score: int
    risk_tier: str
    action_directive: str
    total_evidence_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    narrative_summary: str | None
    risk_signals: list[RiskSignalResponse] = []
    computed_at: datetime
    overridden_score: int | None
    overridden_tier: str | None
    override_reason: str | None


class RiskOverrideRequest(BaseModel):
    score: int
    reason: str
