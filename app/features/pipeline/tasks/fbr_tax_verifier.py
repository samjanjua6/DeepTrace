"""
FBR Tax Verification Engine (Federal Board of Revenue).
NIST SP 800-86 Compliant Statutory Tax and Corporate Identity Examination.

Statutory Frameworks Enforced:
  1. Income Tax Ordinance, 2001 (Ordinance No. XLIX of 2001)
     - Section 149: Withholding of tax at source from salary
     - Section 181 / 181A: National Tax Number (NTN) & CNIC harmonization (FBR SRO 1007(I)/2017)
     - Section 182: Offenses and penalties for fraudulent tax statements
     - First Schedule, Part I, Division I: Progressive income tax slabs for salaried individuals
  2. Federal Board of Revenue Computerized Payment Receipt (CPR) standards
     - e-FBR / IRIS / SBP e-Payment verification
     - Head of Account and temporal non-future validity
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# FBR NTN Weights for Modulus 11 Check Digit (7 base digits)
_NTN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2]

# Regex patterns for extraction
# NTN corporate/AOP format: 7 digits followed by a hyphen and check digit, or labeled NTN
NTN_FORMAT_REGEX = re.compile(r"\b(\d{7})-?(\d)\b")
NTN_LABELED_REGEX = re.compile(
    r"\b(?:NTN|N\.T\.N|Tax\s*Number|National\s*Tax\s*Number)[\s:#.-]*(\d{7}-?\d|\d{5}-?\d{7}-?\d)\b",
    re.IGNORECASE,
)

# CPR patterns: CPR-YYYYMMDD-XXXX-XXXXXXX or IT-YYYY-XXXXXX
CPR_REGEX = re.compile(
    r"\b(CPR[-_\s]?\d{8}[-_\s]?[A-Z0-9]{4}[-_\s]?[A-Z0-9]{7}|(?:IT|ST|FED)[-_\s]?\d{4}[-_\s]?[A-Z0-9]{6,14}|CPR[-_\s]?[A-Z0-9]{10,24})\b",
    re.IGNORECASE,
)

# Salary Slip Keywords for Gross Salary and Withholding Tax
GROSS_SALARY_REGEX = re.compile(
    r"(?:Gross\s*(?:Salary|Pay|Earnings)|Total\s*(?:Earnings|Salary)|Basic\s*(?:Pay|Salary))\s*[:=]?\s*(?:PKR|Rs\.?)?\s*([0-9,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

TAX_DEDUCTION_REGEX = re.compile(
    r"(?:Income\s*Tax|Withholding\s*Tax|WHT|Tax\s*Deduction|IT\s*Deduction|Sec(?:tion)?\.?\s*149)\s*[:=]?\s*(?:PKR|Rs\.?)?\s*([0-9,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NTNVerificationResult:
    """Result of National Tax Number structural validation."""
    is_valid: bool
    ntn_raw: str
    formatted: str
    entity_type: str  # "CORPORATE_AOP" or "INDIVIDUAL_CNIC"
    base_digits: str
    check_digit: str
    expected_check_digit: str
    rule_id: str
    error_message: Optional[str] = None

    @property
    def formatted_ntn(self) -> str:
        return self.formatted

    @property
    def ntn_type(self) -> str:
        return self.entity_type

    @property
    def calculated_check_digit(self) -> str:
        return self.expected_check_digit

    @property
    def reason(self) -> str:
        return self.error_message or "Verified authentic under FBR Modulus 11."


@dataclass(frozen=True)
class Section149SalaryTaxResult:
    """Result of Section 149 Income Tax Ordinance 2001 salary tax audit."""
    is_compliant: bool
    monthly_gross: Decimal
    annual_gross: Decimal
    tax_year: int
    applicable_slab: int
    slab_description: str
    statutory_annual_tax: Decimal
    expected_monthly_wht: Decimal
    declared_monthly_wht: Decimal
    discrepancy_amount: Decimal
    discrepancy_percentage: Decimal
    rule_id: str
    severity: str
    narrative: str

    @property
    def status(self) -> str:
        if self.rule_id == "RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY":
            return "ZERO_TAX_VIOLATION"
        elif self.rule_id == "RULE_FBR_WHT_DISCREPANCY":
            return "DISCREPANCY"
        elif self.rule_id == "RULE_FBR_WHT_VERIFIED":
            return "COMPLIANT"
        return "UNKNOWN"

    @property
    def findings(self) -> list[dict[str, Any]]:
        return [{
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.slab_description,
            "description": self.narrative,
        }]

    def __getitem__(self, item: str) -> Any:
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


@dataclass(frozen=True)
class CPRVerificationResult:
    """Result of Computerized Payment Receipt validation."""
    is_valid: bool
    cpr_number: str
    receipt_type: str  # "INCOME_TAX", "SALES_TAX", "FED", "GENERIC_CPR"
    tax_year: Optional[int]
    payment_date: Optional[str]
    is_future_date: bool
    rule_id: str
    error_message: Optional[str] = None

    @property
    def is_future_dated(self) -> bool:
        return self.is_future_date

    @property
    def cpr_type(self) -> str:
        return self.receipt_type

    @property
    def reason(self) -> str:
        return self.error_message or "Authentic FBR Computerized Payment Receipt."


def calculate_ntn_check_digit(base_7: str) -> Optional[str]:
    """
    Compute the official FBR Modulus 11 check digit for a 7-digit base NTN.
    Weights: [8, 7, 6, 5, 4, 3, 2].
    """
    clean = re.sub(r"\D", "", base_7)
    if len(clean) != 7:
        return None

    digits = [int(c) for c in clean]
    weighted_sum = sum(d * w for d, w in zip(digits, _NTN_WEIGHTS))
    rem = weighted_sum % 11

    if rem == 0:
        return "0"
    check = 11 - rem
    if check == 10:
        # Undefined single-digit representation; unassigned by FBR
        return None
    return str(check)


def validate_ntn_structure(ntn_input: str) -> NTNVerificationResult:
    """
    Statutorily validate a Pakistani National Tax Number (NTN).
    Supports:
      - 7-digit + 1 check digit corporate/AOP NTNs (e.g. 0710008-6).
      - 13-digit individual CNIC NTNs under Section 181 of ITO 2001 & FBR SRO 1007(I)/2017.
    """
    if not ntn_input:
        return NTNVerificationResult(
            is_valid=False,
            ntn_raw="",
            formatted="",
            entity_type="UNKNOWN",
            base_digits="",
            check_digit="",
            expected_check_digit="",
            rule_id="RULE_FBR_NTN_INVALID_FORMAT",
            error_message="Empty or null NTN provided",
        )

    clean = re.sub(r"^(?:NTN|N\.T\.N)[\s:#.-]*", "", ntn_input.strip(), flags=re.IGNORECASE)
    digits_only = re.sub(r"\D", "", clean)

    # 1. Check if 13-digit CNIC is provided as Individual NTN
    if len(digits_only) == 13:
        try:
            from app.features.pipeline.tasks.nadra_cnic_verifier import validate_cnic_structure
            cnic_res = validate_cnic_structure(digits_only)
            formatted_cnic = f"{digits_only[:5]}-{digits_only[5:12]}-{digits_only[12]}"
            is_valid_cnic = cnic_res.get("is_valid", False) if isinstance(cnic_res, dict) else getattr(cnic_res, "is_valid", False)
            if is_valid_cnic:
                return NTNVerificationResult(
                    is_valid=True,
                    ntn_raw=ntn_input,
                    formatted=formatted_cnic,
                    entity_type="INDIVIDUAL_CNIC",
                    base_digits=digits_only[:12],
                    check_digit=digits_only[12],
                    expected_check_digit=digits_only[12],
                    rule_id="RULE_FBR_NTN_VERIFIED",
                )
            else:
                rule_id = cnic_res.get("rule_id", "RULE_FBR_NTN_INVALID_FORMAT") if isinstance(cnic_res, dict) else getattr(cnic_res, "rule_id", "RULE_FBR_NTN_INVALID_FORMAT")
                err_msg = cnic_res.get("error", "CNIC validation failed") if isinstance(cnic_res, dict) else getattr(cnic_res, "error_message", "CNIC validation failed")
                return NTNVerificationResult(
                    is_valid=False,
                    ntn_raw=ntn_input,
                    formatted=formatted_cnic,
                    entity_type="INDIVIDUAL_CNIC",
                    base_digits=digits_only[:12],
                    check_digit=digits_only[12],
                    expected_check_digit="",
                    rule_id=rule_id,
                    error_message=f"Individual CNIC NTN failed validation: {err_msg}",
                )
        except Exception as e:
            logger.debug("fbr_tax_verifier: CNIC fallback error: %s", e)

    # 2. Corporate / AOP 8-digit NTN (7 base + 1 check digit)
    if len(digits_only) == 8:
        base = digits_only[:7]
        check = digits_only[7]
        formatted = f"{base}-{check}"

        expected_check = calculate_ntn_check_digit(base)
        if expected_check is None:
            return NTNVerificationResult(
                is_valid=False,
                ntn_raw=ntn_input,
                formatted=formatted,
                entity_type="CORPORATE_AOP",
                base_digits=base,
                check_digit=check,
                expected_check_digit="",
                rule_id="RULE_FBR_NTN_CHECK_DIGIT_INVALID",
                error_message=f"FBR NTN {formatted} yields unassigned Modulus 11 remainder (check digit 10)",
            )

        if check == expected_check:
            return NTNVerificationResult(
                is_valid=True,
                ntn_raw=ntn_input,
                formatted=formatted,
                entity_type="CORPORATE_AOP",
                base_digits=base,
                check_digit=check,
                expected_check_digit=expected_check,
                rule_id="RULE_FBR_NTN_VERIFIED",
            )
        else:
            return NTNVerificationResult(
                is_valid=False,
                ntn_raw=ntn_input,
                formatted=formatted,
                entity_type="CORPORATE_AOP",
                base_digits=base,
                check_digit=check,
                expected_check_digit=expected_check,
                rule_id="RULE_FBR_NTN_CHECK_DIGIT_INVALID",
                error_message=(
                    f"FBR NTN Modulus 11 check digit failure: Expected '{expected_check}' "
                    f"for base '{base}', but found '{check}'."
                ),
            )

    return NTNVerificationResult(
        is_valid=False,
        ntn_raw=ntn_input,
        formatted=clean,
        entity_type="UNKNOWN",
        base_digits="",
        check_digit="",
        expected_check_digit="",
        rule_id="RULE_FBR_NTN_INVALID_FORMAT",
        error_message=f"NTN '{ntn_input}' does not conform to valid length ({len(digits_only)} digits). Expected 8 digits (Corporate) or 13 digits (CNIC).",
    )


def calculate_expected_salary_wht(monthly_gross: Decimal, tax_year: int = 2025) -> dict[str, Any]:
    """
    Compute statutory Withholding Tax (WHT) under Section 149 of the Income Tax Ordinance, 2001
    (First Schedule, Part I, Division I - Salaried Individuals).
    """
    annual_gross = monthly_gross * Decimal("12")

    # Finance Act 2024 (Tax Year 2025 & 2026)
    if tax_year >= 2025:
        if annual_gross <= Decimal("600000"):
            slab = 1
            desc = "Slab 1: Up to PKR 600,000 (0%)"
            annual_tax = Decimal("0")
        elif annual_gross <= Decimal("1200000"):
            slab = 2
            desc = "Slab 2: PKR 600,001 - 1,200,000 (5% exceeding 600,000)"
            annual_tax = (annual_gross - Decimal("600000")) * Decimal("0.05")
        elif annual_gross <= Decimal("2200000"):
            slab = 3
            desc = "Slab 3: PKR 1,200,001 - 2,200,000 (PKR 30,000 + 15% exceeding 1,200,000)"
            annual_tax = Decimal("30000") + (annual_gross - Decimal("1200000")) * Decimal("0.15")
        elif annual_gross <= Decimal("3200000"):
            slab = 4
            desc = "Slab 4: PKR 2,200,001 - 3,200,000 (PKR 180,000 + 25% exceeding 2,200,000)"
            annual_tax = Decimal("180000") + (annual_gross - Decimal("2200000")) * Decimal("0.25")
        elif annual_gross <= Decimal("4100000"):
            slab = 5
            desc = "Slab 5: PKR 3,200,001 - 4,100,000 (PKR 430,000 + 30% exceeding 3,200,000)"
            annual_tax = Decimal("430000") + (annual_gross - Decimal("3200000")) * Decimal("0.30")
        else:
            slab = 6
            desc = "Slab 6: Exceeding PKR 4,100,000 (PKR 700,000 + 35% exceeding 4,100,000)"
            annual_tax = Decimal("700000") + (annual_gross - Decimal("4100000")) * Decimal("0.35")
    else:
        # Finance Act 2023 (Tax Year 2024)
        if annual_gross <= Decimal("600000"):
            slab = 1
            desc = "Slab 1: Up to PKR 600,000 (0%)"
            annual_tax = Decimal("0")
        elif annual_gross <= Decimal("1200000"):
            slab = 2
            desc = "Slab 2: PKR 600,001 - 1,200,000 (2.5% exceeding 600,000)"
            annual_tax = (annual_gross - Decimal("600000")) * Decimal("0.025")
        elif annual_gross <= Decimal("2400000"):
            slab = 3
            desc = "Slab 3: PKR 1,200,001 - 2,400,000 (PKR 15,000 + 12.5% exceeding 1,200,000)"
            annual_tax = Decimal("15000") + (annual_gross - Decimal("1200000")) * Decimal("0.125")
        elif annual_gross <= Decimal("3600000"):
            slab = 4
            desc = "Slab 4: PKR 2,400,001 - 3,600,000 (PKR 165,000 + 22.5% exceeding 2,400,000)"
            annual_tax = Decimal("165000") + (annual_gross - Decimal("2400000")) * Decimal("0.225")
        elif annual_gross <= Decimal("6000000"):
            slab = 5
            desc = "Slab 5: PKR 3,600,001 - 6,000,000 (PKR 435,000 + 27.5% exceeding 3,600,000)"
            annual_tax = Decimal("435000") + (annual_gross - Decimal("3600000")) * Decimal("0.275")
        else:
            slab = 6
            desc = "Slab 6: Exceeding PKR 6,000,000 (PKR 1,095,000 + 35% exceeding 6,000,000)"
            annual_tax = Decimal("1095000") + (annual_gross - Decimal("6000000")) * Decimal("0.35")

    monthly_wht = (annual_tax / Decimal("12")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "slab": slab,
        "slab_description": desc,
        "slab_name": desc,
        "annual_gross": annual_gross,
        "annual_tax": annual_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "monthly_wht": monthly_wht,
        "monthly_tax": monthly_wht,
        "is_taxable": annual_gross > Decimal("600000"),
    }


def verify_salary_slip_tax(
    monthly_gross: Decimal | float | str,
    declared_wht: Decimal | float | str,
    tax_year: int = 2025,
    tolerance_pct: Decimal = Decimal("0.15"),
) -> Section149SalaryTaxResult:
    """
    Statutorily audit a salary slip's declared income tax deduction against Section 149
    of the Income Tax Ordinance, 2001.
    """
    try:
        m_gross = Decimal(str(monthly_gross).replace(",", "")).quantize(Decimal("0.01"))
        d_wht = Decimal(str(declared_wht).replace(",", "")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Section149SalaryTaxResult(
            is_compliant=False,
            monthly_gross=Decimal("0"),
            annual_gross=Decimal("0"),
            tax_year=tax_year,
            applicable_slab=0,
            slab_description="Invalid financial parameters",
            statutory_annual_tax=Decimal("0"),
            expected_monthly_wht=Decimal("0"),
            declared_monthly_wht=Decimal("0"),
            discrepancy_amount=Decimal("0"),
            discrepancy_percentage=Decimal("0"),
            rule_id="RULE_FBR_WHT_INVALID_AMOUNTS",
            severity="HIGH",
            narrative="Unable to parse salary slip monetary amounts for tax audit.",
        )

    calc = calculate_expected_salary_wht(m_gross, tax_year)
    exp_wht = calc["monthly_wht"]
    slab = calc["slab"]
    desc = calc["slab_description"]
    ann_tax = calc["annual_tax"]
    ann_gross = calc["annual_gross"]

    # Discrepancy metrics
    diff = d_wht - exp_wht
    abs_diff = abs(diff)
    if exp_wht > Decimal("0"):
        pct_diff = (abs_diff / exp_wht).quantize(Decimal("0.001"))
    else:
        pct_diff = Decimal("1.0") if d_wht > Decimal("0") else Decimal("0.0")

    # Case 1: Taxable Salary (> PKR 50,000 / mo), but ZERO tax was deducted!
    if m_gross > Decimal("50000") and exp_wht > Decimal("0") and d_wht == Decimal("0"):
        return Section149SalaryTaxResult(
            is_compliant=False,
            monthly_gross=m_gross,
            annual_gross=ann_gross,
            tax_year=tax_year,
            applicable_slab=slab,
            slab_description=desc,
            statutory_annual_tax=ann_tax,
            expected_monthly_wht=exp_wht,
            declared_monthly_wht=d_wht,
            discrepancy_amount=diff,
            discrepancy_percentage=pct_diff,
            rule_id="RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY",
            severity="CRITICAL",
            narrative=(
                f"Statutory Tax Evasion / Forged Payslip: Employee declared Gross Salary of "
                f"PKR {m_gross:,.2f}/month (Annual: PKR {ann_gross:,.2f}) under FBR Tax Year {tax_year} "
                f"Slab {slab}, requiring statutory monthly tax deduction of PKR {exp_wht:,.2f} under "
                f"Section 149 of ITO 2001. However, ZERO tax deduction was recorded."
            ),
        )

    # Case 2: Significant under-deduction or over-deduction exceeding tolerance
    if exp_wht > Decimal("0") and pct_diff > tolerance_pct:
        return Section149SalaryTaxResult(
            is_compliant=False,
            monthly_gross=m_gross,
            annual_gross=ann_gross,
            tax_year=tax_year,
            applicable_slab=slab,
            slab_description=desc,
            statutory_annual_tax=ann_tax,
            expected_monthly_wht=exp_wht,
            declared_monthly_wht=d_wht,
            discrepancy_amount=diff,
            discrepancy_percentage=pct_diff,
            rule_id="RULE_FBR_WHT_DISCREPANCY",
            severity="HIGH",
            narrative=(
                f"Section 149 WHT Discrepancy: Declared tax of PKR {d_wht:,.2f} deviates by "
                f"{pct_diff:.1%} from statutory monthly liability of PKR {exp_wht:,.2f} "
                f"(Slab {slab}: {desc})."
            ),
        )

    # Case 3: Compliant salary tax deduction
    return Section149SalaryTaxResult(
        is_compliant=True,
        monthly_gross=m_gross,
        annual_gross=ann_gross,
        tax_year=tax_year,
        applicable_slab=slab,
        slab_description=desc,
        statutory_annual_tax=ann_tax,
        expected_monthly_wht=exp_wht,
        declared_monthly_wht=d_wht,
        discrepancy_amount=diff,
        discrepancy_percentage=pct_diff,
        rule_id="RULE_FBR_WHT_VERIFIED",
        severity="INFO",
        narrative=(
            f"FBR Section 149 Salaried Withholding Tax Verified: Declared tax (PKR {d_wht:,.2f}) "
            f"strictly conforms to statutory progressive tax slab {slab} ({desc}) for Tax Year {tax_year}."
        ),
    )


def validate_cpr_structure(cpr_str: str) -> CPRVerificationResult:
    """
    Validate an FBR Computerized Payment Receipt (CPR) number.
    Formats:
      - CPR-YYYYMMDD-XXXX-XXXXXXX (e-Payment CPR, 24 characters)
      - IT-YYYY-XXXXXXXX (Income Tax Challan)
      - ST-YYYY-XXXXXXXX (Sales Tax Challan)
      - FED-YYYY-XXXXXXXX (Federal Excise Duty Challan)
    """
    if not cpr_str:
        return CPRVerificationResult(
            is_valid=False,
            cpr_number="",
            receipt_type="UNKNOWN",
            tax_year=None,
            payment_date=None,
            is_future_date=False,
            rule_id="RULE_FBR_CPR_FORMAT_INVALID",
            error_message="Empty CPR provided",
        )

    clean = cpr_str.strip().upper()
    now_utc = datetime.now(timezone.utc)
    current_year = now_utc.year

    # 1. Standard date-based CPR (CPR-YYYYMMDD-XXXX-XXXXXXX or IT-YYYYMMDD-XXXX-XXXXXXX)
    m_std = re.match(r"^(CPR|IT|ST|FED)[-_]?(\d{4})(\d{2})(\d{2})[-_]?([A-Z0-9]{4})?[-_]?([A-Z0-9]{6,10})$", clean)
    if m_std:
        prefix, yyyy, mm, dd, head, serial = m_std.groups()
        try:
            p_date = datetime(int(yyyy), int(mm), int(dd), tzinfo=timezone.utc)
            is_future = p_date > now_utc
            tax_yr = int(yyyy) if int(mm) <= 6 else int(yyyy) + 1
            r_type = "INCOME_TAX_CPR" if prefix == "IT" or head == "0101" else ("SALES_TAX_CPR" if prefix == "ST" else ("FED_CPR" if prefix == "FED" else "GENERIC_CPR"))

            if is_future:
                return CPRVerificationResult(
                    is_valid=False,
                    cpr_number=clean,
                    receipt_type=r_type,
                    tax_year=tax_yr,
                    payment_date=f"{yyyy}-{mm}-{dd}",
                    is_future_date=True,
                    rule_id="RULE_FBR_CPR_FUTURE_DATE",
                    error_message=f"FBR CPR payment date ({yyyy}-{mm}-{dd}) is post-dated / in the future.",
                )

            return CPRVerificationResult(
                is_valid=True,
                cpr_number=clean,
                receipt_type=r_type,
                tax_year=tax_yr,
                payment_date=f"{yyyy}-{mm}-{dd}",
                is_future_date=False,
                rule_id="RULE_FBR_CPR_VERIFIED",
            )
        except ValueError:
            return CPRVerificationResult(
                is_valid=False,
                cpr_number=clean,
                receipt_type="GENERIC_CPR",
                tax_year=None,
                payment_date=None,
                is_future_date=False,
                rule_id="RULE_FBR_CPR_FORMAT_INVALID",
                error_message="Invalid calendar date inside CPR number.",
            )

    # 2. Tax Head CPR (IT-YYYY-XXXXXX, ST-YYYY-XXXXXX)
    m_head = re.match(r"^(IT|ST|FED)[-_]?(\d{4})[-_]?([A-Z0-9]{6,14})$", clean)
    if m_head:
        head_type, yyyy, serial = m_head.groups()
        yr = int(yyyy)
        is_future = yr > (current_year + 1)
        r_type = "INCOME_TAX" if head_type == "IT" else ("SALES_TAX" if head_type == "ST" else "FED")

        if is_future:
            return CPRVerificationResult(
                is_valid=False,
                cpr_number=clean,
                receipt_type=r_type,
                tax_year=yr,
                payment_date=None,
                is_future_date=True,
                rule_id="RULE_FBR_CPR_FUTURE_DATE",
                error_message=f"FBR CPR Tax Year ({yr}) is in the future.",
            )

        if yr < 2005:
            return CPRVerificationResult(
                is_valid=False,
                cpr_number=clean,
                receipt_type=r_type,
                tax_year=yr,
                payment_date=None,
                is_future_date=False,
                rule_id="RULE_FBR_CPR_FORMAT_INVALID",
                error_message=f"FBR CPR Tax Year ({yr}) precedes e-filing system inception (2005).",
            )

        return CPRVerificationResult(
            is_valid=True,
            cpr_number=clean,
            receipt_type=r_type,
            tax_year=yr,
            payment_date=None,
            is_future_date=False,
            rule_id="RULE_FBR_CPR_VERIFIED",
        )

    # 3. Generic CPR fallback
    if clean.startswith("CPR") and len(re.sub(r"\W", "", clean)) >= 10:
        return CPRVerificationResult(
            is_valid=True,
            cpr_number=clean,
            receipt_type="GENERIC_CPR",
            tax_year=None,
            payment_date=None,
            is_future_date=False,
            rule_id="RULE_FBR_CPR_VERIFIED",
        )

    return CPRVerificationResult(
        is_valid=False,
        cpr_number=cpr_str,
        receipt_type="UNKNOWN",
        tax_year=None,
        payment_date=None,
        is_future_date=False,
        rule_id="RULE_FBR_CPR_FORMAT_INVALID",
        error_message=f"CPR number '{cpr_str}' does not match standard FBR e-Payment or Challan structure.",
    )


def audit_fbr_tax_compliance(
    doc_text: str,
    doc_type: str = "SALARY_SLIP",
    declared_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Orchestrate full FBR tax compliance and fraud examination across a document.
    """
    declared = declared_data or {}
    findings: list[dict[str, Any]] = []

    ntn_results: list[dict[str, Any]] = []
    cpr_results: list[dict[str, Any]] = []
    salary_tax_result: Optional[dict[str, Any]] = None

    # 1. NTN Discovery and Validation
    raw_ntns = set()
    for m in NTN_FORMAT_REGEX.finditer(doc_text):
        raw_ntns.add(f"{m.group(1)}-{m.group(2)}")
    for m in NTN_LABELED_REGEX.finditer(doc_text):
        raw_ntns.add(m.group(1))

    if declared.get("ntn"):
        raw_ntns.add(str(declared["ntn"]))

    for ntn_str in raw_ntns:
        res = validate_ntn_structure(ntn_str)
        ntn_results.append(asdict(res))
        if not res.is_valid:
            findings.append({
                "rule_id": res.rule_id,
                "severity": "CRITICAL" if "CHECK_DIGIT" in res.rule_id else "HIGH",
                "risk_points": 50 if "CHECK_DIGIT" in res.rule_id else 30,
                "title": f"Invalid FBR National Tax Number (NTN): {res.formatted}",
                "description": res.error_message,
                "expected": f"Modulus 11 check digit {res.expected_check_digit}" if res.expected_check_digit else "Valid 8-digit NTN",
                "actual": f"Found check digit {res.check_digit}",
            })
        else:
            findings.append({
                "rule_id": "RULE_FBR_NTN_VERIFIED",
                "severity": "INFO",
                "risk_points": 0,
                "title": f"FBR National Tax Number (NTN) Verified: {res.formatted}",
                "description": f"NTN satisfies official FBR Modulus 11 check digit ({res.entity_type}).",
                "expected": "Valid registered NTN",
                "actual": res.formatted,
            })

    # 2. CPR Discovery and Validation
    raw_cprs = set()
    for m in CPR_REGEX.finditer(doc_text):
        raw_cprs.add(m.group(1))

    if declared.get("cpr"):
        raw_cprs.add(str(declared["cpr"]))

    for cpr_str in raw_cprs:
        cpr_res = validate_cpr_structure(cpr_str)
        cpr_results.append(asdict(cpr_res))
        if not cpr_res.is_valid:
            findings.append({
                "rule_id": cpr_res.rule_id,
                "severity": "CRITICAL" if "FUTURE" in cpr_res.rule_id else "HIGH",
                "risk_points": 70 if "FUTURE" in cpr_res.rule_id else 40,
                "title": f"FBR CPR Validation Anomaly: {cpr_res.cpr_number}",
                "description": cpr_res.error_message,
                "expected": "Valid historical e-Payment CPR",
                "actual": cpr_res.cpr_number,
            })
        else:
            findings.append({
                "rule_id": "RULE_FBR_CPR_VERIFIED",
                "severity": "INFO",
                "risk_points": 0,
                "title": f"FBR Computerized Payment Receipt (CPR) Verified: {cpr_res.cpr_number}",
                "description": f"Valid {cpr_res.receipt_type} receipt structure.",
                "expected": "Valid CPR",
                "actual": cpr_res.cpr_number,
            })

    # 3. Salary Slip Section 149 WHT Reconciliation
    if doc_type in ("SALARY_SLIP", "PAYSLIP", "EMPLOYMENT_LETTER") or GROSS_SALARY_REGEX.search(doc_text):
        gross_val = None
        tax_val = None

        if declared.get("monthly_gross") is not None:
            gross_val = declared["monthly_gross"]
        else:
            g_match = GROSS_SALARY_REGEX.search(doc_text)
            if g_match:
                gross_val = g_match.group(1).replace(",", "")

        if declared.get("monthly_wht") is not None:
            tax_val = declared["monthly_wht"]
        else:
            t_match = TAX_DEDUCTION_REGEX.search(doc_text)
            if t_match:
                tax_val = t_match.group(1).replace(",", "")
            else:
                if gross_val:
                    tax_val = "0"

        if gross_val is not None and tax_val is not None:
            tax_yr = declared.get("tax_year", 2025)
            s_audit = verify_salary_slip_tax(gross_val, tax_val, tax_year=tax_yr)
            salary_tax_result = asdict(s_audit)
            for k, v in salary_tax_result.items():
                if isinstance(v, Decimal):
                    salary_tax_result[k] = float(v)

            if not s_audit.is_compliant:
                findings.append({
                    "rule_id": s_audit.rule_id,
                    "severity": s_audit.severity,
                    "risk_points": 60 if s_audit.rule_id == "RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY" else 40,
                    "title": (
                        "Section 149 WHT Violation: Zero Tax on Taxable Salary"
                        if s_audit.rule_id == "RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY"
                        else "Section 149 Withholding Tax Discrepancy"
                    ),
                    "description": s_audit.narrative,
                    "expected": f"Monthly WHT PKR {s_audit.expected_monthly_wht:,.2f} (Slab {s_audit.applicable_slab})",
                    "actual": f"Declared monthly tax PKR {s_audit.declared_monthly_wht:,.2f}",
                })
            else:
                findings.append({
                    "rule_id": "RULE_FBR_WHT_VERIFIED",
                    "severity": "INFO",
                    "risk_points": 0,
                    "title": "FBR Section 149 Salaried Tax Deduction Verified",
                    "description": s_audit.narrative,
                    "expected": f"PKR {s_audit.expected_monthly_wht:,.2f}",
                    "actual": f"PKR {s_audit.declared_monthly_wht:,.2f}",
                })

    is_compliant = not any(f["severity"] in ("CRITICAL", "HIGH") for f in findings)

    overall_status = "COMPLIANT"
    if any(f.get("rule_id") == "RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY" for f in findings):
        overall_status = "TAX_EVASION_SUSPECTED"
    elif any(f.get("severity") == "CRITICAL" for f in findings):
        overall_status = "NON_COMPLIANT"
    elif any(f.get("severity") == "HIGH" for f in findings):
        overall_status = "DISCREPANCY_DETECTED"
    elif not findings:
        overall_status = "NO_TAX_DATA_FOUND"

    primary_ntn = ntn_results[0] if ntn_results else None
    primary_cpr = cpr_results[0] if cpr_results else None

    # Map wht_audit keys for frontend and downstream consumers
    wht_audit_data = None
    if salary_tax_result:
        wht_audit_data = dict(salary_tax_result)
        wht_audit_data["declared_wht"] = float(salary_tax_result.get("declared_monthly_wht", 0))
        wht_audit_data["expected_monthly_wht"] = float(salary_tax_result.get("expected_monthly_wht", 0))
        wht_audit_data["monthly_discrepancy"] = float(salary_tax_result.get("discrepancy_amount", 0))
        wht_audit_data["slab_name"] = salary_tax_result.get("slab_description", "")
        wht_audit_data["slab_formula"] = salary_tax_result.get("narrative", "")
        wht_audit_data["status"] = "ZERO_TAX_VIOLATION" if salary_tax_result.get("rule_id") == "RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY" else ("DISCREPANCY" if salary_tax_result.get("rule_id") == "RULE_FBR_WHT_DISCREPANCY" else "COMPLIANT")
        wht_audit_data["is_taxable"] = float(salary_tax_result.get("monthly_gross", 0)) > 50000

    return {
        "overall_status": overall_status,
        "is_compliant": is_compliant,
        "document_type": doc_type,
        "ntn_result": primary_ntn,
        "wht_audit": wht_audit_data,
        "cpr_result": primary_cpr,
        "ntn_validations": ntn_results,
        "cpr_validations": cpr_results,
        "salary_tax_audit": salary_tax_result,
        "findings": findings,
    }
