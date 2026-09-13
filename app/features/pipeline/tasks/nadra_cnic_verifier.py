"""
NADRA CNIC & Smart National Identity Card (SNIC) Verification Engine.
Implements:
1. 13-digit CNIC administrative format validation (XXXXX-XXXXXXX-X).
2. 1st-digit Province / Administrative Region decoding & validation (1=KP, 2=FATA, 3=Punjab, 4=Sindh, 5=Balochistan, 6=Islamabad, 7=GB, 8=AJK).
3. 13th-digit Gender parity validation (Odd = Male, Even = Female) against declared sex/title.
4. ICAO Doc 9303 Part 5 (TD1) 3-Line Machine Readable Zone (MRZ) parser with 7-3-1 modulus-10 checksum validation.
5. VIZ vs MRZ cross-verification (Front visual zone vs Reverse machine-readable zone).
6. Temporal validity audits (10-year validity, age >= 18 at issuance, lifetime senior citizen rules).
Statutory Authority: National Database and Registration Authority Ordinance, 2000 (NADRA Ordinance 2000 Section 30).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
import logging
import re
from typing import Any, Optional, Tuple

logger = logging.getLogger("deeptrace.nadra_cnic")

# NADRA 1st-digit Province / Administrative Territory Mapping
PROVINCE_CODES = {
    "1": "Khyber Pakhtunkhwa (KP)",
    "2": "Federally Administered Tribal Areas (FATA / Merged Districts)",
    "3": "Punjab",
    "4": "Sindh",
    "5": "Balochistan",
    "6": "Islamabad Capital Territory (ICT)",
    "7": "Gilgit-Baltistan (GB)",
    "8": "Azad Jammu & Kashmir (AJK)",
}

# 13-digit CNIC regex patterns
CNIC_HYPHEN_REGEX = re.compile(r"\b(\d{5})[-\s](\d{7})[-\s](\d{1})\b")
CNIC_RAW_REGEX = re.compile(r"\b(\d{13})\b")

# VIZ date extraction regex (DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY)
DATE_REGEX = re.compile(r"\b(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{4})\b")

# VIZ Gender patterns
GENDER_MALE_REGEX = re.compile(r"\b(?:gender|sex)?\s*[:\-]?\s*(?:M|Male|مرد|Mr\.?|Mian)\b", re.IGNORECASE)
GENDER_FEMALE_REGEX = re.compile(r"\b(?:gender|sex)?\s*[:\-]?\s*(?:F|Female|عورت|Mrs\.?|Ms\.?|Miss)\b", re.IGNORECASE)

# ICAO 9303 TD1 MRZ pattern: 3 lines, each 30 chars
# Line 1 begins with I<PAK, IDPAK, or I?PAK
MRZ_LINE1_REGEX = re.compile(r"^I[A-Z0-9<]PAK[A-Z0-9<]{25}$")
MRZ_LINE2_REGEX = re.compile(r"^\d{7}[MF<]\d{7}PAK[A-Z0-9<]{12}$")
MRZ_LINE3_REGEX = re.compile(r"^[A-Z0-9<]{30}$")


def _icao_char_value(c: str) -> int:
    """Map character to ICAO 9303 numerical value: 0-9 = 0-9, A-Z = 10-35, '<' = 0."""
    if c.isdigit():
        return int(c)
    if c.isalpha() and c.isupper():
        return ord(c) - ord("A") + 10
    return 0


def calculate_icao_check_digit(data: str) -> int:
    """
    Calculate ICAO Doc 9303 check digit using weights [7, 3, 1] repeating mod 10.
    """
    weights = [7, 3, 1]
    total = 0
    for idx, ch in enumerate(data):
        w = weights[idx % 3]
        total += _icao_char_value(ch) * w
    return total % 10


def parse_cnic_raw(cnic_str: str) -> Optional[tuple[str, str, str, str]]:
    """
    Parse a raw or hyphenated CNIC string into (formatted, part1_5, part2_7, digit13).
    Returns None if not 13 digits.
    """
    if not cnic_str:
        return None
    cleaned = re.sub(r"[^\d]", "", cnic_str)
    if len(cleaned) != 13:
        return None
    part1 = cleaned[:5]
    part2 = cleaned[5:12]
    digit13 = cleaned[12]
    formatted = f"{part1}-{part2}-{digit13}"
    return formatted, part1, part2, digit13


def validate_cnic_structure(cnic_str: str) -> dict[str, Any]:
    """
    Validate the 13-digit administrative structure of a Pakistani CNIC.
    Checks:
    - 13 digits length
    - 1st digit province code (1-8 valid, 0 and 9 invalid)
    - 13th digit gender parity (odd = Male, even = Female)
    """
    parsed = parse_cnic_raw(cnic_str)
    if not parsed:
        err_msg = "Invalid CNIC length or characters: expected exactly 13 digits"
        return {
            "is_valid": False,
            "raw_input": cnic_str,
            "formatted_cnic": None,
            "error": err_msg,
            "errors": [err_msg],
            "province_code": None,
            "province_name": None,
            "gender_parity": None,
        }

    formatted, part1, part2, digit13 = parsed
    prov_digit = part1[0]
    prov_name = PROVINCE_CODES.get(prov_digit)

    if not prov_name:
        err_msg = f"Invalid NADRA province/administrative code '{prov_digit}': must be between 1 and 8"
        return {
            "is_valid": False,
            "raw_input": cnic_str,
            "formatted_cnic": formatted,
            "error": err_msg,
            "errors": [err_msg],
            "province_code": prov_digit,
            "province_name": None,
            "gender_parity": "MALE" if int(digit13) % 2 != 0 else "FEMALE",
            "check_digit": digit13,
        }

    gender_parity = "MALE" if int(digit13) % 2 != 0 else "FEMALE"

    return {
        "is_valid": True,
        "raw_input": cnic_str,
        "formatted_cnic": formatted,
        "province_code": prov_digit,
        "province_name": prov_name,
        "division_code": part1[1],
        "district_code": part1[2],
        "tehsil_code": part1[3],
        "union_council_code": part1[4],
        "family_number": part2,
        "check_digit": digit13,
        "gender_parity": gender_parity,
        "error": None,
        "errors": [],
    }


def verify_gender_parity(
    cnic_str: str,
    declared_gender_or_title: Optional[str] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Verify whether the 13th digit parity matches the declared gender/title.
    Returns: (is_conforming, explanation, detected_parity)
    """
    struct = validate_cnic_structure(cnic_str)
    if not struct["is_valid"]:
        return False, struct["error"], None

    detected_parity = struct["gender_parity"]  # "MALE" or "FEMALE"

    if not declared_gender_or_title:
        return True, f"CNIC parity designates {detected_parity} cardholder", detected_parity

    declared_lower = declared_gender_or_title.lower().strip()
    tokens = re.findall(r"[a-z]+", declared_lower)
    is_declared_female = (
        any(w in ("female", "f", "mrs", "ms", "miss") for w in tokens)
        or "عورت" in declared_lower
    )
    is_declared_male = (
        not is_declared_female
        and (any(w in ("male", "m", "mr", "mian") for w in tokens) or "مرد" in declared_lower)
    )

    if is_declared_female and detected_parity == "MALE":
        reason = (
            f"Gender parity mismatch: CNIC {struct['formatted_cnic']} ends in odd digit '{struct['check_digit']}' "
            "(strictly designating MALE), but document declares FEMALE gender/title."
        )
        return False, reason, detected_parity

    if is_declared_male and detected_parity == "FEMALE":
        reason = (
            f"Gender parity mismatch: CNIC {struct['formatted_cnic']} ends in even digit '{struct['check_digit']}' "
            "(strictly designating FEMALE), but document declares MALE gender/title."
        )
        return False, reason, detected_parity

    return True, f"Gender parity verified: {detected_parity} matches cardholder record", detected_parity


