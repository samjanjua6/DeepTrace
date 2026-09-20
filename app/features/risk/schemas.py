"""Risk schemas with Pydantic v2 AliasChoices for Prisma models."""
from datetime import datetime
from typing import Any
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator



RECOMMENDATION_MAP = {
    "IMMEDIATE_REJECTION": "Recommend: Reject / Escalate to Fraud Unit",
    "MANDATORY_STR_AND_ACCOUNT_FREEZE": "Recommend: Mandatory STR Escalation & Freeze Review",
    "ENHANCED_TRANSACTION_MONITORING": "Recommend: Enhanced Due Diligence / Compliance Review",
    "ESCALATION_REQUIRED": "Recommend: Escalate to Senior Underwriter",
    "HUMAN_REVIEW": "Recommend: Human Review & Operational Verification",
    "SECONDARY_SCAN": "Recommend: Secondary Branch / Counterfoil Verification",
    "STRAIGHT_THROUGH_APPROVAL": "Recommend: Straight-Through Approval (Standard Underwriting)",
    "MANUAL_SUPERVISOR_REVIEW": "Recommend: Human Review & Operational Verification",
    "ENHANCED_DUE_DILIGENCE": "Recommend: Enhanced Due Diligence / Compliance Review",
}


def format_recommendation(action_directive: str | None, tier: str | None = None) -> str:
    """Transform an internal action directive or tier into a human-centered advisory recommendation."""
    if not action_directive:
        return "Recommend: Operational Verification"
    norm = action_directive.strip().upper()
    if norm in RECOMMENDATION_MAP:
        return RECOMMENDATION_MAP[norm]
    if "REJECT" in norm:
        return "Recommend: Reject / Escalate to Fraud Unit"
    if "FREEZE" in norm or "STR" in norm:
        return "Recommend: Mandatory STR Escalation & Freeze Review"
    if "MONITOR" in norm or "EDD" in norm:
        return "Recommend: Enhanced Due Diligence / Compliance Review"
    if "APPROV" in norm or "STRAIGHT" in norm:
        return "Recommend: Straight-Through Processing (Standard Underwriting)"
    cleaned = norm.replace("_", " ").title()
    return f"Recommend: {cleaned}"


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
    recommended_action: str = Field(default="Recommend: Operational Verification", validation_alias=AliasChoices("recommended_action", "recommendedAction"))
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
    overridden_by_id: str | None = Field(default=None, validation_alias=AliasChoices("overridden_by_id", "overriddenById"))
    overridden_at: datetime | None = Field(default=None, validation_alias=AliasChoices("overridden_at", "overriddenAt"))
    fusion_parameters: dict | None = Field(default=None, validation_alias=AliasChoices("fusion_parameters", "fusionParameters"))

    # Decoupled Dual Forensics Scores
    authenticity_score: int = Field(default=100, validation_alias=AliasChoices("authenticity_score", "authenticityScore"))
    tamper_score: int = Field(default=0, validation_alias=AliasChoices("tamper_score", "tamperScore"))
    authenticity_tier: str = Field(default="VERIFIED_AUTHENTIC", validation_alias=AliasChoices("authenticity_tier", "authenticityTier"))
    transaction_risk_score: int = Field(default=0, validation_alias=AliasChoices("transaction_risk_score", "transactionRiskScore"))
    transaction_risk_tier: str = Field(default="CLEAN", validation_alias=AliasChoices("transaction_risk_tier", "transactionRiskTier"))

    @classmethod
    def _extract_fusion_data(cls, fp: Any, overall: int) -> dict:
        if hasattr(fp, "data"):
            fp = fp.data
        elif hasattr(fp, "to_dict"):
            fp = fp.to_dict()
        if not isinstance(fp, dict):
            fp = {}
        da = fp.get("document_authenticity") or {}
        tr = fp.get("transaction_risk") or {}

        tamper = da.get("tamper_score", overall)
        auth = da.get("score", max(0, 100 - tamper))
        auth_tier = da.get(
            "tier",
            "VERIFIED_AUTHENTIC" if tamper <= 10 else ("SUSPECT_DOCUMENT" if tamper <= 40 else "FORGERY_DETECTED"),
        )
        txn_score = tr.get("score", 0)
        txn_tier = tr.get(
            "tier",
            "CRITICAL_PROSCRIBED" if txn_score >= 75 else ("HIGH_AML_RISK" if txn_score >= 45 else ("MONITORED" if txn_score >= 20 else "CLEAN")),
        )
        return {
            "authenticity_score": auth,
            "tamper_score": tamper,
            "authenticity_tier": auth_tier,
            "transaction_risk_score": txn_score,
            "transaction_risk_tier": txn_tier,
        }

    @model_validator(mode="before")
    @classmethod
    def extract_subscores(cls, data: Any) -> Any:
        if isinstance(data, dict):
            fp = data.get("fusionParameters") or data.get("fusion_parameters") or {}
            overall = data.get("overall_score") or data.get("overallScore") or 0
            extracted = cls._extract_fusion_data(fp, overall)
            for k, v in extracted.items():
                data.setdefault(k, v)

            directive = data.get("action_directive") or data.get("actionDirective")
            tier = data.get("overridden_tier") or data.get("overriddenTier") or data.get("risk_tier") or data.get("riskTier")
            data.setdefault("recommended_action", format_recommendation(directive, tier))
            return data

        fp = getattr(data, "fusionParameters", None) or getattr(data, "fusion_parameters", None) or {}
        overall = getattr(data, "overallScore", getattr(data, "overall_score", 0))
        extracted = cls._extract_fusion_data(fp, overall)
        directive = getattr(data, "actionDirective", getattr(data, "action_directive", None))
        tier = getattr(data, "overriddenTier", getattr(data, "overridden_tier", getattr(data, "riskTier", getattr(data, "risk_tier", None))))
        rec = format_recommendation(directive, str(tier) if tier else None)

        if hasattr(data, "__dict__"):
            for k, v in extracted.items():
                data.__dict__[k] = v
            data.__dict__.setdefault("recommended_action", rec)
        return data


class RiskOverrideRequest(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Overridden risk score between 0 and 100")
    reason: str = Field(..., min_length=10, max_length=1000, description="Mandatory audit justification under SBP guidelines")


