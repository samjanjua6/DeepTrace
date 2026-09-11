"""
Risk service — evidence fusion and tier classification.
"""
from datetime import datetime, timezone
from typing import Any

from prisma import Json
from app.db.client import db, set_org_context
from app.features.pipeline.tasks.stage_7_fusion import compute_risk_tier


async def get_risk_assessment(org_id: str, investigation_id: str) -> Any:
    """Fetch the computed RiskAssessment with all RiskSignal breakdowns."""
    async with set_org_context(org_id) as tx:
        return await tx.riskassessment.find_unique(
            where={"investigationId": investigation_id},
            include={"riskSignals": True},
        )


async def override_risk_score(
    org_id: str,
    investigation_id: str,
    score: int,
    overriding_user_id: str,
    reason: str,
) -> Any:
    """Allow an analyst to manually override the computed risk score."""
    if not (0 <= score <= 100):
        raise ValueError("Risk score must be between 0 and 100")

    tier, _ = compute_risk_tier(score)

    async with set_org_context(org_id) as tx:
        assessment = await tx.riskassessment.find_unique(
            where={"investigationId": investigation_id}
        )
        if not assessment:
            raise ValueError(f"No risk assessment exists for investigation '{investigation_id}'")

        updated = await tx.riskassessment.update(
            where={"id": assessment.id},
            data={
                "overriddenById": overriding_user_id,
                "overriddenScore": score,
                "overriddenTier": tier,
                "overrideReason": reason,
                "overriddenAt": datetime.now(timezone.utc),
            },
            include={"riskSignals": True},
        )

        # Audit log for human override
        audit_data: dict[str, Any] = {
            "organization": {"connect": {"id": org_id}},
            "action": "RISK_SCORE_OVERRIDDEN",
            "entityType": "RISK_ASSESSMENT",
            "entityId": assessment.id,
            "metadata": Json({
                "original_score": assessment.overallScore,
                "overridden_score": score,
                "reason": reason,
            }),
        }
        if overriding_user_id:
            audit_data["user"] = {"connect": {"id": overriding_user_id}}

        await tx.auditlog.create(data=audit_data)

        return updated
