"""
Risk service — evidence fusion and tier classification.
"""
from datetime import datetime, timezone
from typing import Any

from prisma import Json
from app.db.client import db, set_org_context
from app.features.pipeline.tasks.stage_7_fusion import compute_risk_tier
from app.features.risk.schemas import format_recommendation


async def get_risk_assessment(org_id: str, investigation_id: str) -> Any:
    """Fetch the computed RiskAssessment with all RiskSignal breakdowns."""
    async with set_org_context(org_id) as tx:
        assessment = await tx.riskassessment.find_unique(
            where={"investigationId": investigation_id},
            include={"riskSignals": True},
        )
        if assessment:
            fp = assessment.fusionParameters or {}
            if hasattr(fp, "data"):
                fp = fp.data
            elif hasattr(fp, "to_dict"):
                fp = fp.to_dict()
            if not isinstance(fp, dict):
                fp = {}

            da = fp.get("document_authenticity") or {}
            tr = fp.get("transaction_risk") or {}

            tamper_score = da.get("tamper_score", assessment.overallScore)
            auth_score = da.get("score", max(0, 100 - tamper_score))
            auth_tier = da.get(
                "tier",
                "VERIFIED_AUTHENTIC" if tamper_score <= 10 else ("SUSPECT_DOCUMENT" if tamper_score <= 40 else "FORGERY_DETECTED"),
            )
            txn_score = tr.get("score", 0)
            txn_tier = tr.get(
                "tier",
                "CRITICAL_PROSCRIBED" if txn_score >= 75 else ("HIGH_AML_RISK" if txn_score >= 45 else ("MONITORED" if txn_score >= 20 else "CLEAN")),
            )

            assessment.__dict__["authenticity_score"] = auth_score
            assessment.__dict__["tamper_score"] = tamper_score
            assessment.__dict__["authenticity_tier"] = auth_tier
            assessment.__dict__["transaction_risk_score"] = txn_score
            assessment.__dict__["transaction_risk_tier"] = txn_tier
            effective_tier = assessment.overriddenTier or assessment.riskTier
            assessment.__dict__["recommended_action"] = format_recommendation(assessment.actionDirective, effective_tier)

        return assessment



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

    trimmed_reason = (reason or "").strip()
    if len(trimmed_reason) < 10:
        raise ValueError("Mandatory compliance justification of at least 10 characters is required under SBP audit regulations.")

    tier, _ = compute_risk_tier(score)

    async with set_org_context(org_id) as tx:
        assessment = await tx.riskassessment.find_unique(
            where={"investigationId": investigation_id}
        )
        if not assessment:
            raise ValueError(f"No risk assessment exists for investigation '{investigation_id}'")

        rec_action = format_recommendation(assessment.actionDirective, tier)

        updated = await tx.riskassessment.update(
            where={"id": assessment.id},
            data={
                "overriddenById": overriding_user_id,
                "overriddenScore": score,
                "overriddenTier": tier,
                "overrideReason": trimmed_reason,
                "overriddenAt": datetime.now(timezone.utc),
            },
            include={"riskSignals": True},
        )

        # Audit log for human override with previous and new state diff
        audit_data: dict[str, Any] = {
            "organization": {"connect": {"id": org_id}},
            "action": "RISK_SCORE_OVERRIDDEN",
            "entityType": "RISK_ASSESSMENT",
            "entityId": assessment.id,
            "previousState": Json({
                "overallScore": assessment.overallScore,
                "riskTier": str(assessment.riskTier),
                "actionDirective": assessment.actionDirective,
            }),
            "newState": Json({
                "overriddenScore": score,
                "overriddenTier": str(tier),
                "overrideReason": trimmed_reason,
                "overriddenById": overriding_user_id,
                "recommendedAction": rec_action,
            }),
            "metadata": Json({
                "original_score": assessment.overallScore,
                "overridden_score": score,
                "original_tier": str(assessment.riskTier),
                "overridden_tier": str(tier),
                "reason": trimmed_reason,
                "audit_standard": "SBP_BPRD_HUMAN_IN_THE_LOOP",
            }),
        }
        if overriding_user_id:
            audit_data["user"] = {"connect": {"id": overriding_user_id}}

        await tx.auditlog.create(data=audit_data)

        # Unpack dual scores into updated before returning
        fp = updated.fusionParameters or {}
        if hasattr(fp, "data"):
            fp = fp.data
        elif hasattr(fp, "to_dict"):
            fp = fp.to_dict()
        if not isinstance(fp, dict):
            fp = {}
        da = fp.get("document_authenticity") or {}
        tr = fp.get("transaction_risk") or {}

        tamper_score = da.get("tamper_score", updated.overallScore)
        auth_score = da.get("score", max(0, 100 - tamper_score))
        auth_tier = da.get(
            "tier",
            "VERIFIED_AUTHENTIC" if tamper_score <= 10 else ("SUSPECT_DOCUMENT" if tamper_score <= 40 else "FORGERY_DETECTED"),
        )
        txn_score = tr.get("score", 0)
        txn_tier = tr.get(
            "tier",
            "CRITICAL_PROSCRIBED" if txn_score >= 75 else ("HIGH_AML_RISK" if txn_score >= 45 else ("MONITORED" if txn_score >= 20 else "CLEAN")),
        )

        updated.__dict__["authenticity_score"] = auth_score
        updated.__dict__["tamper_score"] = tamper_score
        updated.__dict__["authenticity_tier"] = auth_tier
        updated.__dict__["transaction_risk_score"] = txn_score
        updated.__dict__["transaction_risk_tier"] = txn_tier
        updated.__dict__["recommended_action"] = rec_action

        return updated
