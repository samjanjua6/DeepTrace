"""
Unit and Integration Tests for NADRA CNIC & Smart Card (SNIC) Verification Engine.
Verifies compliance with:
- NADRA Ordinance 2000 Section 30
- 13-digit CNIC administrative format (XXXXX-XXXXXXX-X)
- 1st-digit Provincial administrative decoding (1=KP, 2=FATA, 3=Punjab, 4=Sindh, 5=Balochistan, 6=Islamabad, 7=GB, 8=AJK)
- 13th-digit Gender parity invariant (Odd = Male, Even = Female)
- ICAO Doc 9303 Part 5 (TD1) 3-line Machine Readable Zone (MRZ) 7-3-1 modulus-10 checksum validation
- Front Visual Zone (VIZ) vs Reverse Optical MRZ cross-verification
- Swarm Agent & Bilingual Credit Briefing integration
"""
import pytest
from app.features.pipeline.tasks.nadra_cnic_verifier import (
    calculate_icao_check_digit,
    parse_cnic_raw,
    validate_cnic_structure,
    verify_gender_parity,
    parse_and_verify_snic_mrz,
    audit_cnic_dates,
    verify_identity_document,
    PROVINCE_CODES,
)
from app.features.agents.swarm.semantic_pk_agent import SemanticPKFinancialAgent
from app.features.agents.swarm.lead_investigator import (
    _build_structured_credit_briefing_items,
    _generate_deterministic_briefing,
)


def test_calculate_icao_check_digit():
    """Verify ICAO 9303 repeating [7, 3, 1] modulus 10 calculation."""
    # Data: "D23145890" -> 7*D(13)+3*2+1*3+7*1+3*4+1*5+7*8+3*9+1*0
    # 13*7 + 6 + 3 + 7 + 12 + 5 + 56 + 27 + 0 = 91 + 6 + 3 + 7 + 12 + 5 + 56 + 27 = 207 % 10 = 7
    check = calculate_icao_check_digit("D23145890")
    assert check == 7

    # Blank / '<' maps to 0
    assert calculate_icao_check_digit("<<<") == 0


def test_cnic_raw_parsing():
    """Verify raw and hyphenated CNIC string parsing."""
    res = parse_cnic_raw("35201-1234567-1")
    assert res is not None
    formatted, p1, p2, p3 = res
    assert formatted == "35201-1234567-1"
    assert p1 == "35201"
    assert p2 == "1234567"
    assert p3 == "1"

    # Raw 13 digits without hyphens
    res2 = parse_cnic_raw("4210198765432")
    assert res2 is not None
    assert res2[0] == "42101-9876543-2"

    # Invalid length
    assert parse_cnic_raw("35201-12345") is None
    assert parse_cnic_raw("abcdef1234567") is None


def test_cnic_province_codes_1_to_8():
    """Verify valid provinces (1-8) decode accurately under NADRA Ordinance 2000."""
    valid_test_cases = [
        ("17301-1234567-1", "1", "Khyber Pakhtunkhwa (KP)", "MALE"),
        ("21101-2345678-2", "2", "Federally Administered Tribal Areas (FATA / Merged Districts)", "FEMALE"),
        ("35201-3456789-1", "3", "Punjab", "MALE"),
        ("42101-4567890-2", "4", "Sindh", "FEMALE"),
        ("54400-5678901-1", "5", "Balochistan", "MALE"),
        ("61101-6789012-1", "6", "Islamabad Capital Territory (ICT)", "MALE"),
        ("71501-7890123-2", "7", "Gilgit-Baltistan (GB)", "FEMALE"),
        ("82201-8901234-1", "8", "Azad Jammu & Kashmir (AJK)", "MALE"),
    ]

    for cnic, expected_code, expected_name, expected_gender in valid_test_cases:
        res = validate_cnic_structure(cnic)
        assert res["is_valid"] is True, f"Failed for {cnic}: {res['errors']}"
        assert res["province_code"] == expected_code
        assert res["province_name"] == expected_name
        assert res["gender_parity"] == expected_gender
        assert len(res["errors"]) == 0


def test_invalid_cnic_province_codes():
    """Verify 0 and 9 flag as invalid non-existent provincial territories."""
    # Province code 0 does not exist
    res_0 = validate_cnic_structure("05201-1234567-1")
    assert res_0["is_valid"] is False
    assert any("0" in err for err in res_0["errors"])

    # Province code 9 does not exist
    res_9 = validate_cnic_structure("95201-1234567-1")
    assert res_9["is_valid"] is False
    assert any("9" in err for err in res_9["errors"])


