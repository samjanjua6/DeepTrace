"""
Unit & Integration Test Suite: LangGraph Lead Investigator Agent with Groq (gpt-oss-120b / gpt-oss-20b)
Verifies:
  1. LangGraph StateGraph orchestration of Structural, Visual, and Semantic PK agents.
  2. Multi-vector cross-signal correlation (Font + Math, ELA + Math, External Editor + ELA).
  3. Plain English credit officer briefing with exact page, row, PKR discrepancy, and font details.
  4. Urdu credit officer briefing (خلاصہ برائے کریڈٹ آفیسر) with authentic Pakistani banking terminology.
  5. Groq primary model (gpt-oss-120b) and fallback model (gpt-oss-20b) execution paths.
  6. Deterministic zero-hallucination safety net when API keys are absent or offline.
  7. Guardrails rejecting non-existent evidence references.
  8. Interactive Q&A in English and Urdu strictly grounded in the evidence manifest.
"""
import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, r"d:\zylo\DeepTrace")

from app.config import get_settings
from app.features.agents.swarm.lead_investigator import (
    LeadInvestigatorAgent,
    _extract_row_number,
    _extract_font_details,
    _build_structured_credit_briefing_items,
    _call_groq_llm,
)

settings = get_settings()


class TestLeadInvestigatorAgent(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.sample_manifest = {
            "investigation": {
                "id": "inv-pk-test-01",
                "caseNumber": "DT-PK-2026-000099",
                "title": "Meezan Bank Credit Application Audit",
            },
            "documents": [
                {
                    "id": "doc-01",
                    "originalFilename": "Meezan_Salary_Statement.pdf",
                    "sha256Hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "pageCount": 5,
                }
            ],
            "risk_assessment": {
                "overallScore": 88,
                "riskTier": "CRITICAL",
                "actionDirective": "IMMEDIATE_REJECTION",
            },
            "evidence_items": [
                {
                    "id": "ev-font-1",
                    "documentId": "doc-01",
                    "ruleId": "RULE_FONT_MISMATCH",
                    "category": "FONT_GLYPH_ANALYSIS",
                    "severity": "CRITICAL",
                    "riskPoints": 35,
                    "title": "Unauthorized Font Substitution Detected",
                    "description": "Page 2, Row 4: Font is Calibri instead of document's Arial-BoldMT.",
                    "pageNumber": 2,
                },
                {
                    "id": "ev-math-1",
                    "documentId": "doc-01",
                    "ruleId": "RULE_PK_LEDGER_RECONCILIATION_FAIL",
                    "category": "FINANCIAL_VERIFICATION",
                    "severity": "CRITICAL",
                    "riskPoints": 50,
                    "title": "Salary Credit Inflation Discrepancy",
                    "description": "Page 2, Row 4: Salary credit of PKR 450,000 does not match running balance (+PKR 150,000 discrepancy).",
                    "expectedValue": "PKR 300,000.00",
                    "actualValue": "PKR 450,000.00",
                    "discrepancy": "+PKR 150,000.00",
                    "pageNumber": 2,
                    "isDeterministic": True,
                },
                {
                    "id": "ev-ela-1",
                    "documentId": "doc-01",
                    "ruleId": "RULE_CV_ELA_ANOMALY",
                    "category": "COMPUTER_VISION_ELA",
                    "severity": "HIGH",
                    "riskPoints": 30,
                    "title": "Localized ELA Compression Discontinuity",
                    "description": "Page 2, Row 4: Localized compression boundaries surround credit amount digits.",
                    "pageNumber": 2,
                },
            ],
        }

    def test_row_and_font_extraction_helpers(self):
        """Verify regex helpers correctly extract row numbers and font substitution names."""
        # Row number
        text1 = "Page 2, Row 4: Salary credit of PKR 450,000"
        self.assertEqual(_extract_row_number(text1), 4)

        text2 = "Line 12: Stated balance mismatch"
        self.assertEqual(_extract_row_number(text2), 12)

        # Font extraction
        item = {
            "title": "Font tampering",
            "description": "Font is Calibri instead of document's Arial-BoldMT",
        }
        actual, expected = _extract_font_details(item, [])
        self.assertEqual(actual, "Calibri")
        self.assertEqual(expected, "Arial-BoldMT")

    def test_structured_credit_briefing_items(self):
        """Ensure evidence items are parsed into credit briefing structures with English and Urdu summaries."""
        items = _build_structured_credit_briefing_items(self.sample_manifest["evidence_items"])
        self.assertEqual(len(items), 3)

        math_item = next(it for it in items if "RULE_PK" in (it.get("rule_id") or ""))
        self.assertEqual(math_item["page_number"], 2)
        self.assertEqual(math_item["row_number"], 4)
        self.assertIn("PKR 450,000", math_item["actual_value"])
        self.assertIn("+PKR 150,000", math_item["discrepancy"])
        # Verify font details attached
        self.assertEqual(math_item["font_detected"], "Calibri")
        self.assertEqual(math_item["expected_font"], "Arial-BoldMT")

        # Verify English and Urdu summaries contain specific details
        self.assertIn("Page 2, Row 4", math_item["summary_en"])
        self.assertIn("Calibri", math_item["summary_en"])
        self.assertIn("صفحہ 2، قطار 4", math_item["summary_ur"])
        self.assertIn("Calibri", math_item["summary_ur"])
        self.assertIn("Arial-BoldMT", math_item["summary_ur"])

    async def test_langgraph_full_analysis_deterministic_fallback(self):
        """Test full LangGraph StateGraph analysis without LLM API keys (deterministic safety net)."""
        agent = LeadInvestigatorAgent(self.sample_manifest)
        res = await agent.analyze()

        self.assertEqual(res["agent_role"], "LEAD_INVESTIGATOR")
        self.assertEqual(res["risk_tier"], "CRITICAL")
        self.assertEqual(res["overall_score"], 88)
        self.assertEqual(res["action_directive"], "IMMEDIATE_REJECTION")
        self.assertEqual(res["anomalies_detected"], 3)

        # Verify cross-signal correlations
        self.assertTrue(len(res["cross_signal_correlations"]) >= 2)
        self.assertTrue(
            any("Multi-Vector Convergence" in c for c in res["cross_signal_correlations"])
        )
        self.assertTrue(
            any("Page 2 Co-Location" in c for c in res["cross_signal_correlations"])
        )

        # Verify Plain English Credit Officer Briefing
        self.assertIn("CRITICAL BRIEFING FOR CREDIT UNDERWRITERS", res["english_summary"])
        self.assertIn("Page 2, Row 4", res["english_summary"])
        self.assertIn("PKR 450,000", res["english_summary"])

        # Verify Urdu Credit Officer Briefing
        self.assertIn("خلاصہ", res["urdu_summary"])
        self.assertIn("صفحہ 2، قطار 4", res["urdu_summary"])
        self.assertIn("مسترد", res["urdu_summary"])

        # Verify structured credit briefing items
        self.assertTrue(len(res["credit_briefing_items"]) >= 3)
        self.assertEqual(res["credit_briefing_items"][0]["page_number"], 2)

    async def test_groq_llm_primary_and_fallback_dispatch(self):
        """Test Groq LLM invocation with primary model gpt-oss-120b and fallback gpt-oss-20b."""
        # Scenario 1: Primary succeeds
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="SECTION 1: Plain English Briefing\\nSECTION 2: خلاصہ برائے کریڈٹ آفیسر"))
        ]

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch("groq.AsyncGroq", return_value=mock_client):
            text, provider, model = await _call_groq_llm(
                prompt="Audit prompt",
                system_prompt="System prompt",
                primary_model="gpt-oss-120b",
                fallback_model="gpt-oss-20b",
                api_key="gsk_dummy_test_key",
            )
            self.assertEqual(provider, "groq")
            self.assertEqual(model, "gpt-oss-120b")
            self.assertIn("SECTION 1", text)

        # Scenario 2: Primary fails (e.g. rate limit), fallback to gpt-oss-20b succeeds
        def side_effect(*args, **kwargs):
            if kwargs.get("model") == "gpt-oss-120b":
                raise Exception("Model gpt-oss-120b capacity limit reached")
            return mock_completion

        mock_client_fallback = MagicMock()
        mock_client_fallback.chat.completions.create = AsyncMock(side_effect=side_effect)

        with patch("groq.AsyncGroq", return_value=mock_client_fallback):
            with patch("httpx.AsyncClient.post", side_effect=Exception("HTTP connection refused")):
                text, provider, model = await _call_groq_llm(
                    prompt="Audit prompt",
                    system_prompt="System prompt",
                    primary_model="gpt-oss-120b",
                    fallback_model="gpt-oss-20b",
                    api_key="gsk_dummy_test_key",
                )
                self.assertEqual(provider, "groq")
                self.assertEqual(model, "gpt-oss-20b")

    async def test_zero_hallucination_guardrail(self):
        """Agent must raise ValueError when attempting to assert non-existent evidence."""
        agent = LeadInvestigatorAgent(self.sample_manifest)
        # Existing item passes
        agent._assert_evidence_exists("ev-math-1")

        # Non-existent item raises
        with self.assertRaises(ValueError):
            agent._assert_evidence_exists("RULE_FABRICATED_FICTION")

    async def test_interactive_qa_bilingual(self):
        """Interactive Q&A answers queries in both English and Urdu citing verified evidence."""
        agent = LeadInvestigatorAgent(self.sample_manifest)

        # English query about balance
        resp_en = await agent.answer_query("Why is the balance tampered on row 4?")
        self.assertIn("discrepancies were identified", resp_en["answer"].lower())
        self.assertIn("ev-math-1", resp_en["evidence_references"])
        self.assertTrue(resp_en["tokens_used"] > 0)

        # Urdu query about risk
        resp_ur = await agent.answer_query("یہ دستاویز کیوں مسترد کی گئی اور اس کا رسک سکور کیا ہے؟")
        self.assertIn("CRITICAL", resp_ur["answer"])
        self.assertIn("خطرہ", resp_ur["answer"])
        self.assertTrue(len(resp_ur["evidence_references"]) > 0)

    async def test_authentic_clean_document_briefing(self):
        """A 100% authentic document yields Straight-Through Approval in English and Urdu."""
        clean_manifest = {
            "investigation": {"id": "clean-1", "caseNumber": "DT-CLEAN-01"},
            "documents": [{"originalFilename": "Authentic_Meezan.pdf", "sha256Hash": "abc123clean"}],
            "risk_assessment": {
                "overallScore": 0,
                "riskTier": "LOW",
                "actionDirective": "STRAIGHT_THROUGH_APPROVAL",
            },
            "evidence_items": [],
        }
        agent = LeadInvestigatorAgent(clean_manifest)
        res = await agent.analyze()

        self.assertEqual(res["overall_score"], 0)
        self.assertEqual(res["risk_tier"], "LOW")
        self.assertEqual(res["action_directive"], "STRAIGHT_THROUGH_APPROVAL")
        self.assertIn("Straight-Through Approval", res["english_summary"])
        self.assertIn("براہِ راست منظوری", res["urdu_summary"])

    async def test_passing_verification_check_segregation(self):
        """Test that passing checks (e.g. RULE_BANK_TEMPLATE_VERIFIED) are not listed as deficiencies."""
        manifest_with_passing_check = {
            "investigation": {
                "id": "inv-test-seg",
                "caseNumber": "DT-2026-TEST",
                "title": "Audit With Passing CBS Check",
            },
            "risk_assessment": {
                "overallScore": 65,
                "riskTier": "HIGH",
                "actionDirective": "MANUAL_SUPERVISOR_REVIEW",
            },
            "evidence_items": [
                {
                    "id": "ev-adverse-1",
                    "category": "MATHEMATICAL_MISMATCH",
                    "severity": "HIGH",
                    "ruleId": "RULE_PK_LEDGER_RECONCILIATION_FAIL",
                    "title": "Ledger Arithmetic Discrepancy",
                    "description": "Row 2 balance formula mismatch",
                    "expectedValue": "PKR 100,000",
                    "actualValue": "PKR 120,000",
                    "discrepancy": "PKR 20,000",
                    "pageNumber": 1,
                },
                {
                    "id": "ev-passing-cbs",
                    "category": "TRANSACTION_FORMAT_VIOLATION",
                    "severity": "INFO",
                    "ruleId": "RULE_BANK_TEMPLATE_VERIFIED",
                    "title": "CBS Reporting Template Verified (Meezan Bank Limited)",
                    "description": "Canonical Temenos T24 layout confirmed with 0 pt column drift across 5 columns, 1 fonts verified",
                    "expectedValue": "Canonical Temenos T24 Grid",
                    "actualValue": "100% Match (MEZN-001)",
                    "discrepancy": "0 pt column drift - Certified Authentic",
                    "pageNumber": 1,
                },
            ],
        }
        agent = LeadInvestigatorAgent(manifest_with_passing_check)
        res = await agent.analyze()

        # Deficiencies section must contain adverse item
        self.assertIn("Key Forensic Deficiencies Detected:", res["english_summary"])
        self.assertIn("Ledger Arithmetic Discrepancy", res["english_summary"])

        # Deficiencies section must NOT list CBS Reporting Template Verified as a deficiency
        deficiencies_part = res["english_summary"].split("Key Forensic Deficiencies Detected:")[1]
        if "Certified Authentic Controls:" in deficiencies_part:
            deficiencies_part, controls_part = deficiencies_part.split("Certified Authentic Controls:")
            self.assertIn("CBS Reporting Template Verified", controls_part)
        self.assertNotIn("CBS Reporting Template Verified", deficiencies_part)

        # Ensure no hallucinated font irregularity is added
        self.assertNotIn("Font irregularity identified", res["english_summary"])

        # Check credit_briefing list only includes adverse items
        self.assertEqual(len(res["credit_briefing"]), 1)

    async def test_interactive_qa_history_service(self):
        """Test retrieving interactive QA history with sequence sorting."""
        from app.features.agents.service import get_interactive_qa_history
        from datetime import datetime, timezone

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "sess-123"
        mock_session.modelProvider = "groq"
        mock_session.modelName = "llama-3.3-70b-versatile"
        mock_session.status = "active"

        m1 = MagicMock()
        m1.id = "msg-1"
        m1.role = "USER"
        m1.content = "What is the baseline offset?"
        m1.tokensIn = 6
        m1.tokensOut = 0
        m1.sequenceOrder = 1
        m1.createdAt = datetime.now(timezone.utc)

        m2 = MagicMock()
        m2.id = "msg-2"
        m2.role = "ASSISTANT"
        m2.content = "Sub-pixel typography offset of 2.50 pt detected."
        m2.tokensIn = 0
        m2.tokensOut = 85
        m2.sequenceOrder = 2
        m2.createdAt = datetime.now(timezone.utc)

        mock_session.messages = [m2, m1]  # Intentionally unsorted to verify sorting logic
        mock_db.agentsession.find_first = AsyncMock(return_value=mock_session)

        history = await get_interactive_qa_history(mock_db, "inv-test-123")
        self.assertEqual(history.session_id, "sess-123")
        self.assertEqual(history.model_provider, "groq")
        self.assertEqual(len(history.messages), 2)
        # Verify deterministic ascending order
        self.assertEqual(history.messages[0].id, "msg-1")
        self.assertEqual(history.messages[0].role, "USER")
        self.assertEqual(history.messages[1].id, "msg-2")
        self.assertEqual(history.messages[1].role, "ASSISTANT")


if __name__ == "__main__":
    unittest.main()

