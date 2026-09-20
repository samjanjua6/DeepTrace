"""
tests/test_dual_risk_scores.py
Unit and integration tests for decoupled Document Authenticity & Transaction Risk scores.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import unittest
from typing import Any

from app.features.pipeline.tasks.stage_7_fusion import (
    compute_authenticity_tier,
    compute_transaction_risk_tier,
    compute_risk_tier,
    is_tamper_item,
    is_transaction_risk_item,
    CATEGORY_WEIGHTS,
)
from app.features.risk.schemas import RiskAssessmentResponse
from app.features.agents.swarm.lead_investigator import _generate_deterministic_briefing


@dataclass
class MockEvidenceItem:
    id: str
    category: str
    ruleId: str
    severity: str
    riskPoints: int = 0
    isDeterministic: bool = True
    pageNumber: int | None = 1
    title: str = ""
    description: str = ""
    boundingBoxes: list[Any] = field(default_factory=list)


class TestDualRiskScores(unittest.TestCase):
    """Test suite for decoupled dual scoring engine."""

    def test_item_classification_routing(self):
        """Verify evidence classification accurately bifurcates tampering from financial/AML risk."""
        font_item = MockEvidenceItem("1", "FONT_BASELINE_INCONSISTENCY", "RULE_FONT_BASELINE_OFFSET", "HIGH", 30)
        pdf_item = MockEvidenceItem("2", "PDF_OBJECT_ANOMALY", "RULE_PDF_INCREMENTAL_SAVES", "HIGH", 25)
        ela_item = MockEvidenceItem("3", "IMAGE_ELA_MANIPULATION", "RULE_CV_ELA_ANOMALY", "MEDIUM", 20)
        math_item = MockEvidenceItem("4", "MATHEMATICAL_MISMATCH", "RULE_PK_LEDGER_RECONCILIATION_FAIL", "CRITICAL", 45)
        template_item = MockEvidenceItem("5", "TRANSACTION_FORMAT_VIOLATION", "RULE_BANK_TEMPLATE_COLUMN_MISALIGNMENT", "HIGH", 30)

        for item in [font_item, pdf_item, ela_item, math_item, template_item]:
            self.assertTrue(is_tamper_item(item), f"Expected {item.ruleId} to be classified as tamper item")

        nacta_item = MockEvidenceItem("6", "TRANSACTION_FORMAT_VIOLATION", "RULE_AML_NACTA_PROSCRIBED_MATCH", "CRITICAL", 100)
        pep_item = MockEvidenceItem("7", "TRANSACTION_FORMAT_VIOLATION", "RULE_AML_PEP_IDENTIFIED", "HIGH", 35)
        crypto_item = MockEvidenceItem("8", "TRANSACTION_FORMAT_VIOLATION", "RULE_AML_HIGH_RISK_NARRATION", "HIGH", 25)
        date_item = MockEvidenceItem("9", "DATE_SEQUENCE_VIOLATION", "RULE_PK_FUTURE_DATE_TRANSACTION", "MEDIUM", 15)
        cnic_item = MockEvidenceItem("10", "TRANSACTION_FORMAT_VIOLATION", "RULE_CNIC_PROVINCE_CODE_INVALID", "HIGH", 30)

        for item in [nacta_item, pep_item, crypto_item, date_item, cnic_item]:
            self.assertTrue(is_transaction_risk_item(item), f"Expected {item.ruleId} to be classified as transaction risk item")


    def test_tier_computations(self):
        """Test threshold boundaries for authenticity and transaction risk tiers."""
        self.assertEqual(compute_authenticity_tier(0), "VERIFIED_AUTHENTIC")
        self.assertEqual(compute_authenticity_tier(10), "VERIFIED_AUTHENTIC")
        self.assertEqual(compute_authenticity_tier(11), "SUSPECT_DOCUMENT")
        self.assertEqual(compute_authenticity_tier(40), "SUSPECT_DOCUMENT")
        self.assertEqual(compute_authenticity_tier(41), "FORGERY_DETECTED")
        self.assertEqual(compute_authenticity_tier(100), "FORGERY_DETECTED")

        self.assertEqual(compute_transaction_risk_tier(0), "CLEAN")
        self.assertEqual(compute_transaction_risk_tier(20), "CLEAN")
        self.assertEqual(compute_transaction_risk_tier(21), "MONITORED")
        self.assertEqual(compute_transaction_risk_tier(40), "MONITORED")
        self.assertEqual(compute_transaction_risk_tier(41), "HIGH_AML_RISK")
        self.assertEqual(compute_transaction_risk_tier(70), "HIGH_AML_RISK")
        self.assertEqual(compute_transaction_risk_tier(71), "CRITICAL_PROSCRIBED")
        self.assertEqual(compute_transaction_risk_tier(100), "CRITICAL_PROSCRIBED")

    def _compute_fusion_scores(self, evidence_items: list[MockEvidenceItem]):
        tamper_evidence = [
            item for item in evidence_items
            if item.severity != "INFO" and (item.riskPoints or 0) > 0 and is_tamper_item(item)
        ]
        transaction_evidence = [
            item for item in evidence_items
            if item.severity != "INFO" and (item.riskPoints or 0) > 0 and is_transaction_risk_item(item)
        ]

        tamper_base = 0.0
        tamper_cat_groups: dict[str, list[Any]] = {}
        for item in tamper_evidence:
            tamper_cat_groups.setdefault(item.category, []).append(item)

        for cat, items in tamper_cat_groups.items():
            raw_score = sum(item.riskPoints for item in items)
            w = CATEGORY_WEIGHTS.get(cat, 0.20)
            tamper_base += min(float(raw_score), 100.0) * w

        if len(tamper_cat_groups) >= 2:
            tamper_base *= 1.25

        has_crit_tamper = any(item.severity == "CRITICAL" for item in tamper_evidence)
        high_tamper_count = sum(1 for item in tamper_evidence if item.severity == "HIGH")

        if has_crit_tamper:
            tamper_score = max(85, min(100, int(round(tamper_base))))
        elif high_tamper_count >= 2:
            tamper_score = max(65, min(100, int(round(tamper_base))))
        elif tamper_evidence:
            tamper_score = max(10, min(100, int(round(tamper_base))))
        else:
            tamper_score = 0

        authenticity_score = max(0, 100 - tamper_score)
        authenticity_tier = compute_authenticity_tier(tamper_score)

        has_nacta_or_unsc = any(
            "NACTA" in (item.ruleId or "") or "UNSC" in (item.ruleId or "")
            for item in transaction_evidence
        )
        if has_nacta_or_unsc:
            transaction_risk_score = 100
        else:
            raw_txn_points = sum(item.riskPoints for item in transaction_evidence)
            has_crit_txn = any(item.severity == "CRITICAL" for item in transaction_evidence)
            high_txn_count = sum(1 for item in transaction_evidence if item.severity == "HIGH")

            if has_crit_txn:
                transaction_risk_score = max(85, min(100, raw_txn_points))
            elif high_txn_count >= 2:
                transaction_risk_score = max(65, min(100, raw_txn_points))
            elif high_txn_count == 1:
                transaction_risk_score = max(35, min(100, raw_txn_points))
            elif transaction_evidence:
                transaction_risk_score = min(100, raw_txn_points)
            else:
                transaction_risk_score = 0

        transaction_risk_tier = compute_transaction_risk_tier(transaction_risk_score)

        final_score = max(tamper_score, transaction_risk_score)
        if tamper_score >= 20 and transaction_risk_score >= 20:
            final_score = min(100, int(round(final_score * 1.15)))

        risk_tier, tier_directive = compute_risk_tier(final_score)

        if has_nacta_or_unsc:
            action_directive = "MANDATORY_STR_AND_ACCOUNT_FREEZE"
        elif tamper_score >= 85:
            action_directive = "IMMEDIATE_REJECTION"
        elif transaction_risk_score >= 60 and tamper_score <= 10:
            action_directive = "ENHANCED_TRANSACTION_MONITORING"
        else:
            action_directive = tier_directive

        return {
            "authenticity_score": authenticity_score,
            "tamper_score": tamper_score,
            "authenticity_tier": authenticity_tier,
            "transaction_risk_score": transaction_risk_score,
            "transaction_risk_tier": transaction_risk_tier,
            "overall_score": final_score,
            "risk_tier": risk_tier,
            "action_directive": action_directive,
        }

    def test_scenario_clean_forgery(self):
        evidence = [
            MockEvidenceItem("1", "FONT_BASELINE_INCONSISTENCY", "RULE_FONT_BASELINE_OFFSET", "HIGH", 30),
            MockEvidenceItem("2", "PDF_OBJECT_ANOMALY", "RULE_PDF_INCREMENTAL_SAVES", "HIGH", 25),
        ]
        res = self._compute_fusion_scores(evidence)
        self.assertLessEqual(res["authenticity_score"], 35)
        self.assertEqual(res["authenticity_tier"], "FORGERY_DETECTED")
        self.assertEqual(res["transaction_risk_score"], 0)
        self.assertEqual(res["transaction_risk_tier"], "CLEAN")

    def test_scenario_authentic_aml_hit(self):
        evidence = [
            MockEvidenceItem("1", "CBS_LAYOUT_PROFILE", "RULE_BANK_TEMPLATE_VERIFIED", "INFO", 0),
            MockEvidenceItem("2", "TRANSACTION_FORMAT_VIOLATION", "RULE_AML_HIGH_RISK_NARRATION", "HIGH", 25),
            MockEvidenceItem("3", "TRANSACTION_FORMAT_VIOLATION", "RULE_AML_PEP_IDENTIFIED", "HIGH", 35),
        ]
        res = self._compute_fusion_scores(evidence)
        self.assertEqual(res["authenticity_score"], 100)
        self.assertEqual(res["authenticity_tier"], "VERIFIED_AUTHENTIC")
        self.assertEqual(res["tamper_score"], 0)
        self.assertGreaterEqual(res["transaction_risk_score"], 60)
        self.assertEqual(res["transaction_risk_tier"], "HIGH_AML_RISK")
        self.assertEqual(res["action_directive"], "ENHANCED_TRANSACTION_MONITORING")

    def test_scenario_clean_retail(self):
        evidence = [
            MockEvidenceItem("1", "CBS_LAYOUT_PROFILE", "RULE_BANK_TEMPLATE_VERIFIED", "INFO", 0),
            MockEvidenceItem("2", "TRANSACTION_FORMAT_VIOLATION", "RULE_CNIC_VERIFIED", "INFO", 0),
        ]
        res = self._compute_fusion_scores(evidence)
        self.assertEqual(res["authenticity_score"], 100)
        self.assertEqual(res["authenticity_tier"], "VERIFIED_AUTHENTIC")
        self.assertEqual(res["transaction_risk_score"], 0)
        self.assertEqual(res["transaction_risk_tier"], "CLEAN")
        self.assertEqual(res["action_directive"], "STRAIGHT_THROUGH_APPROVAL")

    def test_scenario_compound_malicious(self):
        evidence = [
            MockEvidenceItem("1", "MATHEMATICAL_MISMATCH", "RULE_PK_LEDGER_RECONCILIATION_FAIL", "CRITICAL", 45),
            MockEvidenceItem("2", "TRANSACTION_FORMAT_VIOLATION", "RULE_AML_NACTA_PROSCRIBED_MATCH", "CRITICAL", 100),
        ]
        res = self._compute_fusion_scores(evidence)
        self.assertLessEqual(res["authenticity_score"], 15)
        self.assertEqual(res["authenticity_tier"], "FORGERY_DETECTED")
        self.assertEqual(res["transaction_risk_score"], 100)
        self.assertEqual(res["transaction_risk_tier"], "CRITICAL_PROSCRIBED")
        self.assertEqual(res["action_directive"], "MANDATORY_STR_AND_ACCOUNT_FREEZE")

    def test_lead_investigator_bifurcated_advisory(self):
        briefing_items = [{
            "summary_en": "Page 1: High-Risk Narration (Binance P2P)",
            "summary_ur": "صفحہ 1: مشکوک کرپٹو الفاظ",
            "severity": "HIGH",
            "is_adverse": True,
        }]
        en, ur, narr = _generate_deterministic_briefing(
            overall_score=60,
            risk_tier="HIGH",
            action_directive="ENHANCED_TRANSACTION_MONITORING",
            evidence_items=[],
            cross_signal_correlations=[],
            briefing_items=briefing_items,
            authenticity_score=100,
            tamper_score=0,
            authenticity_tier="VERIFIED_AUTHENTIC",
            transaction_risk_score=60,
            transaction_risk_tier="HIGH_AML_RISK",
        )

        self.assertNotIn("artificially inflated", en.lower())
        self.assertNotIn("ردوبدل کر کے بیلنس بڑھایا گیا", ur)
        self.assertIn("Statutory AML/CFT Compliance Advisory", en)
        self.assertIn("Document Authenticity: 100%", en)
        self.assertIn("Transaction Risk: 60/100", en)

        briefing_tamper = [{
            "summary_en": "Page 1, Row 5: Altered closing balance",
            "summary_ur": "صفحہ 1، قطار 5: تبدیل شدہ بیلنس",
            "severity": "CRITICAL",
            "is_adverse": True,
        }]
        en_t, ur_t, narr_t = _generate_deterministic_briefing(
            overall_score=85,
            risk_tier="CRITICAL",
            action_directive="IMMEDIATE_REJECTION",
            evidence_items=[],
            cross_signal_correlations=[],
            briefing_items=briefing_tamper,
            authenticity_score=15,
            tamper_score=85,
            authenticity_tier="FORGERY_DETECTED",
            transaction_risk_score=0,
            transaction_risk_tier="CLEAN",
        )
        self.assertIn("Credit Risk Advisory", en_t)
        self.assertIn("artificially inflated", en_t.lower())
        self.assertIn("Document Authenticity: 15%", en_t)

    def test_risk_assessment_schema_validator(self):
        raw_payload = {
            "id": "ra-123",
            "investigationId": "inv-456",
            "overallScore": 60,
            "riskTier": "HIGH",
            "actionDirective": "ENHANCED_TRANSACTION_MONITORING",
            "totalEvidenceCount": 2,
            "criticalCount": 0,
            "highCount": 2,
            "mediumCount": 0,
            "lowCount": 0,
            "infoCount": 1,
            "computedAt": datetime.now(timezone.utc),
            "fusionParameters": {
                "document_authenticity": {
                    "score": 100,
                    "tamper_score": 0,
                    "tier": "VERIFIED_AUTHENTIC",
                },
                "transaction_risk": {
                    "score": 60,
                    "tier": "HIGH_AML_RISK",
                },
            },
        }

        resp = RiskAssessmentResponse.model_validate(raw_payload)
        self.assertEqual(resp.overall_score, 60)
        self.assertEqual(resp.authenticity_score, 100)
        self.assertEqual(resp.tamper_score, 0)
        self.assertEqual(resp.authenticity_tier, "VERIFIED_AUTHENTIC")
        self.assertEqual(resp.transaction_risk_score, 60)
        self.assertEqual(resp.transaction_risk_tier, "HIGH_AML_RISK")


if __name__ == "__main__":
    unittest.main()