def test_gender_parity_validation():
    """Verify odd=Male and even=Female parity invariants against declared customer sex/title."""
    # Male with Odd check digit -> Valid
    ok, reason, _ = verify_gender_parity("35201-1234567-1", "Male")
    assert ok is True
    assert "verified" in reason.lower()

    ok, reason, _ = verify_gender_parity("35201-1234567-3", "Mr. Tariq Khan")
    assert ok is True

    # Female with Even check digit -> Valid
    ok, reason, _ = verify_gender_parity("42101-1234567-2", "Female")
    assert ok is True

    ok, reason, _ = verify_gender_parity("42101-1234567-8", "Mrs. Fatima Zahra")
    assert ok is True

    # Male declared but Even check digit -> Mismatch!
    ok, reason, _ = verify_gender_parity("35201-1234567-2", "Mr. Asad Ali")
    assert ok is False
    assert "female" in reason.lower()

    # Female declared but Odd check digit -> Mismatch!
    ok, reason, _ = verify_gender_parity("42101-1234567-5", "Ms. Ayesha Siddiqa")
    assert ok is False
    assert "male" in reason.lower()


def test_snic_mrz_parsing_and_valid_checksum():
    """Verify Smart CNIC TD1 3-line MRZ parsing with authentic ICAO 9303 checksums."""
    # Construct a valid 3-line TD1 MRZ:
    # Line 1: I<PAK followed by 9-char doc number + check digit + 15 optional chars (<)
    doc_num = "123456789"
    doc_check = calculate_icao_check_digit(doc_num)
    line1 = f"I<PAK{doc_num}{doc_check}<<<<<<<<<<<<<<<"

    # Line 2: DOB (YYMMDD) + check + Sex (M/F) + Expiry (YYMMDD) + check + PAK + optional (11) + composite check
    dob = "900101"
    dob_check = calculate_icao_check_digit(dob)
    sex = "M"
    exp = "300101"
    exp_check = calculate_icao_check_digit(exp)
    nat = "PAK"
    opt_padded = "35201123456"

    # Composite check covers:
    # Line 1: chars 5-30 (doc_num + doc_check + optional) -> length 25
    # Line 2: chars 0-7 (dob + dob_check)
    # Line 2: chars 8-15 (exp + exp_check)
    # Line 2: chars 18-29 (optional)
    composite_data = (
        line1[5:30]
        + f"{dob}{dob_check}"
        + f"{exp}{exp_check}"
        + opt_padded
    )
    comp_check = calculate_icao_check_digit(composite_data)
    line2 = f"{dob}{dob_check}{sex}{exp}{exp_check}{nat}{opt_padded}{comp_check}"

    # Line 3: Name / Surname << Given Names
    line3 = "KHAN<<TARIQ<<<<<<<<<<<<<<<<<<<"

    mrz_lines = [line1, line2, line3]
    res = parse_and_verify_snic_mrz(mrz_lines)
    assert res["mrz_detected"] is True
    assert res["is_valid"] is True
    assert len(res["failures"]) == 0
    assert res["document_number"]["is_valid"] is True
    assert res["date_of_birth"]["is_valid"] is True
    assert res["expiry_date"]["is_valid"] is True
    assert res["composite_check"]["is_valid"] is True


def test_snic_mrz_tampered_checksum():
    """Verify modified digits in MRZ trigger ICAO Doc 9303 checksum failure."""
    line1 = "I<PAK1234567899<<<<<<<<<<<<<<<"  # Intentionally corrupt check digit
    line2 = "9001015M3001012PAK35201123456717"
    line3 = "KHAN<<TARIQ<<<<<<<<<<<<<<<<<<<"

    res = parse_and_verify_snic_mrz([line1, line2, line3])
    assert res["mrz_detected"] is True
    assert res["is_valid"] is False
    assert len(res["failures"]) > 0


