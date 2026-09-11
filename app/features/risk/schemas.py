"""Risk schemas with Pydantic v2 AliasChoices for Prisma models."""
from datetime import datetime
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class RiskSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    signal_category: str = Field(validation_alias=AliasChoices("signal_category", "signalCategory"))
    raw_score: float = Field(validation_alias=AliasChoices("raw_score", "rawScore"))
    normalized_weight: float = Field(validation_alias=AliasChoices("normalized_weight", "normalizedWeight"))
    weighted_score: float = Field(validation_alias=AliasChoices("weighted_score", "weightedScore"))
    max_possible_points: int = Field(validation_alias=AliasChoices("max_possible_points", "maxPossiblePoints"))
    is_deterministic: bool = Field(validation_alias=AliasChoices("is_deterministic", "isDeterministic"))
    evidence_count: int = Field(validation_alias=AliasChoices("evidence_count", "evidenceCount"))


class RiskAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    investigation_id: str = Field(validation_alias=AliasChoices("investigation_id", "investigationId"))
    overall_score: int = Field(validation_alias=AliasChoices("overall_score", "overallScore"))
    risk_tier: str = Field(validation_alias=AliasChoices("risk_tier", "riskTier"))
    action_directive: str = Field(validation_alias=AliasChoices("action_directive", "actionDirective"))
    total_evidence_count: int = Field(validation_alias=AliasChoices("total_evidence_count", "totalEvidenceCount"))
    critical_count: int = Field(validation_alias=AliasChoices("critical_count", "criticalCount"))
    high_count: int = Field(validation_alias=AliasChoices("high_count", "highCount"))
    medium_count: int = Field(validation_alias=AliasChoices("medium_count", "mediumCount"))
    low_count: int = Field(validation_alias=AliasChoices("low_count", "lowCount"))
    narrative_summary: str | None = Field(default=None, validation_alias=AliasChoices("narrative_summary", "narrativeSummary"))
    risk_signals: list[RiskSignalResponse] = Field(default=[], validation_alias=AliasChoices("risk_signals", "riskSignals"))
    computed_at: datetime = Field(validation_alias=AliasChoices("computed_at", "computedAt"))
    overridden_score: int | None = Field(default=None, validation_alias=AliasChoices("overridden_score", "overriddenScore"))
    overridden_tier: str | None = Field(default=None, validation_alias=AliasChoices("overridden_tier", "overriddenTier"))
    override_reason: str | None = Field(default=None, validation_alias=AliasChoices("override_reason", "overrideReason"))


class RiskOverrideRequest(BaseModel):
    score: int
    reason: str
