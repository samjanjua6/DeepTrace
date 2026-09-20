"""
SBP AML/CFT & Customer Due Diligence (CDD) Screening Engine.
Implements high-precision Pakistani name normalization, fuzzy token-sort matching,
and statutory screening against:
- NACTA 4th Schedule Proscribed Persons & Entities (ATA 1997 §11EE)
- UN Security Council 1267 / 1988 / 2253 Sanctions Lists
- Politically Exposed Persons (PEPs) under SBP BPRD Circular No. 1 of 2021
- Hawala / Hundi / Trade Structuring Red Flag Narrations
"""

import difflib
import logging
import re
from typing import Any, Optional, Tuple

from app.features.pipeline.tasks.aml_sanctions_data import (
    AML_HIGH_RISK_NARRATION_KEYWORDS,
    NACTA_PROSCRIBED_ENTITIES,
    NACTA_PROSCRIBED_INDIVIDUALS,
    PEP_REGISTRY,
    UNSC_SANCTIONED_INDIVIDUALS,
)

logger = logging.getLogger("deeptrace.aml_cdd")

# Common South Asian honorifics and religious prefixes
HONORIFIC_PREFIXES_REGEX = re.compile(
    r"\b(mr|mrs|ms|dr|syed|hafiz|qari|moulana|maulana|al-haj|sheikh|engr|advocate|mian|senator|minister|governor|justice|colonel|brigadier|general|admiral)\b\.?",
    re.IGNORECASE,
)

# Transliteration aliases
TRANSLITERATION_MAP = [
    (r"\bmohammad\b|\bmohd\b|\bmd\b", "muhammad"),
    (r"\bahmad\b", "ahmed"),
    (r"\bchaudhary\b|\bchoudhry\b|\bch\b", "chaudhry"),
    (r"\bsayed\b", "syed"),
    (r"\bhussain\b", "husein"),
    (r"\bshahbaz\b", "shehbaz"),
]

# Account title patterns in Pakistani bank statements
ACCOUNT_TITLE_PATTERNS = [
    re.compile(r"(?i)(?:Account\s+Title|Title\s+of\s+Account|Customer\s+Name|Name\s+of\s+Account\s+Holder|Account\s+Name)\s*[:\-]\s*([A-Za-z\s\.\,\'\-]+?)(?:\r?\n|\t|Account\s+No|IBAN|CNIC|Date|Branch|Currency|Address|$)", re.IGNORECASE),
    re.compile(r"(?i)(?:Beneficiary\s+Name|Remitter\s+Name)\s*[:\-]\s*([A-Za-z\s\.\,\'\-]+?)(?:\r?\n|\t|$)", re.IGNORECASE),
]

# Pakistani CNIC regex: 5 digits - 7 digits - 1 digit
CNIC_REGEX = re.compile(r"\b(\d{5}-\d{7}-\d{1})\b")
CNIC_RAW_REGEX = re.compile(r"\b(\d{13})\b")


def normalize_tokens_for_screening(name: str) -> list[str]:
    """
    Normalize South Asian names:
    - Strip honorifics (Mr, Dr, Hafiz, Moulana, Syed, Mian)
    - Normalize transliteration (Mohammad -> muhammad, Ahmad -> ahmed)
    - Return sorted list of lowercase words > 1 char
    """
    if not name or not isinstance(name, str):
        return []

    cleaned = HONORIFIC_PREFIXES_REGEX.sub(" ", name)
    for pat, repl in TRANSLITERATION_MAP:
        cleaned = re.sub(pat, repl, cleaned, flags=re.IGNORECASE)

    tokens = [t.lower() for t in re.findall(r"[a-zA-Z]+", cleaned) if len(t) > 1]
    return tokens


