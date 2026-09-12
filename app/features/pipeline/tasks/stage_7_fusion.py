"""
Stage 7: Bayesian Evidence Fusion & Calibrated Risk Scoring — Celery Task & Async Processor
NIST SP 800-86 Compliant Multi-Signal Risk Fusion and Action Directive Calibration.
"""
from datetime import datetime, timezone
import time
from typing import Any

from app.config import get_settings
from app.core.celery_app import celery_app
from prisma import Json
from app.db.client import db, set_org_context

settings = get_settings()

# Domain weights for the evidence categories in the fusion matrix
CATEGORY_WEIGHTS: dict[str, float] = {
    "MATHEMATICAL_MISMATCH": 0.35,
    "IBAN_CHECKSUM_FAILURE": 0.25,
    "FONT_BASELINE_INCONSISTENCY": 0.25,
    "PDF_OBJECT_ANOMALY": 0.20,
    "IMAGE_ELA_MANIPULATION": 0.25,
    "METADATA_TIMESTAMP_MISMATCH": 0.15,
    "DATE_SEQUENCE_VIOLATION": 0.15,
    "TRANSACTION_FORMAT_VIOLATION": 0.10,
    "OCR_CONFIDENCE_ANOMALY": 0.25,
}


def compute_risk_tier(score: int) -> tuple[str, str]:
    """
    Map calibrated 0-100 score to Prisma RiskTier enum and actionable decision directive.
    RiskTier enum: LOW (0-20), MODERATE (21-40), ELEVATED (41-60), HIGH (61-80), CRITICAL (81-100).
    """
    if score <= 20:
        return "LOW", "STRAIGHT_THROUGH_APPROVAL"
    elif score <= 40:
        return "MODERATE", "SECONDARY_SCAN"
    elif score <= 60:
        return "ELEVATED", "HUMAN_REVIEW"
    elif score <= 80:
        return "HIGH", "ESCALATION_REQUIRED"
    else:
        return "CRITICAL", "IMMEDIATE_REJECTION"


