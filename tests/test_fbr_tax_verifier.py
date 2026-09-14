"""
Tests for Federal Board of Revenue (FBR) Tax Verification,
National Tax Number (NTN) Modulus 11 Check Digit Validation,
Section 149 Income Tax Ordinance 2001 Salaried Progressive Tax Slabs,
and Computerized Payment Receipt (CPR) Verification.
"""
from decimal import Decimal
import pytest

from app.features.pipeline.tasks.fbr_tax_verifier import (
    calculate_ntn_check_digit,
    validate_ntn_structure,
    calculate_expected_salary_wht,
    verify_salary_slip_tax,
    validate_cpr_structure,
    audit_fbr_tax_compliance,
)
from app.features.agents.swarm.semantic_pk_agent import SemanticPKFinancialAgent
from app.features.agents.swarm.lead_investigator import LeadInvestigatorAgent


class TestNTNValidation:
    """Test FBR National Tax Number (NTN) Modulus 11 Checksum and Individual CNIC routing."""

    def test_valid_corporate_ntn_pso(self):
        """Test legitimate Pakistan State Oil (PSO) NTN 0710008-6."""
        res = validate_ntn_structure("0710008-6")
        assert res.is_valid is True
        assert res.formatted_ntn == "0710008-6"
        assert res.check_digit == "6"
        assert res.calculated_check_digit == "6"
        assert res.ntn_type == "CORPORATE_AOP"

    def test_invalid_corporate_ntn_check_digit(self):
        """Test altered check digit for PSO (0710008-2 instead of -6)."""
        res = validate_ntn_structure("0710008-2")
        assert res.is_valid is False
        assert res.check_digit == "2"
        assert res.calculated_check_digit == "6"
        assert "Modulus 11 check digit failure" in res.reason

    def test_valid_individual_cnic_ntn(self):
        """Test individual taxpayer NTN routed to 13-digit CNIC under Section 181."""
        res = validate_ntn_structure("35201-1234567-1")
        assert res.is_valid is True
        assert res.ntn_type == "INDIVIDUAL_CNIC"
        assert res.formatted_ntn == "35201-1234567-1"

    def test_invalid_ntn_format(self):
        """Test non-compliant NTN strings."""
        res = validate_ntn_structure("12345")
        assert res.is_valid is False
        assert "does not conform" in res.reason

    def test_modulus_11_calculation_edge_cases(self):
        """Test calculate_ntn_check_digit with non-7-digit input."""
        assert calculate_ntn_check_digit("1234") is None
        assert calculate_ntn_check_digit("abcdefg") is None


class TestSection149SalaryTaxSlabs:
    """Test statutory tax calculations under Section 149 & First Schedule Division I."""

    def test_slab_1_tax_exempt_under_50k(self):
        """Gross PKR 45,000/mo (Annual PKR 540,000) has 0% tax."""
        res = calculate_expected_salary_wht(Decimal("45000"), tax_year=2025)
        assert res["is_taxable"] is False
        assert res["annual_tax"] == Decimal("0")
        assert res["monthly_tax"] == Decimal("0")
        assert "Slab 1" in res["slab_name"]

    def test_slab_2_5_percent_excess_over_600k(self):
        """Gross PKR 100,000/mo (Annual PKR 1,200,000). Tax = 5% of 600,000 = PKR 30,000/yr -> PKR 2,500/mo."""
        res = calculate_expected_salary_wht(Decimal("100000"), tax_year=2025)
        assert res["is_taxable"] is True
        assert res["annual_tax"] == Decimal("30000")
        assert res["monthly_tax"] == Decimal("2500.00")
        assert "Slab 2" in res["slab_name"]

    def test_slab_3_15_percent_excess_over_1_2m(self):
        """Gross PKR 150,000/mo (Annual PKR 1,800,000). Tax = 30k + 15% of 600k = PKR 120,000/yr -> PKR 10,000/mo."""
        res = calculate_expected_salary_wht(Decimal("150000"), tax_year=2025)
        assert res["annual_tax"] == Decimal("120000")
        assert res["monthly_tax"] == Decimal("10000.00")
        assert "Slab 3" in res["slab_name"]

    def test_slab_4_25_percent_excess_over_2_2m(self):
        """Gross PKR 250,000/mo (Annual PKR 3,000,000). Tax = 180k + 25% of 800k = PKR 380,000/yr -> PKR 31,666.67/mo."""
        res = calculate_expected_salary_wht(Decimal("250000"), tax_year=2025)
        assert res["annual_tax"] == Decimal("380000")
        assert res["monthly_tax"] == Decimal("31666.67")
        assert "Slab 4" in res["slab_name"]

    def test_slab_6_highest_bracket(self):
        """Gross PKR 500,000/mo (Annual PKR 6,000,000). Tax = 700k + 35% of 1.9M = PKR 1,365,000/yr -> PKR 113,750/mo."""
        res = calculate_expected_salary_wht(Decimal("500000"), tax_year=2025)
        assert res["annual_tax"] == Decimal("1365000")
        assert res["monthly_tax"] == Decimal("113750.00")
        assert "Slab 6" in res["slab_name"]

    def test_prior_tax_year_2024_slabs(self):
        """Tax Year 2024 had 2.5% for Slab 2."""
        res = calculate_expected_salary_wht(Decimal("100000"), tax_year=2024)
        assert res["annual_tax"] == Decimal("15000")
        assert res["monthly_tax"] == Decimal("1250.00")


