"""
tests/test_override_audit_and_recommendations.py
Unit and integration tests verifying:
1. SBP-compliant 10-character minimum justification validation on risk score overrides.
2. Comprehensive Prisma AuditLog state diffs (previousState, newState, metadata).
3. Dual decoupled scores and recommended_action propagation in RiskAssessmentResponse.
4. Advisory forensic recommendations replacing statutory action directives across human touchpoints.
"""
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from app.features.risk.schemas import (
    RiskOverrideRequest,
    RiskAssessmentResponse,
    RECOMMENDATION_MAP,
    format_recommendation,
)
from app.features.risk.service import override_risk_score
from app.features.agents.swarm.lead_investigator import _generate_deterministic_briefing


class TestOverrideAuditAndRecommendations(unittest.IsolatedAsyncioTestCase):
    """Test suite for human adjudication overrides, audit diffs, and recommendation framing."""

    def test_recommendation_formatter_mappings(self):
        """Verify all internal database action directives format into human-in-the-loop recommendations."""
        expected_mappings = {
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

        for directive, expected in expected_mappings.items():
            self.assertEqual(
                format_recommendation(directive),
                expected,
                f"Mismatch for directive {directive}",
            )

        # None / empty fallback
        self.assertEqual(
            format_recommendation(None),
            "Recommend: Operational Verification",
        )
        self.assertEqual(
            format_recommendation(""),
            "Recommend: Operational Verification",
        )

        # Fuzzy / keyword fallbacks
        self.assertEqual(
            format_recommendation("AUTO_REJECT_FRAUD"),
            "Recommend: Reject / Escalate to Fraud Unit",
        )
        self.assertEqual(
            format_recommendation("SUSPICIOUS_STR_FILE"),
            "Recommend: Mandatory STR Escalation & Freeze Review",
        )
        self.assertEqual(
            format_recommendation("EDD_INVESTIGATION"),
            "Recommend: Enhanced Due Diligence / Compliance Review",
        )

    def test_risk_override_request_validation(self):
        """Pydantic schema must strictly enforce [0, 100] score and >=10 char justification."""
        # Valid override
        valid_req = RiskOverrideRequest(
            score=35,
            reason="Branch verified physically signed deposit slip with account manager.",
        )
        self.assertEqual(valid_req.score, 35)
        self.assertEqual(
            valid_req.reason,
            "Branch verified physically signed deposit slip with account manager.",
        )

        # Score < 0
        with self.assertRaises(ValidationError):
            RiskOverrideRequest(score=-1, reason="Valid justification over 10 chars")

        # Score > 100
        with self.assertRaises(ValidationError):
            RiskOverrideRequest(score=101, reason="Valid justification over 10 chars")

        # Justification too short (<10 chars)
        with self.assertRaises(ValidationError):
            RiskOverrideRequest(score=50, reason="looks ok")

        # Empty justification
        with self.assertRaises(ValidationError):
            RiskOverrideRequest(score=50, reason="")

    def test_risk_assessment_response_schema_fields(self):
        """Verify response schema serializes override attributes and recommended_action."""
        now = datetime.now(timezone.utc)
        payload = {
            "id": "ra-001",
            "investigationId": "inv-001",
            "overallScore": 85,
            "riskTier": "CRITICAL",
            "actionDirective": "IMMEDIATE_REJECTION",
            "recommendedAction": "Recommend: Reject / Escalate to Fraud Unit",
            "overriddenScore": 30,
            "overriddenTier": "LOW",
            "overrideReason": "Manual branch verification passed with certified seal.",
            "overriddenById": "usr-auditor-9",
            "overriddenAt": now,
            "totalEvidenceCount": 1,
            "criticalCount": 1,
            "highCount": 0,
            "mediumCount": 0,
            "lowCount": 0,
            "infoCount": 0,
            "computedAt": now,
            "fusionParameters": {
                "document_authenticity": {"score": 90, "tamper_score": 10, "tier": "VERIFIED_AUTHENTIC"},
                "transaction_risk": {"score": 20, "tier": "CLEAN"},
            },
        }

        resp = RiskAssessmentResponse.model_validate(payload)
        self.assertEqual(resp.overall_score, 85)
        self.assertEqual(resp.overridden_score, 30)
        self.assertEqual(resp.overridden_tier, "LOW")
        self.assertEqual(resp.override_reason, "Manual branch verification passed with certified seal.")
        self.assertEqual(resp.overridden_by_id, "usr-auditor-9")
        self.assertEqual(resp.overridden_at, now)
        self.assertEqual(resp.recommended_action, "Recommend: Reject / Escalate to Fraud Unit")
        self.assertEqual(resp.authenticity_score, 90)
        self.assertEqual(resp.transaction_risk_score, 20)

    async def test_override_service_validation_and_audit_diff(self):
        """Test that override_risk_score records previousState, newState diffs in Prisma AuditLog."""
        # 1. Validation rejection on service level
        with self.assertRaises(ValueError) as ctx:
            await override_risk_score("org-1", "inv-1", 40, "usr-1", "  short  ")
        self.assertIn("at least 10 characters", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            await override_risk_score("org-1", "inv-1", 120, "usr-1", "Valid explanation for override")
        self.assertIn("between 0 and 100", str(ctx.exception))

        # 2. Mock DB transaction context for successful override
        existing_ra = MagicMock()
        existing_ra.id = "ra-999"
        existing_ra.investigationId = "inv-test"
        existing_ra.overallScore = 80
        existing_ra.riskTier = "CRITICAL"
        existing_ra.actionDirective = "IMMEDIATE_REJECTION"
        existing_ra.fusionParameters = {
            "document_authenticity": {"score": 30, "tamper_score": 70, "tier": "FORGERY_DETECTED"},
            "transaction_risk": {"score": 15, "tier": "CLEAN"},
        }

        updated_ra = MagicMock()
        updated_ra.id = "ra-999"
        updated_ra.investigationId = "inv-test"
        updated_ra.overallScore = 80
        updated_ra.riskTier = "CRITICAL"
        updated_ra.actionDirective = "IMMEDIATE_REJECTION"
        updated_ra.overriddenScore = 20
        updated_ra.overriddenTier = "LOW"
        updated_ra.overrideReason = "Verified counterfoil directly with Meezan Bank I.I. Chundrigar branch."
        updated_ra.overriddenById = "usr-senior-auditor"
        updated_ra.overriddenAt = datetime.now(timezone.utc)
        updated_ra.fusionParameters = existing_ra.fusionParameters

        mock_tx = MagicMock()
        mock_tx.riskassessment.find_unique = AsyncMock(return_value=existing_ra)
        mock_tx.riskassessment.update = AsyncMock(return_value=updated_ra)
        mock_tx.auditlog.create = AsyncMock()

        # Context manager for set_org_context
        class MockOrgContext:
            async def __aenter__(self):
                return mock_tx
            async def __aexit__(self, *args):
                pass

        with patch("app.features.risk.service.set_org_context", return_value=MockOrgContext()):
            res = await override_risk_score(
                org_id="org-pk-01",
                investigation_id="inv-test",
                score=20,
                overriding_user_id="usr-senior-auditor",
                reason="Verified counterfoil directly with Meezan Bank I.I. Chundrigar branch.",
            )

            # Verify update was called with correct data
            mock_tx.riskassessment.update.assert_called_once()
            call_kwargs = mock_tx.riskassessment.update.call_args[1]
            self.assertEqual(call_kwargs["data"]["overriddenScore"], 20)
            self.assertEqual(call_kwargs["data"]["overriddenTier"], "LOW")
            self.assertEqual(
                call_kwargs["data"]["overrideReason"],
                "Verified counterfoil directly with Meezan Bank I.I. Chundrigar branch.",
            )

            # Verify AuditLog.create recorded previous and new state diff
            mock_tx.auditlog.create.assert_called_once()
            audit_call_data = mock_tx.auditlog.create.call_args[1]["data"]
            self.assertEqual(audit_call_data["action"], "RISK_SCORE_OVERRIDDEN")
            self.assertEqual(audit_call_data["entityType"], "RISK_ASSESSMENT")
            self.assertEqual(audit_call_data["entityId"], "ra-999")

            prev_state = audit_call_data["previousState"].data
            new_state = audit_call_data["newState"].data
            meta = audit_call_data["metadata"].data

            self.assertEqual(prev_state["overallScore"], 80)
            self.assertEqual(prev_state["riskTier"], "CRITICAL")
            self.assertEqual(prev_state["actionDirective"], "IMMEDIATE_REJECTION")

            self.assertEqual(new_state["overriddenScore"], 20)
            self.assertEqual(new_state["overriddenTier"], "LOW")
            self.assertEqual(new_state["overriddenById"], "usr-senior-auditor")
            self.assertEqual(
                new_state["recommendedAction"],
                "Recommend: Reject / Escalate to Fraud Unit",
            )

            self.assertEqual(meta["original_score"], 80)
            self.assertEqual(meta["overridden_score"], 20)
            self.assertEqual(meta["audit_standard"], "SBP_BPRD_HUMAN_IN_THE_LOOP")

            # Check unpacked dual scores on returned result
            self.assertEqual(res.recommended_action, "Recommend: Reject / Escalate to Fraud Unit")
            self.assertEqual(res.authenticity_score, 30)
            self.assertEqual(res.transaction_risk_score, 15)

    def test_lead_investigator_deterministic_override_framing(self):
        """Lead investigator summary highlights human adjudication notice and baseline comparisons."""
        briefing_items = [
            {
                "summary_en": "Page 1: Signature stamp offset",
                "summary_ur": "صفحہ 1: دستخط کی جگہ تبدیل",
                "severity": "CRITICAL",
                "is_adverse": True,
            }
        ]

        en, ur, narr = _generate_deterministic_briefing(
            overall_score=85,
            risk_tier="CRITICAL",
            action_directive="IMMEDIATE_REJECTION",
            evidence_items=[],
            cross_signal_correlations=[],
            briefing_items=briefing_items,
            authenticity_score=20,
            tamper_score=80,
            authenticity_tier="FORGERY_DETECTED",
            transaction_risk_score=10,
            transaction_risk_tier="CLEAN",
            overridden_score=25,
            overridden_tier="LOW",
            override_reason="Account holder presented original wet-ink signed statement at the branch.",
            overridden_by="Lead Auditor Fatima",
        )

        # Verify advisory framing
        self.assertIn("Forensic Recommendation: Recommend: Reject / Escalate to Fraud Unit (Human Adjudication Required)", en)
        self.assertIn("Evaluated Risk: 25/100 (LOW Risk) [Engine Baseline: 85/100 (CRITICAL)]", en)
        self.assertIn("[HUMAN ADJUDICATION AUDIT NOTICE]", en)
        self.assertIn("Account holder presented original wet-ink signed statement", en)
        self.assertIn("Lead Auditor Fatima", en)
        self.assertIn("statutory prerogative of authorized human credit & compliance officers", en)

        # Verify Urdu advisory framing
        self.assertIn("تجویز کردہ کارروائی: سفارش: درخواست مسترد / اینٹی فراڈ یونٹ کو بھیجیں (حتمی فیصلہ مجاز افسر کا ہوگا)", ur)
        self.assertIn("[آڈٹ نوٹ برائے انسانی فیصلہ]", ur)
        self.assertIn("25/100 (LOW) [سسٹم کا ابتدائی سکور: 85/100]", ur)
        self.assertIn("تمام مالیاتی و قرضہ جاتی فیصلے مجاز افسران کی صوابدید پر منحصر ہیں", ur)


if __name__ == "__main__":
    unittest.main()