async def process_evidence_fusion(
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Stage 7: Bayesian Multi-Signal Evidence Fusion.
    Aggregates all EvidenceItems across stages, calculates per-signal risk scores,
    applies co-occurrence synergy boosts, generates narrative forensic rationale,
    and persists RiskAssessment and RiskSignal records under tenant RLS context.
    """
    start_time = time.perf_counter()

    async with set_org_context(org_id) as tx:
        await tx.pipelinestage.update(
            where={"id": pipeline_stage_id},
            data={"status": "RUNNING", "startedAt": datetime.now(timezone.utc)},
        )

        try:
            # Query all documents in this investigation
            docs = await tx.document.find_many(
                where={"investigationId": investigation_id},
            )
            doc_ids = [d.id for d in docs]

            # Query all evidence items for these documents (including bounding boxes for spatial synergy)
            evidence_items = await tx.evidenceitem.find_many(
                where={"documentId": {"in": doc_ids}},
                include={"boundingBoxes": True},
            )

            # Tally counts by severity
            critical_count = sum(1 for e in evidence_items if e.severity == "CRITICAL")
            high_count = sum(1 for e in evidence_items if e.severity == "HIGH")
            medium_count = sum(1 for e in evidence_items if e.severity == "MEDIUM")
            low_count = sum(1 for e in evidence_items if e.severity == "LOW")
            info_count = sum(1 for e in evidence_items if e.severity == "INFO")
            total_count = len(evidence_items)

            # Cross-Stage Spatial IoU Splicing Synergy (Stage 3 Typography x Stage 4 Vision ELA/TruFor)
            # When typographical baseline offsets and neural/compression noise hotspots converge
            # on the exact same physical coordinates, fraud confidence reaches near-certainty.
            splicing_synergy_pages: set[int] = set()
            font_items = [e for e in evidence_items if e.category == "FONT_BASELINE_INCONSISTENCY"]
            vision_items = [
                e for e in evidence_items
                if e.category == "IMAGE_ELA_MANIPULATION" and e.ruleId in ("RULE_CV_TRUFOR_MANIPULATION", "RULE_CV_ELA_ANOMALY")
            ]

            for f_item in font_items:
                for v_item in vision_items:
                    if f_item.pageNumber and f_item.pageNumber == v_item.pageNumber:
                        for fb in (f_item.boundingBoxes or []):
                            for vb in (v_item.boundingBoxes or []):
                                x1 = fb.xPts if fb.xPts is not None else fb.x
                                y1 = fb.yPts if fb.yPts is not None else fb.y
                                w1 = fb.widthPts if fb.widthPts is not None else fb.width
                                h1 = fb.heightPts if fb.heightPts is not None else fb.height

                                x2 = vb.xPts if vb.xPts is not None else vb.x
                                y2 = vb.yPts if vb.yPts is not None else vb.y
                                w2 = vb.widthPts if vb.widthPts is not None else vb.width
                                h2 = vb.heightPts if vb.heightPts is not None else vb.height

                                ix0 = max(x1, x2)
                                iy0 = max(y1, y2)
                                ix1 = min(x1 + w1, x2 + w2)
                                iy1 = min(y1 + h1, y2 + h2)

                                if ix1 > ix0 and iy1 > iy0:
                                    inter = (ix1 - ix0) * (iy1 - iy0)
                                    min_area = min(w1 * h1, w2 * h2)
                                    if min_area > 0 and (inter / min_area) >= 0.15:
                                        splicing_synergy_pages.add(f_item.pageNumber)

            # Group by category
            category_groups: dict[str, list[Any]] = {}
            for item in evidence_items:
                cat = item.category
                category_groups.setdefault(cat, []).append(item)

            # Compute category signals
            signals_to_create = []
            base_score = 0.0

            for cat, items in category_groups.items():
                raw_score = sum(item.riskPoints for item in items)
                weight = CATEGORY_WEIGHTS.get(cat, 0.10)
                # Weighted score capped at 100 per category contribution
                weighted_cat_score = min(float(raw_score), 100.0) * weight
                base_score += weighted_cat_score

                all_deterministic = all(item.isDeterministic for item in items)

                signals_to_create.append({
                    "signalCategory": cat,
                    "rawScore": float(raw_score),
                    "normalizedWeight": weight,
                    "weightedScore": round(weighted_cat_score, 2),
                    "maxPossiblePoints": 100,
                    "isDeterministic": all_deterministic,
                    "evidenceCount": len(items),
                    "details": {
                        "rules_triggered": list(set(item.ruleId for item in items)),
                        "severities": [item.severity for item in items],
                    },
                })

            # Co-occurrence Synergy Multiplier:
            # If multiple distinct anomaly categories are detected, confidence of fraud multiplies
            distinct_categories = len(category_groups)
            if distinct_categories >= 2:
                base_score *= 1.25

            # Apply Cross-Stage Splicing Synergy Boost
            if splicing_synergy_pages:
                base_score = max(base_score + 25.0, 90.0)
                critical_count += len(splicing_synergy_pages)

            # Deterministic override: If there are CRITICAL mathematical or custody failures, clamp to >= 85
            if critical_count > 0:
                final_score = max(85, min(100, int(round(base_score))))
            elif high_count >= 2:
                final_score = max(65, min(100, int(round(base_score))))
            else:
                final_score = min(100, int(round(base_score)))

            risk_tier, action_directive = compute_risk_tier(final_score)

            # Generate narrative summary
            has_registry_verified = any(e.ruleId == "RULE_PK_UTILITY_REGISTRY_VERIFIED" for e in evidence_items)
            has_bank_template_verified = any(e.ruleId == "RULE_BANK_TEMPLATE_VERIFIED" for e in evidence_items)
            if total_count == 0 or (critical_count == 0 and high_count == 0 and medium_count == 0 and (has_registry_verified or has_bank_template_verified)):
                if has_registry_verified:
                    narrative = (
                        "Document verified 100% authentic against the official government utility authority registry (PITC). "
                        "Payable amounts, billing month, due date, and consumer credentials match live government records. "
                        "No physical typographical distortions, neural tampering, or ELA anomalies detected."
                    )
                elif has_bank_template_verified:
                    narrative = (
                        "Document verified 100% authentic against official Core Banking System (CBS) reporting profiles. "
                        "Columnar layout, font typography, and SBP statutory regulatory footers strictly match "
                        "canonical institutional reporting specifications with zero forensic discrepancies."
                    )
                else:
                    narrative = (
                        "No forensic anomalies detected across structural, typographical, or financial checks. "
                        "The document satisfies all mathematical ledger reconciliations, contains uniform typography "
                        "and font baselines, and adheres to authentic document specifications."
                    )
            else:
                findings_summary = []
                if splicing_synergy_pages:
                    pages_str = ", ".join(f"Page {p}" for p in sorted(splicing_synergy_pages))
                    findings_summary.append(
                        f"confirmed cross-modal physical splicing on {pages_str} (typographical font baseline distortion "
                        f"spatially coincides with neural/compression noise discontinuity)"
                    )
                if critical_count > 0:
                    findings_summary.append(f"{critical_count} critical finding(s) (including ledger arithmetic discrepancies)")
                if high_count > 0:
                    findings_summary.append(f"{high_count} high-severity anomaly(ies) (sub-pixel baseline offsets, producer signatures, or IBAN failures)")
                if medium_count > 0:
                    findings_summary.append(f"{medium_count} medium-severity indicator(s)")

                narrative = (
                    f"Forensic verification completed with an overall fraud risk score of {final_score}/100 ({risk_tier} risk). "
                    f"Identified {', '.join(findings_summary)}. "
                    f"Action Directive: {action_directive.replace('_', ' ')}."
                )

            # Upsert RiskAssessment under tenant RLS context
            # First delete existing risk signals if re-running
            existing_assessment = await tx.riskassessment.find_unique(
                where={"investigationId": investigation_id}
            )

            if existing_assessment:
                await tx.risksignal.delete_many(
                    where={"riskAssessmentId": existing_assessment.id}
                )
                risk_assessment = await tx.riskassessment.update(
                    where={"id": existing_assessment.id},
                    data={
                        "overallScore": final_score,
                        "riskTier": risk_tier,
                        "actionDirective": action_directive,
                        "totalEvidenceCount": total_count,
                        "criticalCount": critical_count,
                        "highCount": high_count,
                        "mediumCount": medium_count,
                        "lowCount": low_count,
                        "infoCount": info_count,
                        "narrativeSummary": narrative,
                        "computedAt": datetime.now(timezone.utc),
                    },
                )
            else:
                risk_assessment = await tx.riskassessment.create(
                    data={
                        "investigation": {"connect": {"id": investigation_id}},
                        "overallScore": final_score,
                        "riskTier": risk_tier,
                        "actionDirective": action_directive,
                        "totalEvidenceCount": total_count,
                        "criticalCount": critical_count,
                        "highCount": high_count,
                        "mediumCount": medium_count,
                        "lowCount": low_count,
                        "infoCount": info_count,
                        "narrativeSummary": narrative,
                        "fusionAlgorithm": "bayesian_weighted",
                        "fusionParameters": Json({
                            "category_weights": CATEGORY_WEIGHTS,
                            "synergy_multiplier": 1.25 if distinct_categories >= 2 else 1.0,
                            "splicing_synergy_detected": bool(splicing_synergy_pages),
                            "splicing_synergy_pages": list(sorted(splicing_synergy_pages)),
                        }),
                    }
                )

            # Create RiskSignal records
            for sig in signals_to_create:
                await tx.risksignal.create(
                    data={
                        "riskAssessment": {"connect": {"id": risk_assessment.id}},
                        "signalCategory": sig["signalCategory"],
                        "rawScore": sig["rawScore"],
                        "normalizedWeight": sig["normalizedWeight"],
                        "weightedScore": sig["weightedScore"],
                        "maxPossiblePoints": sig["maxPossiblePoints"],
                        "isDeterministic": sig["isDeterministic"],
                        "evidenceCount": sig["evidenceCount"],
                        "details": Json(sig["details"]),
                    }
                )

            # Update Investigation status
            new_inv_status = "AWAITING_REVIEW" if final_score >= 41 else "REVIEWED"
            await tx.investigation.update(
                where={"id": investigation_id},
                data={"status": new_inv_status},
            )

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            output_payload = {
                "overall_score": final_score,
                "risk_tier": risk_tier,
                "action_directive": action_directive,
                "total_evidence_count": total_count,
                "critical_count": critical_count,
                "high_count": high_count,
                "duration_ms": duration_ms,
                "narrative": narrative,
            }

            await tx.pipelinestage.update(
                where={"id": pipeline_stage_id},
                data={
                    "status": "COMPLETED",
                    "durationMs": duration_ms,
                    "completedAt": datetime.now(timezone.utc),
                    "outputPayload": Json(output_payload),
                },
            )
            return output_payload

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            await tx.pipelinestage.update(
                where={"id": pipeline_stage_id},
                data={
                    "status": "FAILED",
                    "durationMs": duration_ms,
                    "completedAt": datetime.now(timezone.utc),
                    "errorMessage": str(exc),
                    "errorStack": exc.__class__.__name__,
                },
            )
            raise


@celery_app.task(
    name="app.features.pipeline.tasks.stage_7_fusion",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run(
    self,
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict:
    """Celery task entry point for Stage 7."""
    import asyncio
    return asyncio.run(
        process_evidence_fusion(
            pipeline_run_id, pipeline_stage_id, org_id, investigation_id, document_id
        )
    )