def test_verify_identity_document_clean():
    """Verify clean identity document returns VERIFIED with RULE_CNIC_VERIFIED finding."""
    text = (
        "NATIONAL IDENTITY CARD\n"
        "ISLAMIC REPUBLIC OF PAKISTAN\n"
        "Name: Muhammad Tariq\n"
        "Father Name: Abdul Rehman\n"
        "Gender: Male\n"
        "Identity Number: 35201-1234567-1\n"
        "Date of Birth: 15.08.1985\n"
        "Date of Issue: 10.01.2018\n"
        "Date of Expiry: 10.01.2028\n"
    )
    res = verify_identity_document(all_text=text)
    assert res["overall_status"] == "VERIFIED"
    assert res["is_conforming"] is True
    assert res["primary_cnic"] == "35201-1234567-1"
    assert any(f["rule_id"] == "RULE_CNIC_VERIFIED" for f in res["findings"])


def test_verify_identity_document_tampered_province():
    """Verify non-existent province code returns TAMPERED and RULE_CNIC_PROVINCE_CODE_INVALID."""
    text = (
        "NATIONAL IDENTITY CARD\n"
        "Identity Number: 05201-1234567-1\n"
        "Gender: Male\n"
    )
    res = verify_identity_document(all_text=text)
    assert res["overall_status"] == "TAMPERED"
    assert any(f["rule_id"] == "RULE_CNIC_PROVINCE_CODE_INVALID" for f in res["findings"])


def test_verify_identity_document_gender_mismatch():
    """Verify contradiction between declared gender and terminal parity returns CRITICAL finding."""
    text = (
        "NATIONAL IDENTITY CARD\n"
        "Title: Mr. Tariq Khan\n"
        "Gender: Male\n"
        "Identity Number: 35201-1234567-2\n"
    )
    res = verify_identity_document(all_text=text)
    assert res["overall_status"] == "TAMPERED"
    assert any(f["rule_id"] == "RULE_CNIC_GENDER_PARITY_MISMATCH" for f in res["findings"])


@pytest.mark.asyncio
async def test_swarm_semantic_pk_agent_cnic_integration():
    """Verify SemanticPKFinancialAgent ingests RULE_CNIC_ findings and raises critical indicators."""
    evidence_manifest = {
        "evidence_items": [
            {
                "id": "ev-cnic-1",
                "category": "TRANSACTION_FORMAT_VIOLATION",
                "severity": "CRITICAL",
                "ruleId": "RULE_CNIC_PROVINCE_CODE_INVALID",
                "riskPoints": 50,
                "title": "Invalid Pakistani CNIC Province Code",
                "description": "Province code 9 does not exist under NADRA schema.",
                "discrepancy": "Non-existent province code 9",
            },
            {
                "id": "ev-cnic-2",
                "category": "TRANSACTION_FORMAT_VIOLATION",
                "severity": "CRITICAL",
                "ruleId": "RULE_CNIC_GENDER_PARITY_MISMATCH",
                "riskPoints": 60,
                "title": "CNIC Gender Parity Contradiction",
                "description": "Declared male with even check digit.",
                "discrepancy": "Gender parity contradiction",
            },
        ],
        "risk_assessment": {"overallScore": 85, "riskTier": "CRITICAL"},
    }

    agent = SemanticPKFinancialAgent(
        evidence_manifest=evidence_manifest,
    )
    result = await agent.analyze()
    assert result["anomalies_detected"] == 2
    assert any("provincial administrative coding" in ind for ind in result["key_indicators"])
    assert any("gender parity contradicts" in ind for ind in result["key_indicators"])


def test_lead_investigator_bilingual_cnic_briefing():
    """Verify bilingual English and Urdu credit briefings include statutory NADRA citations."""
    items = [
        {
            "pageNumber": 1,
            "title": "Invalid Pakistani CNIC Province Code: 95201-1234567-1",
            "ruleId": "RULE_CNIC_PROVINCE_CODE_INVALID",
            "severity": "CRITICAL",
            "description": "Province code 9 violates NADRA Ordinance 2000 Section 30.",
            "discrepancy": "Invalid province code 9",
        },
        {
            "pageNumber": 1,
            "title": "CNIC Gender Parity Mismatch",
            "ruleId": "RULE_CNIC_GENDER_PARITY_MISMATCH",
            "severity": "CRITICAL",
            "description": "Check digit indicates female while account holder title is Mr.",
            "discrepancy": "Gender parity contradiction",
        },
    ]

    briefing_items = _build_structured_credit_briefing_items(items)
    assert len(briefing_items) == 2

    # Check Urdu translation contains NADRA references
    assert "نادرا" in briefing_items[0]["summary_ur"]
    assert "صوبائی کوڈ" in briefing_items[0]["summary_ur"]
    assert "جنس" in briefing_items[1]["summary_ur"]