def compute_name_match_score(candidate_name: str, reference_name: str) -> Tuple[float, str]:
    """
    Compute similarity between a candidate name and a reference sanctions/PEP name.
    Returns (score 0.0-1.0, match_type).
    """
    cand_tokens = normalize_tokens_for_screening(candidate_name)
    ref_tokens = normalize_tokens_for_screening(reference_name)

    if not cand_tokens or not ref_tokens:
        return 0.0, "NONE"

    cand_str = " ".join(cand_tokens)
    ref_str = " ".join(ref_tokens)

    # 1. Exact string match after normalization
    if cand_str == ref_str:
        return 1.0, "EXACT_NORMALIZED"

    s_cand = set(cand_tokens)
    s_ref = set(ref_tokens)

    # 2. Token subset match (e.g. "Muhammad Saeed" in "Hafiz Muhammad Saeed")
    # Requires at least 2 tokens to prevent matching single words like "Khan"
    if len(s_cand) >= 2 and s_cand.issubset(s_ref):
        return 0.96, "TOKEN_SUBSET"
    if len(s_ref) >= 2 and s_ref.issubset(s_cand):
        return 0.96, "TOKEN_SUBSET"

    # 3. Token Overlap Jaccard-like
    overlap = len(s_cand.intersection(s_ref))
    tok_ratio = overlap / max(len(s_cand), len(s_ref))

    # 4. SequenceMatcher on sorted token strings
    cand_sorted = " ".join(sorted(cand_tokens))
    ref_sorted = " ".join(sorted(ref_tokens))
    seq_ratio = difflib.SequenceMatcher(None, cand_sorted, ref_sorted).ratio()

    final_score = max(tok_ratio, seq_ratio)
    match_type = "FUZZY" if final_score >= 0.85 else "LOW"
    return round(final_score, 4), match_type


def extract_customer_credentials_from_text(all_text: str) -> dict[str, Any]:
    """
    Extract candidate Account Title, Customer Name, and CNIC from raw statement text.
    """
    account_titles = []
    for pat in ACCOUNT_TITLE_PATTERNS:
        matches = pat.findall(all_text)
        for m in matches:
            cleaned = m.strip()
            # Must have reasonable length and not be pure header junk
            if 3 <= len(cleaned) <= 60 and not any(k in cleaned.lower() for k in ["statement", "bank", "balance", "debit", "credit", "page", "branch"]):
                account_titles.append(cleaned)

    cnic_matches = CNIC_REGEX.findall(all_text)
    if not cnic_matches:
        # Check raw 13-digit matches that are not account numbers
        for raw in CNIC_RAW_REGEX.findall(all_text):
            formatted = f"{raw[:5]}-{raw[5:12]}-{raw[12]}"
            cnic_matches.append(formatted)

    primary_title = account_titles[0] if account_titles else None
    primary_cnic = cnic_matches[0] if cnic_matches else None

    return {
        "account_titles": list(dict.fromkeys(account_titles)),
        "primary_account_title": primary_title,
        "cnic_numbers": list(dict.fromkeys(cnic_matches)),
        "primary_cnic": primary_cnic,
    }


