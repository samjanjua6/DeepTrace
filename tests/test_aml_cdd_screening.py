"""
Unit and Integration Tests for SBP AML/CFT & Customer Due Diligence (CDD) Screening Engine.
Verifies compliance with:
- NACTA 4th Schedule (Anti-Terrorism Act 1997 §11EE)
- UN Security Council 1267 / 1988 Sanctions Lists
- Politically Exposed Persons (PEPs) under SBP BPRD Circular No. 1 of 2021
- Hawala / Hundi / Trade Structuring Detection (SBP BPRD Circular No. 3 of 2018)
"""
import pytest
from app.features.pipeline.tasks.aml_screening_engine import (
    normalize_tokens_for_screening,
    compute_name_match_score,
    extract_customer_credentials_from_text,
    screen_entity_against_sanctions,
    scan_transaction_narrations,
    perform_sbp_cdd_screening,
)
from app.features.agents.swarm.semantic_pk_agent import SemanticPKFinancialAgent
from app.features.agents.swarm.lead_investigator import (
    _build_structured_credit_briefing_items,
    _generate_deterministic_briefing,
)


def test_name_normalization():
    """Test South Asian honorific stripping and transliteration normalization."""
    tokens1 = normalize_tokens_for_screening("Hafiz Muhammad Saeed")
    assert "hafiz" not in tokens1
    assert "muhammad" in tokens1
    assert "saeed" in tokens1

    tokens2 = normalize_tokens_for_screening("Moulana Masood Azhar")
    assert "moulana" not in tokens2
    assert "masood" in tokens2
    assert "azhar" in tokens2

    # Transliteration aliases
    tokens3 = normalize_tokens_for_screening("Mohd Ahmad Choudhry")
    assert "muhammad" in tokens3
    assert "ahmed" in tokens3
    assert "chaudhry" in tokens3


def test_token_subset_and_exact_match():
    """Verify dual-score matching achieves high confidence on token subsets."""
    # Token subset (e.g. "Muhammad Saeed" in "Muhammad Saeed Khan")
    score, match_type = compute_name_match_score("Muhammad Saeed", "Muhammad Saeed Khan")
    assert score >= 0.96
    assert match_type == "TOKEN_SUBSET"

    # Exact normalized match (honorific stripped)
    score2, match_type2 = compute_name_match_score("Muhammad Saeed", "Hafiz Muhammad Saeed")
    assert score2 == 1.0
    assert match_type2 == "EXACT_NORMALIZED"

    # Exact normalized match with all tokens
    score3, match_type3 = compute_name_match_score("Imran Ahmed Khan Niazi", "Imran Ahmed Khan Niazi")
    assert score3 == 1.0
    assert match_type3 == "EXACT_NORMALIZED"

    # Unrelated names
    score4, match_type4 = compute_name_match_score("Tariq Mehmood", "Hafiz Muhammad Saeed")
    assert score4 < 0.60


def test_nacta_proscribed_screening():
    """Verify screening detects NACTA 4th Schedule designated individuals and entities."""
    # Individual hit
    hits = screen_entity_against_sanctions("Hafiz Muhammad Saeed")
    assert len(hits) >= 1
    hit = next(h for h in hits if h["list_type"] == "NACTA_4TH_SCHEDULE")
    assert hit["severity"] == "CRITICAL"
    assert hit["risk_points"] == 100
    assert "11EE" in hit["statutory_reference"]
    assert hit["action_directive"] == "MANDATORY_STR_AND_ACCOUNT_FREEZE"

    # Entity hit
    hits_ent = screen_entity_against_sanctions("Tehrik-e-Taliban Pakistan")
    assert len(hits_ent) >= 1
    hit_ent = next(h for h in hits_ent if h["list_type"] == "NACTA_PROSCRIBED_ORGANIZATION")
    assert hit_ent["severity"] == "CRITICAL"
    assert hit_ent["risk_points"] == 100


def test_unsc_1267_sanctions_screening():
    """Verify screening detects UN Security Council Resolution 1267 sanctioned terrorists."""
    hits = screen_entity_against_sanctions("Zaki-ur-Rehman Lakhvi")
    assert len(hits) >= 1
    unsc_hit = next(h for h in hits if h["list_type"] == "UNSC_1267_SANCTIONS")
    assert unsc_hit["severity"] == "CRITICAL"
    assert unsc_hit["risk_points"] == 100
    assert unsc_hit["unsc_id"] == "QDi.264"
    assert unsc_hit["action_directive"] == "MANDATORY_ASSET_FREEZE_UNSC_ACT_1948"


def test_pep_screening():
    """Verify screening identifies Politically Exposed Persons (PEPs) under SBP BPRD."""
    hits = screen_entity_against_sanctions("Mian Muhammad Shehbaz Sharif")
    assert len(hits) >= 1
    pep_hit = next(h for h in hits if h["list_type"] == "PEP_REGISTRY")
    assert pep_hit["severity"] == "HIGH"
    assert pep_hit["risk_points"] == 35
    assert "Prime Minister" in pep_hit["public_office"]
    assert pep_hit["action_directive"] == "SENIOR_MANAGEMENT_APPROVAL_AND_EDD_REQUIRED"