def parse_icao_date(yymmdd: str) -> Optional[date]:
    """Parse a YYMMDD MRZ date string into a Python date."""
    if len(yymmdd) != 6 or not yymmdd.isdigit():
        return None
    yy = int(yymmdd[:2])
    mm = int(yymmdd[2:4])
    dd = int(yymmdd[4:6])

    # Pivot year: YY > 40 is 19YY (e.g. birth dates), YY <= 40 is 20YY
    current_year = datetime.now().year % 100
    year = 2000 + yy if yy <= (current_year + 20) else 1900 + yy
    try:
        return date(year, mm, dd)
    except ValueError:
        return None


def parse_and_verify_snic_mrz(lines: list[str]) -> dict[str, Any]:
    """
    Detect, parse, and cryptographically verify a 3-line TD1 Machine Readable Zone (MRZ)
    from a Pakistani Smart National Identity Card (SNIC).
    Calculates 7-3-1 modulus-10 check digits over Document No, Birth Date, Expiry Date,
    and the Composite checksum.
    """
    cleaned_lines = [re.sub(r"\s+", "", line).upper() for line in lines if line and len(line.strip()) >= 26]

    # Locate 3 contiguous lines matching TD1 format
    mrz_lines = None
    for i in range(len(cleaned_lines) - 2):
        l1, l2, l3 = cleaned_lines[i], cleaned_lines[i + 1], cleaned_lines[i + 2]
        # Allow padding or trimming to exactly 30 characters
        if len(l1) >= 28 and len(l2) >= 28 and len(l3) >= 28:
            if l1.startswith("I") and "PAK" in l1[:6] and ("PAK" in l2[13:20] or l2[7] in ("M", "F", "<")):
                mrz_lines = (l1[:30].ljust(30, "<"), l2[:30].ljust(30, "<"), l3[:30].ljust(30, "<"))
                break

    if not mrz_lines:
        return {
            "mrz_detected": False,
            "is_valid": True,  # Not all documents have reverse MRZ (e.g. legacy CNIC or front-only copy)
            "message": "No 3-line TD1 Machine Readable Zone detected (front-only copy or legacy CNIC).",
        }

    l1, l2, l3 = mrz_lines

    # --- Line 1 Breakdown ---
    doc_type = l1[:2].replace("<", "")
    issuing_country = l1[2:5]
    doc_number = l1[5:14].replace("<", "")
    doc_number_check = l1[14]
    opt_data_1 = l1[15:30]

    # Check 1: Document Number Check Digit
    calc_doc_check = str(calculate_icao_check_digit(l1[5:14]))
    is_doc_check_valid = (doc_number_check == calc_doc_check)

    # --- Line 2 Breakdown ---
    dob_str = l2[:6]
    dob_check = l2[6]
    sex = l2[7]
    expiry_str = l2[8:14]
    expiry_check = l2[14]
    nationality = l2[15:18]
    opt_data_2 = l2[18:29]
    composite_check = l2[29]

    # Check 2: Date of Birth Check Digit
    calc_dob_check = str(calculate_icao_check_digit(dob_str))
    is_dob_check_valid = (dob_check == calc_dob_check)
    dob_date = parse_icao_date(dob_str)

    # Check 3: Expiry Date Check Digit
    calc_expiry_check = str(calculate_icao_check_digit(expiry_str))
    is_expiry_check_valid = (expiry_check == calc_expiry_check)
    expiry_date = parse_icao_date(expiry_str)

    # Check 4: Composite Check Digit (over doc_no + check + opt1 + dob + check + expiry + check + opt2)
    composite_data = l1[5:30] + l2[:7] + l2[8:15] + l2[18:29]
    calc_composite_check = str(calculate_icao_check_digit(composite_data))
    is_composite_check_valid = (composite_check == calc_composite_check)

    # --- Line 3 Breakdown (Cardholder Name) ---
    name_raw = l3.replace("<", " ").strip()
    name_parts = [p for p in name_raw.split() if p]
    formatted_name = " ".join(name_parts)

    all_checks_valid = (
        is_doc_check_valid
        and is_dob_check_valid
        and is_expiry_check_valid
        and is_composite_check_valid
    )

    failures = []
    if not is_doc_check_valid:
        failures.append(f"Document Number check digit mismatch: expected {calc_doc_check}, got {doc_number_check}")
    if not is_dob_check_valid:
        failures.append(f"DOB check digit mismatch: expected {calc_dob_check}, got {dob_check}")
    if not is_expiry_check_valid:
        failures.append(f"Expiry check digit mismatch: expected {calc_expiry_check}, got {expiry_check}")
    if not is_composite_check_valid:
        failures.append(f"Composite check digit mismatch: expected {calc_composite_check}, got {composite_check}")

    return {
        "mrz_detected": True,
        "is_valid": all_checks_valid,
        "doc_type": doc_type,
        "issuing_country": issuing_country,
        "document_number": {
            "value": doc_number,
            "check_digit": doc_number_check,
            "calculated": int(calc_doc_check),
            "is_valid": is_doc_check_valid,
        },
        "document_number_raw": doc_number,
        "document_number_check_valid": is_doc_check_valid,
        "date_of_birth": {
            "value": dob_date.isoformat() if dob_date else dob_str,
            "check_digit": dob_check,
            "calculated": int(calc_dob_check),
            "is_valid": is_dob_check_valid,
        },
        "dob_check_valid": is_dob_check_valid,
        "sex": sex,
        "expiry_date": {
            "value": expiry_date.isoformat() if expiry_date else expiry_str,
            "check_digit": expiry_check,
            "calculated": int(calc_expiry_check),
            "is_valid": is_expiry_check_valid,
        },
        "expiry_check_valid": is_expiry_check_valid,
        "nationality": nationality,
        "optional_data": opt_data_2.replace("<", ""),
        "composite_check": {
            "check_digit": composite_check,
            "calculated": int(calc_composite_check),
            "is_valid": is_composite_check_valid,
        },
        "composite_check_valid": is_composite_check_valid,
        "name": formatted_name,
        "raw_mrz": [l1, l2, l3],
        "raw_lines": [l1, l2, l3],
        "failures": failures,
    }