def screen_entity_against_sanctions(
    name: str,
    cnic: Optional[str] = None,
    threshold: float = 0.86,
) -> list[dict[str, Any]]:
    """
    Screen an individual or entity name against:
    1. NACTA Proscribed Individuals & Entities
    2. UNSC 1267/1988/2253 Sanctions
    3. Politically Exposed Persons (PEPs)
    """
    matches: list[dict[str, Any]] = []

    if not name or len(name.strip()) < 3:
        return matches

    clean_cnic = cnic.strip() if cnic else None

    # 1. NACTA Proscribed Individuals
    for indiv in NACTA_PROSCRIBED_INDIVIDUALS:
        score, match_type = compute_name_match_score(name, indiv["name"])
        # Check aliases
        for alias in indiv.get("aliases", []):
            a_score, a_type = compute_name_match_score(name, alias)
            if a_score > score:
                score, match_type = a_score, a_type

        # Check CNIC tie-breaker
        cnic_match = False
        if clean_cnic and indiv.get("cnic"):
            if clean_cnic == indiv["cnic"]:
                score = 1.0
                match_type = "CNIC_EXACT_MATCH"
                cnic_match = True

        if score >= threshold or cnic_match:
            matches.append({
                "list_type": "NACTA_4TH_SCHEDULE",
                "entity_name": indiv["name"],
                "candidate_name": name,
                "match_score": score,
                "match_type": match_type,
                "category": "PROSCRIBED_INDIVIDUAL",
                "role": indiv.get("role"),
                "statutory_reference": indiv.get("statutory_reference"),
                "action_directive": indiv.get("action_directive", "MANDATORY_STR_AND_ACCOUNT_FREEZE"),
                "risk_points": 100,
                "severity": "CRITICAL",
            })

    # 2. NACTA Proscribed Entities
    for ent in NACTA_PROSCRIBED_ENTITIES:
        score, match_type = compute_name_match_score(name, ent["name"])
        for alias in ent.get("aliases", []):
            a_score, a_type = compute_name_match_score(name, alias)
            if a_score > score:
                score, match_type = a_score, a_type

        if score >= threshold:
            matches.append({
                "list_type": "NACTA_PROSCRIBED_ORGANIZATION",
                "entity_name": ent["name"],
                "candidate_name": name,
                "match_score": score,
                "match_type": match_type,
                "category": ent.get("category"),
                "statutory_reference": ent.get("proscription_authority"),
                "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
                "risk_points": 100,
                "severity": "CRITICAL",
            })

    # 3. UNSC Sanctions (1267 / 1988 / 2253)
    for unsc in UNSC_SANCTIONED_INDIVIDUALS:
        score, match_type = compute_name_match_score(name, unsc["name"])
        if score >= threshold:
            matches.append({
                "list_type": "UNSC_1267_SANCTIONS",
                "entity_name": unsc["name"],
                "candidate_name": name,
                "match_score": score,
                "match_type": match_type,
                "category": "UN_DESIGNATED_TERRORIST",
                "unsc_id": unsc.get("unsc_id"),
                "committee": unsc.get("committee"),
                "statutory_reference": unsc.get("statutory_reference"),
                "action_directive": "MANDATORY_ASSET_FREEZE_UNSC_ACT_1948",
                "risk_points": 100,
                "severity": "CRITICAL",
            })

    # 4. Politically Exposed Persons (PEPs)
    for pep in PEP_REGISTRY:
        score, match_type = compute_name_match_score(name, pep["name"])
        for alias in pep.get("aliases", []):
            a_score, a_type = compute_name_match_score(name, alias)
            if a_score > score:
                score, match_type = a_score, a_type

        if score >= threshold:
            matches.append({
                "list_type": "PEP_REGISTRY",
                "entity_name": pep["name"],
                "candidate_name": name,
                "match_score": score,
                "match_type": match_type,
                "category": pep.get("pep_type", "DOMESTIC_PEP"),
                "public_office": pep.get("public_office"),
                "statutory_reference": pep.get("statutory_ground"),
                "action_directive": "SENIOR_MANAGEMENT_APPROVAL_AND_EDD_REQUIRED",
                "risk_points": 35,
                "severity": "HIGH",
            })

    return matches


# Legitimate Pakistani digital payment rails and retail transaction keywords
LEGITIMATE_BANKING_P2P_INDICATORS = {
    "raast", "1link", "ibft", "interbank", "inter-bank", "funds transfer",
    "fund transfer", "alfa", "hbl pay", "nayapay", "sadapay", "easypaisa",
    "jazzcash", "upaisa", "mobile banking", "internet banking", "app transfer",
    "money transfer", "money request", "rent", "salary", "fee", "bill",
    "over the counter", "clearing", "cheque", "deposit", "atm", "pos",
}


def scan_transaction_narrations(transactions: list[dict]) -> list[dict[str, Any]]:
    """
    Scan transaction ledger descriptions for informal Hawala/Hundi/Crypto red flags.
    Uses regex word boundaries to avoid false-positive substring matches and protects
    legitimate Pakistani interbank payment rails (e.g. Raast P2P, Alfa P2P, 1LINK P2P).
    """
    red_flags: list[dict[str, Any]] = []

    for tx in transactions:
        narr = tx.get("narration") or tx.get("description") or tx.get("particulars") or ""
        if not narr:
            continue
        narr_lower = narr.lower()

        for kw in AML_HIGH_RISK_NARRATION_KEYWORDS:
            term = kw["term"].lower()
            # Enforce regex word boundaries on matched term
            pattern = rf"\b{re.escape(term)}\b"
            if re.search(pattern, narr_lower):
                red_flags.append({
                    "row_number": tx.get("row_number") or tx.get("line_number") or tx.get("index"),
                    "page_number": tx.get("page_number") or tx.get("page") or 1,
                    "narration": narr,
                    "matched_term": kw["term"],
                    "category": kw["category"],
                    "description": kw["description"],
                    "amount": tx.get("amount") or tx.get("credit") or tx.get("debit"),
                    "date": tx.get("date"),
                })
                break

    return red_flags