class TestSalarySlipTaxVerification:
    """Test salary slip verification and rule generation."""

    def test_zero_tax_on_taxable_salary_violation(self):
        """PKR 150,000 gross salary with ZERO declared tax triggers CRITICAL rule."""
        res = verify_salary_slip_tax(
            monthly_gross=Decimal("150000"),
            declared_wht=Decimal("0"),
            tax_year=2025,
        )
        assert res["status"] == "ZERO_TAX_VIOLATION"
        assert res["is_compliant"] is False
        assert any(f["rule_id"] == "RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY" for f in res["findings"])

    def test_under_deduction_discrepancy(self):
        """Expected PKR 10,000, declared PKR 4,000 triggers HIGH discrepancy rule."""
        res = verify_salary_slip_tax(
            monthly_gross=Decimal("150000"),
            declared_wht=Decimal("4000"),
            tax_year=2025,
        )
        assert res["status"] == "DISCREPANCY"
        assert any(f["rule_id"] == "RULE_FBR_WHT_DISCREPANCY" for f in res["findings"])

    def test_compliant_salary_slip(self):
        """Expected PKR 10,000, declared PKR 10,000 triggers VERIFIED rule."""
        res = verify_salary_slip_tax(
            monthly_gross=Decimal("150000"),
            declared_wht=Decimal("10000"),
            tax_year=2025,
        )
        assert res["status"] == "COMPLIANT"
        assert res["is_compliant"] is True
        assert any(f["rule_id"] == "RULE_FBR_WHT_VERIFIED" for f in res["findings"])

    def test_below_threshold_zero_tax_compliant(self):
        """PKR 45,000 gross salary with 0 tax is legally compliant."""
        res = verify_salary_slip_tax(
            monthly_gross=Decimal("45000"),
            declared_wht=Decimal("0"),
            tax_year=2025,
        )
        assert res["status"] == "COMPLIANT"
        assert res["is_compliant"] is True
        assert any(f["rule_id"] == "RULE_FBR_WHT_VERIFIED" for f in res["findings"])


class TestCPRVerification:
    """Test Computerized Payment Receipt (CPR) checks."""

    def test_valid_income_tax_cpr(self):
        res = validate_cpr_structure("IT-20240915-0012-3456789")
        assert res.is_valid is True
        assert res.cpr_type == "INCOME_TAX_CPR"
        assert res.is_future_dated is False

    def test_future_dated_cpr(self):
        res = validate_cpr_structure("IT-20991231-0012-3456789")
        assert res.is_future_dated is True
        assert "post-dated" in res.reason

    def test_invalid_cpr_format(self):
        res = validate_cpr_structure("INVALID-RECEIPT-XYZ")
        assert res.is_valid is False
        assert "does not match standard" in res.reason


class TestAuditFbrTaxCompliance:
    """Test end-to-end text audit orchestrator."""

    def test_extract_and_audit_from_salary_slip_text(self):
        doc_text = (
            "FAUJI FERTILIZER COMPANY LIMITED\n"
            "SALARY SLIP FOR AUGUST 2024\n"
            "Employer NTN: 0710008-6\n"
            "Employee Name: Muhammad Bilal\n"
            "Gross Pay: PKR 150,000\n"
            "Income Tax / WHT: PKR 0\n"
            "Net Pay: PKR 150,000\n"
        )
        audit = audit_fbr_tax_compliance(doc_text, doc_type="SALARY_SLIP")
        assert audit["overall_status"] == "TAX_EVASION_SUSPECTED"
        assert audit["ntn_result"]["is_valid"] is True
        assert audit["wht_audit"]["status"] == "ZERO_TAX_VIOLATION"
        assert len(audit["findings"]) >= 1


class TestSwarmFbrTaxIntegration:
    """Test Multi-Agent Swarm integration for FBR tax rules."""

    @pytest.mark.asyncio
    async def test_semantic_pk_agent_ingests_fbr_rules(self):
        manifest = {
            "evidence_items": [
                {
                    "id": "ev-fbr-1",
                    "ruleId": "RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY",
                    "severity": "CRITICAL",
                    "riskPoints": 60,
                    "title": "FBR Tax Violation: Zero Tax on Taxable Salary",
                    "description": "Salary PKR 150,000 exceeds threshold with 0 WHT.",
                }
            ],
            "risk_assessment": {"overallScore": 60, "riskTier": "HIGH", "actionDirective": "HALT_APPLICATION"},
        }
        agent = SemanticPKFinancialAgent(manifest)
        res = await agent.analyze()
        assert res["anomalies_detected"] == 1
        assert any("PKR 50,000/mo threshold but declares ZERO withholding tax" in ind for ind in res["key_indicators"])

    @pytest.mark.asyncio
    async def test_lead_investigator_qa_answering_fbr(self):
        manifest = {
            "evidence_items": [
                {
                    "id": "ev-fbr-1",
                    "ruleId": "RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY",
                    "severity": "CRITICAL",
                    "riskPoints": 60,
                    "title": "FBR Tax Violation: Zero Tax on Taxable Salary",
                    "description": "Salary PKR 150,000 exceeds statutory PKR 50,000 threshold with zero withholding tax.",
                }
            ],
            "risk_assessment": {"overallScore": 60, "riskTier": "HIGH", "actionDirective": "HALT_APPLICATION"},
        }
        agent = LeadInvestigatorAgent(manifest)

        # English query
        ans_en = await agent.answer_query("Does this salary slip comply with FBR tax and Section 149 WHT?")
        assert "Federal Board of Revenue (FBR) Tax" in ans_en["answer"]
        assert "ev-fbr-1" in ans_en["evidence_references"]

        # Urdu query
        ans_ur = await agent.answer_query("کیا اس دستاویز پر ایف بی آر ٹیکس کٹوتی درست ہے؟")
        assert "ایف بی آر" in ans_ur["answer"]
        assert "ev-fbr-1" in ans_ur["evidence_references"]