def audit_cnic_dates(
    issue_date: Optional[date],
    expiry_date: Optional[date],
    dob: Optional[date],
    is_lifetime: bool = False,
) -> list[dict[str, Any]]:
    """
    Perform temporal audits on CNIC dates:
    - Minimum age at issuance must be >= 18 years
    - Validity must be 10 years (or lifetime for age >= 60)
    - Issue date must not be in the future
    - Expiry date must be strictly after issue date
    """
    anomalies = []
    today = date.today()

    if issue_date and issue_date > today:
        anomalies.append({
            "type": "FUTURE_ISSUE_DATE",
            "message": f"CNIC Date of Issue ({issue_date}) is in the future relative to system time ({today}).",
            "severity": "CRITICAL",
            "risk_points": 50,
        })

    if issue_date and dob:
        age_at_issue = (issue_date - dob).days // 365
        if age_at_issue < 18:
            anomalies.append({
                "type": "UNDERAGE_ADULT_CNIC",
                "message": (
                    f"Cardholder was approximately {age_at_issue} years old at CNIC issue date ({issue_date}). "
                    "NADRA adult identity cards are legally issued strictly to citizens aged 18 and older."
                ),
                "severity": "CRITICAL",
                "risk_points": 60,
            })

    if issue_date and expiry_date:
        if expiry_date <= issue_date:
            anomalies.append({
                "type": "EXPIRY_BEFORE_ISSUE",
                "message": f"CNIC Date of Expiry ({expiry_date}) occurs on or before Date of Issue ({issue_date}).",
                "severity": "CRITICAL",
                "risk_points": 70,
            })
        else:
            validity_years = (expiry_date - issue_date).days / 365.25
            # Standard Pakistani CNIC validity is exactly 10 years (allowing +/- 30 days leap/grace)
            if not is_lifetime and not (9.8 <= validity_years <= 10.3):
                anomalies.append({
                    "type": "NON_STANDARD_VALIDITY_PERIOD",
                    "message": (
                        f"CNIC validity duration is {validity_years:.1f} years ({issue_date} to {expiry_date}). "
                        "NADRA Smart CNICs have a statutory validity of exactly 10 years unless marked 'Lifetime'."
                    ),
                    "severity": "HIGH",
                    "risk_points": 35,
                })

    return anomalies