def test_clean_customer_screening():
    """Verify legitimate ordinary citizens trigger zero false positives."""
    hits = screen_entity_against_sanctions("Sajjad Hussain Malik")
    # Neither in NACTA, UNSC, nor PEP registries
    assert len([h for h in hits if h["match_score"] >= 0.88]) == 0


def test_hawala_hundi_narration_scan():
    """Verify detection of informal value transfer and crypto red flags in ledger narrations."""
    txs = [
        {"row_number": 1, "particulars": "Salary Transfer from Tech Corp", "amount": 250000},
        {"row_number": 2, "particulars": "Payment for Hawala settlement via Dubai chitti", "amount": 1500000},
        {"row_number": 3, "particulars": "Utility Bill K-Electric online", "amount": 12500},
        {"row_number": 4, "particulars": "Binance P2P USDT liquidation", "amount": 800000},
    ]
    flags = scan_transaction_narrations(txs)
    assert len(flags) == 2
    terms = [f["matched_term"].lower() for f in flags]
    assert "hawala" in terms
    assert "usdt" in terms or "binance p2p" in terms


def test_perform_sbp_cdd_screening_proscribed_case():
    """End-to-end test of perform_sbp_cdd_screening with proscribed individual."""
    statement_text = """
    Meezan Bank Limited
    Account Title: Hafiz Muhammad Saeed
    Account No: 0101-0203040506
    IBAN: PK67 MEZN 0001 0102 0304 0506
    CNIC: 35201-1234567-1
    """
    res = perform_sbp_cdd_screening(statement_text, transactions=[])
    assert res["overall_status"] == "PROSCRIBED_MATCH"
    assert res["nacta_match"] is True
    assert res["action_directive"] == "MANDATORY_STR_AND_ACCOUNT_FREEZE"
    assert len(res["findings"]) >= 1
    finding = res["findings"][0]
    assert finding["rule_id"] == "RULE_AML_NACTA_PROSCRIBED_MATCH"
    assert finding["severity"] == "CRITICAL"
    assert finding["risk_points"] == 100


def test_perform_sbp_cdd_screening_clean_case():
    """End-to-end test of perform_sbp_cdd_screening with clean customer."""
    statement_text = """
    Habib Bank Limited
    Account Title: Tariq Mehmood Chaudhry
    Account No: 0042-7901234567
    IBAN: PK36 HABB 0000 4279 0123 4567
    """
    res = perform_sbp_cdd_screening(statement_text, transactions=[])
    assert res["overall_status"] == "CLEARED"
    assert res["nacta_match"] is False
    assert res["unsc_match"] is False
    assert res["pep_detected"] is False
    assert res["action_directive"] == "STANDARD_CUSTOMER_DUE_DILIGENCE_CONFIRMED"
    assert len(res["findings"]) == 1
    assert res["findings"][0]["rule_id"] == "RULE_AML_CDD_CLEARED"
    assert res["findings"][0]["severity"] == "INFO"
    assert res["findings"][0]["risk_points"] == 0


@pytest.mark.asyncio
async def test_semantic_pk_agent_aml_integration():
    """Test SemanticPKFinancialAgent ingests RULE_AML_ findings and emits indicators."""
    evidence_manifest = {
        "evidence_items": [
            {
                "id": "ev-aml-1",
                "ruleId": "RULE_AML_NACTA_PROSCRIBED_MATCH",
                "category": "TRANSACTION_FORMAT_VIOLATION",
                "severity": "CRITICAL",
                "riskPoints": 100,
                "title": "NACTA 4th Schedule Proscribed Match",
                "description": "Account title matches proscribed individual.",
                "pageNumber": 1,
            }
        ]
    }
    agent = SemanticPKFinancialAgent(evidence_manifest)
    res = await agent.analyze()
    assert res["anomalies_detected"] == 1
    assert any("NACTA" in ind for ind in res["key_indicators"])
    assert any("freeze" in ind.lower() for ind in res["key_indicators"])


def test_lead_investigator_briefing_aml_urdu():
    """Verify Lead Investigator formats authentic Urdu briefing for AML findings."""
    evidence_items = [
        {
            "id": "ev-aml-nacta",
            "ruleId": "RULE_AML_NACTA_PROSCRIBED_MATCH",
            "severity": "CRITICAL",
            "title": "NACTA 4th Schedule Match",
            "description": "Matches designated individual.",
            "pageNumber": 1,
            "rowNumber": 1,
        }
    ]
    briefing_items = _build_structured_credit_briefing_items(evidence_items)
    assert len(briefing_items) == 1
    item = briefing_items[0]
    # Urdu briefing must reference NACTA and Section 11EE
    assert "نیکٹا" in item["summary_ur"]
    assert "11EE" in item["summary_ur"]
    assert "اکاؤنٹ منجمد" in item["summary_ur"]