def perform_sbp_cdd_screening(
    all_text: str,
    transactions: list[dict],
    customer_name_hint: Optional[str] = None,
    cnic_hint: Optional[str] = None,
) -> dict[str, Any]:
    """
    Perform complete SBP Customer Due Diligence (CDD) and AML/CFT screening:
    1. Extract customer name and CNIC.
    2. Screen customer against NACTA, UNSC 1267, and PEP registries.
    3. Screen transaction counterparty remitters/beneficiaries.
    4. Screen narrative hawala/hundi indicators.
    5. Formulate SBP BPRD statutory action directives.
    """
    creds = extract_customer_credentials_from_text(all_text)
    account_title = customer_name_hint or creds.get("primary_account_title")
    cnic = cnic_hint or creds.get("primary_cnic")

    # Names to screen (account title + any high-frequency counterparties)
    names_to_screen = []
    if account_title:
        names_to_screen.append(account_title)
    for t in creds.get("account_titles", []):
        if t not in names_to_screen:
            names_to_screen.append(t)

    all_matches: list[dict[str, Any]] = []
    for n in names_to_screen:
        hits = screen_entity_against_sanctions(n, cnic=cnic)
        for h in hits:
            if not any(existing["entity_name"] == h["entity_name"] and existing["list_type"] == h["list_type"] for existing in all_matches):
                all_matches.append(h)

    # Scan transaction narrations for Hawala/Hundi/Crypto red flags
    narration_red_flags = scan_transaction_narrations(transactions)

    # Classify overall compliance status
    has_nacta = any(m["list_type"] in ("NACTA_4TH_SCHEDULE", "NACTA_PROSCRIBED_ORGANIZATION") for m in all_matches)
    has_unsc = any(m["list_type"] == "UNSC_1267_SANCTIONS" for m in all_matches)
    has_pep = any(m["list_type"] == "PEP_REGISTRY" for m in all_matches)
    has_narration = len(narration_red_flags) > 0

    if has_nacta:
        overall_status = "PROSCRIBED_MATCH"
        primary_directive = "MANDATORY_STR_AND_ACCOUNT_FREEZE"
    elif has_unsc:
        overall_status = "SANCTIONS_MATCH"
        primary_directive = "MANDATORY_ASSET_FREEZE_UNSC_ACT_1948"
    elif has_pep:
        overall_status = "PEP_DETECTED"
        primary_directive = "SENIOR_MANAGEMENT_APPROVAL_AND_EDD_REQUIRED"
    elif has_narration:
        overall_status = "HIGH_RISK_NARRATION"
        primary_directive = "ENHANCED_TRANSACTION_MONITORING_REQUIRED"
    else:
        overall_status = "CLEARED"
        primary_directive = "STANDARD_CUSTOMER_DUE_DILIGENCE_CONFIRMED"

    # Construct structured findings
    findings: list[dict[str, Any]] = []

    if has_nacta:
        nacta_match = next(m for m in all_matches if m["list_type"] in ("NACTA_4TH_SCHEDULE", "NACTA_PROSCRIBED_ORGANIZATION"))
        findings.append({
            "category": "TRANSACTION_FORMAT_VIOLATION",
            "severity": "CRITICAL",
            "rule_id": "RULE_AML_NACTA_PROSCRIBED_MATCH",
            "risk_points": 100,
            "title": f"NACTA 4th Schedule Proscribed Match: '{nacta_match['candidate_name']}' matches '{nacta_match['entity_name']}'",
            "description": (
                f"The account title '{nacta_match['candidate_name']}' matches proscribed entity '{nacta_match['entity_name']}' "
                f"under Section 11EE of the Anti-Terrorism Act 1997 (ATA 1997) with {int(nacta_match['match_score']*100)}% similarity confidence. "
                "Under State Bank of Pakistan (SBP) BPRD Circular No. 1 of 2021, regulated institutions must immediately halt all transactions, "
                "freeze account assets, and submit a Suspicious Transaction Report (STR) to the Financial Monitoring Unit (FMU)."
            ),
            "expected_value": "Clean Customer Due Diligence (Non-Proscribed Individual)",
            "actual_value": f"NACTA Match: {nacta_match['entity_name']} (Role: {nacta_match.get('role', 'Designated')})",
            "discrepancy": "Statutory Proscription under Anti-Terrorism Act 1997 Section 11EE",
            "technical_details": {**nacta_match, "aml_category": "AML_SANCTIONS_MATCH"},
        })

    if has_unsc:
        unsc_match = next(m for m in all_matches if m["list_type"] == "UNSC_1267_SANCTIONS")
        findings.append({
            "category": "TRANSACTION_FORMAT_VIOLATION",
            "severity": "CRITICAL",
            "rule_id": "RULE_AML_UNSC_1267_SANCTIONS_MATCH",
            "risk_points": 100,
            "title": f"UN Security Council 1267 Sanctions Match: '{unsc_match['candidate_name']}'",
            "description": (
                f"Account title '{unsc_match['candidate_name']}' matches United Nations Security Council (UNSC) "
                f"sanctioned individual '{unsc_match['entity_name']}' (UN Reference: {unsc_match.get('unsc_id', '1267')}). "
                "Under the United Nations (Security Council) Act 1948 and SBP AML/CFT Regulations, immediate asset freezing without prior notice is legally mandatory."
            ),
            "expected_value": "Clean Sanctions Screening (Non-Designated Entity)",
            "actual_value": f"UNSC Sanctioned: {unsc_match['entity_name']} (Ref: {unsc_match.get('unsc_id')})",
            "discrepancy": "UNSC Resolution 1267/1989/2253 Sanctions Designation",
            "technical_details": {**unsc_match, "aml_category": "AML_SANCTIONS_MATCH"},
        })

    if has_pep:
        pep_match = next(m for m in all_matches if m["list_type"] == "PEP_REGISTRY")
        findings.append({
            "category": "TRANSACTION_FORMAT_VIOLATION",
            "severity": "HIGH",
            "rule_id": "RULE_AML_PEP_IDENTIFIED",
            "risk_points": 35,
            "title": f"Politically Exposed Person (PEP) Identified: '{pep_match['candidate_name']}'",
            "description": (
                f"Account holder '{pep_match['candidate_name']}' matches Politically Exposed Person (PEP) '{pep_match['entity_name']}' "
                f"holding public office as '{pep_match.get('public_office')}'. Under SBP BPRD Circular No. 1 of 2021, "
                "establishing or maintaining banking relationships with PEPs mandates Senior Management Approval (SMA), "
                "Enhanced Due Diligence (EDD), and verification of Source of Wealth."
            ),
            "expected_value": "Standard Risk Customer (Non-PEP)",
            "actual_value": f"PEP: {pep_match['entity_name']} ({pep_match.get('public_office')})",
            "discrepancy": "Politically Exposed Person designation under SBP BPRD Guidelines",
            "technical_details": {**pep_match, "aml_category": "PEP_IDENTIFIED"},
        })

    if has_narration:
        matched_categories = set(r.get("category") for r in narration_red_flags)
        has_crypto = "UNLICENSED_VIRTUAL_ASSETS" in matched_categories
        has_hawala = any(c in matched_categories for c in ("INFORMAL_VALUE_TRANSFER", "UNOFFICIAL_SETTLEMENT"))
        has_structuring = any(c in matched_categories for c in ("STRUCTURING", "CASH_STRUCTURING", "BENAMI_TRANSACTION"))

        unique_terms = sorted(list(set(r["matched_term"] for r in narration_red_flags)))
        sample_terms = ", ".join(unique_terms[:4])
        count = len(narration_red_flags)

        if has_crypto and not (has_hawala or has_structuring):
            title = f"Unlicensed Cryptocurrency P2P Trading Indicators in {count} Transaction(s)"
            desc = (
                f"Detected {count} transaction(s) bearing prohibited virtual asset or cryptocurrency P2P trading keywords: "
                f"{sample_terms}. Prohibited under State Bank of Pakistan (SBP) BPRD Circular No. 3 of 2018."
            )
            discrepancy = "Prohibited virtual asset / cryptocurrency P2P trading keywords detected (SBP BPRD Circular No. 3 of 2018)"
        elif has_hawala and not (has_crypto or has_structuring):
            title = f"Informal Hawala / Hundi Settlement Red Flags in {count} Transaction(s)"
            desc = (
                f"Detected {count} transaction(s) bearing prohibited informal value transfer (Hawala / Hundi) keywords: "
                f"{sample_terms}. Prohibited under Anti-Money Laundering Act (AMLA 2010) and SBP BPRD regulations."
            )
            discrepancy = "Prohibited informal value transfer (Hawala / Hundi) keywords detected"
        elif has_structuring and not (has_crypto or has_hawala):
            title = f"Transaction Structuring / Smurfing Red Flags in {count} Transaction(s)"
            desc = (
                f"Detected {count} transaction(s) bearing high-risk structuring, smurfing, or Benami indicators: "
                f"{sample_terms}. Prohibited under Benami Transactions (Prohibition) Act 2017 and SBP AML guidelines."
            )
            discrepancy = "High-risk transaction structuring or smurfing keywords detected"
        else:
            title = f"Informal Value Transfer & High-Risk AML Red Flags in {count} Transaction(s)"
            desc = (
                f"Detected {count} transaction(s) bearing prohibited informal value transfer, structuring, or crypto liquidation keywords: "
                f"{sample_terms}. Prohibited under SBP BPRD Circular No. 3 of 2018 and AMLA 2010."
            )
            discrepancy = "Prohibited informal value transfer or virtual asset structuring keywords detected"

        findings.append({
            "category": "TRANSACTION_FORMAT_VIOLATION",
            "severity": "HIGH",
            "rule_id": "RULE_AML_HIGH_RISK_NARRATION",
            "risk_points": 25,
            "title": title,
            "description": desc,
            "expected_value": "Standard Commercial / Personal Transaction Narratives",
            "actual_value": f"{count} Suspicious Narrative(s)",
            "discrepancy": discrepancy,
            "technical_details": {
                "red_flags": narration_red_flags,
                "matched_categories": list(matched_categories),
                "matched_terms": unique_terms,
                "aml_category": "AML_HIGH_RISK_NARRATION",
                "is_crypto": has_crypto,
                "is_hawala": has_hawala,
            },
        })

    if not findings:
        findings.append({
            "category": "TRANSACTION_FORMAT_VIOLATION",
            "severity": "INFO",
            "rule_id": "RULE_AML_CDD_CLEARED",
            "risk_points": 0,
            "title": "SBP Customer Due Diligence (CDD) & AML/CFT Screening Cleared",
            "description": (
                f"Account holder '{account_title or 'Account Holder'}' screened against NACTA 4th Schedule, "
                "UN Security Council 1267 Sanctions, and Politically Exposed Persons (PEPs) registry. "
                "No adverse regulatory matches or prohibited Hawala/Hundi narrations identified."
            ),
            "expected_value": "Non-Proscribed, Non-Sanctioned Customer",
            "actual_value": "Clean CDD Verification",
            "discrepancy": "None — SBP BPRD Circular 1 of 2021 Requirements Satisfied",
            "technical_details": {
                "account_title": account_title,
                "cnic": cnic,
                "nacta_cleared": True,
                "unsc_cleared": True,
                "pep_cleared": True,
                "aml_category": "CUSTOMER_DUE_DILIGENCE",
            },
        })

    return {
        "overall_status": overall_status,
        "action_directive": primary_directive,
        "account_title": account_title,
        "cnic": cnic,
        "nacta_match": has_nacta,
        "unsc_match": has_unsc,
        "pep_detected": has_pep,
        "high_risk_narration_count": len(narration_red_flags),
        "matched_entities": all_matches,
        "narration_red_flags": narration_red_flags,
        "findings": findings,
    }