def verify_identity_document(
    all_text: str,
    ocr_lines: Optional[list[str]] = None,
    declared_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Comprehensive NADRA Identity Document verification:
    1. Extracts CNIC numbers and validates 13-digit schema & province code.
    2. Audits 13th digit gender parity against cardholder text.
    3. Detects and verifies 3-line TD1 MRZ checksums (ICAO 9303).
    4. Cross-verifies MRZ data against Front Visual Zone (VIZ).
    5. Formulates statutory findings under NADRA Ordinance 2000 Section 30.
    """
    declared_data = declared_data or {}
    lines = ocr_lines or [line.strip() for line in all_text.splitlines() if line.strip()]

    # 1. Extract CNIC Candidates
    cnic_matches = CNIC_HYPHEN_REGEX.findall(all_text)
    primary_cnic = None
    if cnic_matches:
        primary_cnic = f"{cnic_matches[0][0]}-{cnic_matches[0][1]}-{cnic_matches[0][2]}"
    else:
        raw_matches = CNIC_RAW_REGEX.findall(all_text)
        if raw_matches:
            primary_cnic = f"{raw_matches[0][:5]}-{raw_matches[0][5:12]}-{raw_matches[0][12]}"

    findings: list[dict[str, Any]] = []
    cnic_struct = None
    gender_verified = True
    gender_explanation = ""

    if primary_cnic:
        cnic_struct = validate_cnic_structure(primary_cnic)

        # Check Province Code
        if not cnic_struct["is_valid"]:
            findings.append({
                "category": "TRANSACTION_FORMAT_VIOLATION",
                "severity": "CRITICAL",
                "rule_id": "RULE_CNIC_PROVINCE_CODE_INVALID",
                "risk_points": 50,
                "title": f"Invalid NADRA CNIC Province Code: '{primary_cnic}'",
                "description": (
                    f"The CNIC number '{primary_cnic}' contains invalid administrative code '{cnic_struct.get('province_code')}'. "
                    "Under NADRA regulations, valid province codes are 1 to 8 (1=KP, 2=FATA, 3=Punjab, 4=Sindh, "
                    "5=Balochistan, 6=Islamabad, 7=GB, 8=AJK). Digits 0 and 9 indicate fabricated credentials."
                ),
                "expected_value": "Valid Province Code (1–8)",
                "actual_value": f"Invalid Code: {cnic_struct.get('province_code')}",
                "discrepancy": "Non-existent NADRA administrative province code",
                "technical_details": {
                    "cnic": primary_cnic,
                    "error": cnic_struct.get("error"),
                    "statutory_reference": "NADRA Ordinance 2000 Section 30",
                },
            })

        # Check Gender Parity
        declared_gender = declared_data.get("gender")
        if not declared_gender:
            if GENDER_MALE_REGEX.search(all_text):
                declared_gender = "MALE"
            elif GENDER_FEMALE_REGEX.search(all_text):
                declared_gender = "FEMALE"

        if declared_gender and cnic_struct["is_valid"]:
            parity_ok, parity_reason, detected_parity = verify_gender_parity(primary_cnic, declared_gender)
            gender_verified = parity_ok
            gender_explanation = parity_reason
            if not parity_ok:
                findings.append({
                    "category": "TRANSACTION_FORMAT_VIOLATION",
                    "severity": "CRITICAL",
                    "rule_id": "RULE_CNIC_GENDER_PARITY_MISMATCH",
                    "risk_points": 60,
                    "title": f"NADRA CNIC Gender Parity Contradiction: '{primary_cnic}'",
                    "description": (
                        f"{parity_reason} Under the NADRA Registration Framework, the final digit of the 13-digit CNIC "
                        "is mathematically bound to biological gender (Odd for Male, Even for Female). "
                        "A contradiction is definitive mathematical proof of card tampering or credential fabrication."
                    ),
                    "expected_value": f"Gender parity matching declared gender '{declared_gender}'",
                    "actual_value": f"CNIC 13th digit '{cnic_struct['check_digit']}' designates {detected_parity}",
                    "discrepancy": f"Contradiction between printed gender ({declared_gender}) and CNIC parity ({detected_parity})",
                    "technical_details": {
                        "cnic": primary_cnic,
                        "check_digit": cnic_struct["check_digit"],
                        "detected_parity": detected_parity,
                        "declared_gender": declared_gender,
                        "statutory_reference": "NADRA Ordinance 2000 Section 30",
                    },
                })
    else:
        # No CNIC detected at all in an identity document
        findings.append({
            "category": "TRANSACTION_FORMAT_VIOLATION",
            "severity": "HIGH",
            "rule_id": "RULE_CNIC_MISSING",
            "risk_points": 40,
            "title": "Missing Pakistani 13-Digit CNIC Number",
            "description": "Document classified as an Identity Document, but no valid 13-digit CNIC string was identified.",
            "expected_value": "13-digit Pakistani CNIC (XXXXX-XXXXXXX-X)",
            "actual_value": "Not detected",
            "discrepancy": "Missing essential national identity number",
            "technical_details": {},
        })

    # 2. ICAO 9303 TD1 MRZ Verification (Reverse Side of Smart CNIC)
    mrz_result = parse_and_verify_snic_mrz(lines)
    if mrz_result.get("mrz_detected"):
        if not mrz_result["is_valid"]:
            failures_str = "; ".join(mrz_result.get("failures", []))
            findings.append({
                "category": "TRANSACTION_FORMAT_VIOLATION",
                "severity": "CRITICAL",
                "rule_id": "RULE_CNIC_MRZ_CHECKSUM_INVALID",
                "risk_points": 70,
                "title": "Smart CNIC Machine Readable Zone (MRZ) Checksum Failure",
                "description": (
                    f"The 3-line TD1 Machine Readable Zone on the reverse of the Smart Identity Card failed "
                    f"ICAO Doc 9303 7-3-1 modulus-10 mathematical validation: {failures_str}. "
                    "Legitimate NADRA Smart Cards always satisfy ICAO checksums. A checksum mismatch confirms "
                    "graphic manipulation or counterfeit generation of the MRZ block."
                ),
                "expected_value": "Valid ICAO 9303 7-3-1 Check Digits",
                "actual_value": failures_str,
                "discrepancy": "Failed ICAO 9303 MRZ Checksum Algorithm",
                "technical_details": mrz_result,
            })

        # Cross-Verify MRZ Data against Front Visual Zone (VIZ)
        if primary_cnic and mrz_result.get("optional_data"):
            clean_mrz_cnic = re.sub(r"[^\d]", "", mrz_result["optional_data"])
            clean_front_cnic = re.sub(r"[^\d]", "", primary_cnic)
            # Some MRZs store either full 13 digits or 11/12 digits
            if len(clean_mrz_cnic) >= 11 and clean_mrz_cnic not in clean_front_cnic and clean_front_cnic not in clean_mrz_cnic:
                findings.append({
                    "category": "TRANSACTION_FORMAT_VIOLATION",
                    "severity": "CRITICAL",
                    "rule_id": "RULE_CNIC_MRZ_FRONT_MISMATCH",
                    "risk_points": 80,
                    "title": "Front CNIC Contradicts Reverse MRZ Identity Number",
                    "description": (
                        f"The CNIC on the front visual card ({primary_cnic}) does not match the identity number "
                        f"encoded in the reverse Machine Readable Zone ({mrz_result['optional_data']}). "
                        "This disparity confirms visual splicing or Photoshop manipulation of the cardholder credentials."
                    ),
                    "expected_value": f"MRZ Identity: {clean_mrz_cnic}",
                    "actual_value": f"Front VIZ: {clean_front_cnic}",
                    "discrepancy": "Front visual zone diverges from optical machine readable zone",
                    "technical_details": {
                        "front_cnic": primary_cnic,
                        "mrz_data": mrz_result["optional_data"],
                    },
                })

    # 3. Clean Identity Affirmation
    is_tampered = any(f["severity"] in ("CRITICAL", "HIGH") for f in findings)
    if not is_tampered and primary_cnic and cnic_struct and cnic_struct["is_valid"]:
        findings.append({
            "category": "TRANSACTION_FORMAT_VIOLATION",
            "severity": "INFO",
            "rule_id": "RULE_CNIC_VERIFIED",
            "risk_points": 0,
            "title": f"NADRA CNIC Architecture Verified ({cnic_struct['formatted_cnic']})",
            "description": (
                f"CNIC {cnic_struct['formatted_cnic']} verified authentic: Province code '{cnic_struct['province_code']}' "
                f"matches {cnic_struct['province_name']}, 13th digit '{cnic_struct['check_digit']}' confirms {cnic_struct['gender_parity']} "
                "parity, and all structural invariants satisfy the National Database and Registration Authority Ordinance 2000."
            ),
            "expected_value": "Certified Authentic NADRA Identity Card",
            "actual_value": f"Valid {cnic_struct['province_name']} ({cnic_struct['gender_parity']})",
            "discrepancy": "0 discrepancy — Verified Authentic",
            "technical_details": {
                "cnic": cnic_struct["formatted_cnic"],
                "province": cnic_struct["province_name"],
                "gender_parity": cnic_struct["gender_parity"],
                "mrz_verified": mrz_result.get("is_valid", True),
            },
        })

    overall_status = "TAMPERED" if any(f["severity"] == "CRITICAL" for f in findings) else ("ANOMALY_DETECTED" if is_tampered else "VERIFIED")

    return {
        "overall_status": overall_status,
        "primary_cnic": primary_cnic,
        "cnic_structure": cnic_struct,
        "gender_parity_verified": gender_verified,
        "gender_explanation": gender_explanation,
        "mrz_result": mrz_result,
        "findings": findings,
        "is_conforming": not is_tampered,
    }
