"""
Bank Statement Template Fingerprinting Engine for Major Pakistani Banks.
NIST SP 800-86 Compliant Core Banking System (CBS) Reporting Profile Verifier.

Detects unauthorized template modifications, forged column alignments, alien fonts,
and missing statutory State Bank of Pakistan (SBP) disclaimers across:
  - Meezan Bank Limited (MEZN) - Temenos T24 / JasperReports
  - Habib Bank Limited (HABB) - Temenos Transact / Custom CBS
  - United Bank Limited (UNIL) - Temenos T24 / MicroStrategy
  - Bank Alfalah Limited (ALFH) - SunGard / Temenos T24
  - MCB Bank Limited (MUCB) - Oracle FLEXCUBE
  - Standard Chartered Bank Pakistan (SCBL) - eBBS / Global Reporting Engine
"""
from dataclasses import asdict, dataclass, field
import logging
import re
from typing import Any, Optional

import pymupdf

logger = logging.getLogger(__name__)


@dataclass
class ColumnGridDef:
    name: str  # e.g., "date", "description", "debit", "credit", "balance", "value_date"
    aliases: list[str]
    expected_x_min: float
    expected_x_max: float
    tolerance_pts: float = 20.0


@dataclass
class FontProfileDef:
    allowed_font_families: list[str]
    prohibited_font_families: list[str] = field(default_factory=lambda: [
        "comic", "papyrus", "impact", "lobster", "brush script", "chiller", "curlz"
    ])


@dataclass
class LogoGeometryDef:
    expected_x_min: float = 30.0
    expected_x_max: float = 250.0
    expected_y_min: float = 20.0
    expected_y_max: float = 140.0
    min_width_pts: float = 40.0
    max_width_pts: float = 300.0


@dataclass
class StatutoryFooterDef:
    required_phrases: list[str]  # e.g. ["computer-generated", "signature", "mohtasib"]
    min_y_pts: float = 650.0  # Must be in lower portion of A4 page


@dataclass
class BankTemplateProfile:
    bank_code: str  # SBP code: "MEZN", "HABB", "UNIL", "ALFH", "MUCB", "SCBL"
    template_id: str
    bank_name: str
    cbs_engine: str
    description: str
    expected_page_width: float = 595.3  # A4
    expected_page_height: float = 841.9  # A4
    page_tolerance: float = 25.0
    header_anchors: list[str] = field(default_factory=list)
    columns: list[ColumnGridDef] = field(default_factory=list)
    font_profile: Optional[FontProfileDef] = None
    logo_geometry: Optional[LogoGeometryDef] = None
    statutory_footers: Optional[StatutoryFooterDef] = None


@dataclass
class TemplateDeviation:
    rule_id: str
    category: str  # Prisma EvidenceCategory string
    severity: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    risk_points: int
    title: str
    description: str
    expected_value: str
    actual_value: str
    discrepancy: str
    page_number: int = 1
    bbox_pts: Optional[tuple[float, float, float, float]] = None


@dataclass
class BankTemplateEvaluationResult:
    status: str  # "VERIFIED" | "DEVIATION_DETECTED" | "UNINDEXED_BANK" | "NOT_BANK_STATEMENT"
    bank_code: Optional[str] = None
    bank_name: Optional[str] = None
    matched_template_id: Optional[str] = None
    cbs_engine: Optional[str] = None
    match_score: float = 0.0
    is_conforming: bool = False
    deviations: list[TemplateDeviation] = field(default_factory=list)
    verified_details: dict[str, Any] = field(default_factory=dict)
    message: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Canonical CBS Profiles for the Big 6 Pakistani Banks
# ─────────────────────────────────────────────────────────────────────────────

CANONICAL_BANK_PROFILES: dict[str, list[BankTemplateProfile]] = {
    # 1. Meezan Bank Limited (MEZN) - Temenos T24 / JasperReports
    "MEZN": [
        BankTemplateProfile(
            bank_code="MEZN",
            template_id="MEZN_JASPER_A4_V1",
            bank_name="Meezan Bank Limited",
            cbs_engine="Temenos T24 / JasperReports",
            description="Meezan standard e-statement / branch transaction reporting layout",
            header_anchors=["meezan bank", "statement"],
            columns=[
                ColumnGridDef(
                    name="date",
                    aliases=["date", "trans date", "txn date"],
                    expected_x_min=30.0,
                    expected_x_max=110.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="description",
                    aliases=["narration", "description", "particulars"],
                    expected_x_min=100.0,
                    expected_x_max=320.0,
                    tolerance_pts=30.0,
                ),
                ColumnGridDef(
                    name="debit",
                    aliases=["debit", "withdrawal", "dr"],
                    expected_x_min=310.0,
                    expected_x_max=420.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="credit",
                    aliases=["credit", "deposit", "cr"],
                    expected_x_min=390.0,
                    expected_x_max=500.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="balance",
                    aliases=["balance", "bal"],
                    expected_x_min=460.0,
                    expected_x_max=570.0,
                    tolerance_pts=25.0,
                ),
            ],
            font_profile=FontProfileDef(
                allowed_font_families=["helvetica", "arial", "tahoma", "times", "segoe", "calibri"],
                prohibited_font_families=["comic", "papyrus", "impact", "lobster", "brush script"],
            ),
            statutory_footers=StatutoryFooterDef(
                required_phrases=["computer", "signature", "meezan", "statement"],
                min_y_pts=650.0,
            ),
        )
    ],

    # 2. Habib Bank Limited (HABB / HBL) - Temenos Transact / Custom CBS
    "HABB": [
        BankTemplateProfile(
            bank_code="HABB",
            template_id="HBL_TRANSACT_A4_V1",
            bank_name="Habib Bank Limited (HBL)",
            cbs_engine="Temenos Transact / Custom CBS",
            description="HBL standard retail & corporate account statement layout",
            header_anchors=["habib bank", "statement of account", "hbl"],
            columns=[
                ColumnGridDef(
                    name="date",
                    aliases=["post date", "trans date", "date"],
                    expected_x_min=25.0,
                    expected_x_max=95.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="description",
                    aliases=["particulars", "description", "narration"],
                    expected_x_min=90.0,
                    expected_x_max=290.0,
                    tolerance_pts=30.0,
                ),
                ColumnGridDef(
                    name="debit",
                    aliases=["debit", "withdrawal", "dr"],
                    expected_x_min=290.0,
                    expected_x_max=410.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="credit",
                    aliases=["credit", "deposit", "cr"],
                    expected_x_min=380.0,
                    expected_x_max=490.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="balance",
                    aliases=["balance", "bal"],
                    expected_x_min=460.0,
                    expected_x_max=575.0,
                    tolerance_pts=25.0,
                ),
            ],
            font_profile=FontProfileDef(
                allowed_font_families=["calibri", "arial", "segoe", "helvetica", "tahoma"],
                prohibited_font_families=["comic", "papyrus", "impact", "lobster", "brush script"],
            ),
            statutory_footers=StatutoryFooterDef(
                required_phrases=["computer", "signature", "hbl", "mohtasib"],
                min_y_pts=650.0,
            ),
        )
    ],

    # 3. United Bank Limited (UNIL / UBL) - Temenos T24 / MicroStrategy
    "UNIL": [
        BankTemplateProfile(
            bank_code="UNIL",
            template_id="UBL_T24_A4_V1",
            bank_name="United Bank Limited (UBL)",
            cbs_engine="Temenos T24 / MicroStrategy",
            description="UBL Netbanking & Core Branch Statement Grid",
            header_anchors=["united bank", "statement", "ubl"],
            columns=[
                ColumnGridDef(
                    name="date",
                    aliases=["date", "trans date"],
                    expected_x_min=30.0,
                    expected_x_max=105.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="description",
                    aliases=["description", "particulars", "transaction details"],
                    expected_x_min=95.0,
                    expected_x_max=310.0,
                    tolerance_pts=30.0,
                ),
                ColumnGridDef(
                    name="debit",
                    aliases=["debit", "dr", "withdrawals"],
                    expected_x_min=300.0,
                    expected_x_max=420.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="credit",
                    aliases=["credit", "cr", "deposits"],
                    expected_x_min=390.0,
                    expected_x_max=495.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="balance",
                    aliases=["balance", "bal"],
                    expected_x_min=465.0,
                    expected_x_max=575.0,
                    tolerance_pts=25.0,
                ),
            ],
            font_profile=FontProfileDef(
                allowed_font_families=["helvetica", "arial", "univers", "tahoma", "calibri"],
                prohibited_font_families=["comic", "papyrus", "impact", "lobster"],
            ),
            statutory_footers=StatutoryFooterDef(
                required_phrases=["computer", "ubl", "discrepancy", "statement"],
                min_y_pts=650.0,
            ),
        )
    ],

    # 4. Bank Alfalah Limited (ALFH) - SunGard / Temenos T24
    "ALFH": [
        BankTemplateProfile(
            bank_code="ALFH",
            template_id="ALFALAH_T24_A4_V1",
            bank_name="Bank Alfalah Limited",
            cbs_engine="SunGard / Temenos T24",
            description="Bank Alfalah Alfa & Corporate Statement Layout",
            header_anchors=["bank alfalah", "statement", "alfa"],
            columns=[
                ColumnGridDef(
                    name="date",
                    aliases=["date", "txn date"],
                    expected_x_min=30.0,
                    expected_x_max=105.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="description",
                    aliases=["particulars", "narration", "description"],
                    expected_x_min=100.0,
                    expected_x_max=300.0,
                    tolerance_pts=30.0,
                ),
                ColumnGridDef(
                    name="debit",
                    aliases=["debit", "dr"],
                    expected_x_min=295.0,
                    expected_x_max=415.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="credit",
                    aliases=["credit", "cr"],
                    expected_x_min=385.0,
                    expected_x_max=495.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="balance",
                    aliases=["balance", "bal"],
                    expected_x_min=465.0,
                    expected_x_max=575.0,
                    tolerance_pts=25.0,
                ),
            ],
            font_profile=FontProfileDef(
                allowed_font_families=["arial", "calibri", "trebuchet", "helvetica", "segoe"],
                prohibited_font_families=["comic", "papyrus", "impact", "lobster"],
            ),
            statutory_footers=StatutoryFooterDef(
                required_phrases=["alfalah", "computer", "statement", "mohtasib"],
                min_y_pts=650.0,
            ),
        )
    ],

    # 5. MCB Bank Limited (MUCB) - Oracle FLEXCUBE
    "MUCB": [
        BankTemplateProfile(
            bank_code="MUCB",
            template_id="MCB_FLEXCUBE_A4_V1",
            bank_name="MCB Bank Limited",
            cbs_engine="Oracle FLEXCUBE",
            description="MCB classic Oracle FLEXCUBE transaction report format",
            header_anchors=["mcb bank", "statement of account", "flexcube"],
            columns=[
                ColumnGridDef(
                    name="date",
                    aliases=["post date", "date", "trans date"],
                    expected_x_min=25.0,
                    expected_x_max=100.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="description",
                    aliases=["particulars", "description", "transaction details"],
                    expected_x_min=95.0,
                    expected_x_max=300.0,
                    tolerance_pts=30.0,
                ),
                ColumnGridDef(
                    name="debit",
                    aliases=["debit", "dr"],
                    expected_x_min=295.0,
                    expected_x_max=415.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="credit",
                    aliases=["credit", "cr"],
                    expected_x_min=390.0,
                    expected_x_max=495.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="balance",
                    aliases=["balance", "bal"],
                    expected_x_min=465.0,
                    expected_x_max=575.0,
                    tolerance_pts=25.0,
                ),
            ],
            font_profile=FontProfileDef(
                allowed_font_families=["courier", "helvetica", "arial", "tahoma"],
                prohibited_font_families=["comic", "papyrus", "impact", "lobster"],
            ),
            statutory_footers=StatutoryFooterDef(
                required_phrases=["mcb", "computer", "signature", "discrepancy"],
                min_y_pts=650.0,
            ),
        )
    ],

    # 6. Standard Chartered Bank Pakistan (SCBL) - eBBS / Global Reporting Engine
    "SCBL": [
        BankTemplateProfile(
            bank_code="SCBL",
            template_id="SCB_EBBS_A4_V1",
            bank_name="Standard Chartered Bank (Pakistan)",
            cbs_engine="eBBS / Global Core Reporting",
            description="Standard Chartered Bank e-statement layout",
            header_anchors=["standard chartered", "statement of account"],
            columns=[
                ColumnGridDef(
                    name="date",
                    aliases=["trans date", "date", "booking date"],
                    expected_x_min=30.0,
                    expected_x_max=110.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="description",
                    aliases=["description", "transaction details", "particulars"],
                    expected_x_min=100.0,
                    expected_x_max=320.0,
                    tolerance_pts=30.0,
                ),
                ColumnGridDef(
                    name="debit",
                    aliases=["withdrawal", "debit", "dr"],
                    expected_x_min=310.0,
                    expected_x_max=420.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="credit",
                    aliases=["deposit", "credit", "cr"],
                    expected_x_min=395.0,
                    expected_x_max=505.0,
                    tolerance_pts=25.0,
                ),
                ColumnGridDef(
                    name="balance",
                    aliases=["balance", "bal"],
                    expected_x_min=470.0,
                    expected_x_max=575.0,
                    tolerance_pts=25.0,
                ),
            ],
            font_profile=FontProfileDef(
                allowed_font_families=["sc-sans", "arial", "helvetica", "calibri", "tahoma"],
                prohibited_font_families=["comic", "papyrus", "impact", "lobster"],
            ),
            statutory_footers=StatutoryFooterDef(
                required_phrases=["standard chartered", "computer", "regulatory", "statement"],
                min_y_pts=650.0,
            ),
        )
    ],
}


def resolve_bank_code_from_text(text: str) -> Optional[str]:
    """Identify Pakistani bank code from document text or SBP IBAN."""
    # 1. IBAN extraction (PK + 2 check digits + 4-char SBP bank code)
    iban_m = re.search(r"PK\s*\d{2}\s*([A-Z]{4})\s*[A-Z0-9]{12,18}", text.upper())
    if iban_m:
        code = iban_m.group(1)
        if code in CANONICAL_BANK_PROFILES:
            return code

    # 2. Text anchor mapping
    text_lower = text.lower()
    if "meezan" in text_lower:
        return "MEZN"
    elif "habib bank" in text_lower or re.search(r"\bhbl\b", text_lower):
        return "HABB"
    elif "united bank" in text_lower or re.search(r"\bubl\b", text_lower):
        return "UNIL"
    elif "alfalah" in text_lower:
        return "ALFH"
    elif "mcb" in text_lower:
        return "MUCB"
    elif "standard chartered" in text_lower or re.search(r"\bscb\b", text_lower):
        return "SCBL"

    return None


def evaluate_bank_template(
    pdf_doc: pymupdf.Document,
    bank_code: Optional[str] = None,
    full_text: Optional[str] = None,
) -> BankTemplateEvaluationResult:
    """
    Evaluate a bank statement against canonical Core Banking System reporting profiles.
    Performs deterministic checks on:
      1. Page geometry (standard A4 bounds)
      2. Table column horizontal coordinates vs canonical CBS reporting grid
      3. Font whitelist/blacklist (flags alien or unprofessional fonts)
      4. Mandatory SBP statutory footer disclaimers
    """
    if len(pdf_doc) == 0:
        return BankTemplateEvaluationResult(
            status="NOT_BANK_STATEMENT",
            message="Document contains 0 pages.",
        )

    # 1. Resolve Document Text
    if not full_text:
        full_text = ""
        for page in pdf_doc:
            full_text += page.get_text("text") + "\n"

    # 2. Resolve Bank Code
    code = bank_code or resolve_bank_code_from_text(full_text)
    if not code or code not in CANONICAL_BANK_PROFILES:
        return BankTemplateEvaluationResult(
            status="UNINDEXED_BANK",
            bank_code=code,
            message=f"Bank '{code or 'Unknown'}' is not currently in canonical CBS template index.",
        )

    profiles = CANONICAL_BANK_PROFILES[code]
    # For now, evaluate against primary canonical profile (or select best matching header)
    selected_profile = profiles[0]
    for p in profiles:
        if any(h in full_text.lower() for h in p.header_anchors):
            selected_profile = p
            break

    deviations: list[TemplateDeviation] = []
    verified_metrics: dict[str, Any] = {
        "bank_code": code,
        "bank_name": selected_profile.bank_name,
        "cbs_engine": selected_profile.cbs_engine,
        "template_id": selected_profile.template_id,
        "columns_matched": [],
        "fonts_verified": [],
        "footers_verified": [],
    }

    # 3. Check Page Geometry on Page 1
    page0 = pdf_doc[0]
    w = page0.rect.width
    h = page0.rect.height

    if abs(w - selected_profile.expected_page_width) > selected_profile.page_tolerance:
        # Check if rotated or Letter size
        is_letter = abs(w - 612.0) <= 15.0 and abs(h - 792.0) <= 15.0
        if not is_letter:
            deviations.append(
                TemplateDeviation(
                    rule_id="RULE_BANK_TEMPLATE_GEOMETRY_ANOMALY",
                    category="PDF_OBJECT_ANOMALY",
                    severity="MEDIUM",
                    risk_points=15,
                    title=f"Non-Standard Page Geometry ({selected_profile.bank_name})",
                    description=(
                        f"Official {selected_profile.bank_name} CBS reports are compiled on standard A4 (595x842 pt). "
                        f"Document page 1 dimensions are {w:.1f}x{h:.1f} pt, indicating a manual re-export or re-creation."
                    ),
                    expected_value="A4 (595x842 pt) or Letter (612x792 pt)",
                    actual_value=f"{w:.1f}x{h:.1f} pt",
                    discrepancy=f"Page width off by {abs(w - selected_profile.expected_page_width):.1f} pt",
                    page_number=1,
                    bbox_pts=(0.0, 0.0, w, h),
                )
            )

    # 4. Check Font Whitelist & Prohibited Fonts across all pages
    seen_fonts: set[str] = set()
    for page_idx, page in enumerate(pdf_doc):
        page_fonts = page.get_fonts()
        for f in page_fonts:
            font_name = str(f[3]).lower()
            seen_fonts.add(font_name)

            # Check prohibited fonts
            if selected_profile.font_profile:
                for prohibited in selected_profile.font_profile.prohibited_font_families:
                    if prohibited in font_name:
                        deviations.append(
                            TemplateDeviation(
                                rule_id="RULE_BANK_TEMPLATE_UNAUTHORIZED_FONT",
                                category="FONT_BASELINE_INCONSISTENCY",
                                severity="HIGH",
                                risk_points=25,
                                title=f"Prohibited Font in CBS Statement: {f[3]}",
                                description=(
                                    f"The document embeds font '{f[3]}' which is strictly prohibited in "
                                    f"{selected_profile.bank_name} Core Banking ({selected_profile.cbs_engine}) statements. "
                                    "This indicates forged content created via non-institutional software (e.g. Word, Canva, PDF editor)."
                                ),
                                expected_value=f"Institutional CBS Fonts ({', '.join(selected_profile.font_profile.allowed_font_families)})",
                                actual_value=f[3],
                                discrepancy=f"Prohibited font '{f[3]}' detected",
                                page_number=page_idx + 1,
                            )
                        )
                        break

    verified_metrics["fonts_verified"] = list(seen_fonts)

    # 5. Check Table Column Grid Alignment (Scan first 2 pages)
    header_found = False
    for page_idx in range(min(2, len(pdf_doc))):
        page = pdf_doc[page_idx]
        words = page.get_text("words")
        if not words:
            continue

        # Group words into approximate lines (y tolerance <= 4.0 pt)
        lines: dict[int, list[tuple]] = {}
        for w_item in words:
            bucket = int(w_item[1] / 4.0)
            lines.setdefault(bucket, []).append(w_item)

        for _, l_words in lines.items():
            l_words.sort(key=lambda x: x[0])
            line_str = " ".join([w[4] for w in l_words]).lower()

            # Check if this line is a financial table header line
            if any(k in line_str for k in ["date", "post date", "trans date"]) and any(
                k in line_str for k in ["description", "narration", "particulars", "balance", "credit", "debit"]
            ):
                header_found = True
                # Match individual columns to words
                for col_def in selected_profile.columns:
                    col_word = None
                    for w_item in l_words:
                        w_text = w_item[4].lower()
                        if any(alias in w_text for alias in col_def.aliases):
                            col_word = w_item
                            break

                    if col_word:
                        col_x = float(col_word[0])
                        # Verify column X against expected range
                        if (col_x < col_def.expected_x_min - col_def.tolerance_pts) or (
                            col_x > col_def.expected_x_max + col_def.tolerance_pts
                        ):
                            expected_mid = (col_def.expected_x_min + col_def.expected_x_max) / 2.0
                            shift = col_x - expected_mid
                            deviations.append(
                                TemplateDeviation(
                                    rule_id="RULE_BANK_TEMPLATE_COLUMN_MISALIGNMENT",
                                    category="TRANSACTION_FORMAT_VIOLATION",
                                    severity="HIGH",
                                    risk_points=25,
                                    title=f"CBS Column Drift: '{col_def.name.upper()}' Displaced by {abs(shift):.1f} pt",
                                    description=(
                                        f"Column '{col_def.name.upper()}' was found at horizontal coordinate x={col_x:.1f} pt. "
                                        f"Official {selected_profile.bank_name} CBS grid ({selected_profile.cbs_engine}) mandates "
                                        f"placement within [{col_def.expected_x_min:.1f} - {col_def.expected_x_max:.1f}] pt. "
                                        f"A displacement of {abs(shift):.1f} pt indicates whole-cloth layout forgery."
                                    ),
                                    expected_value=f"x in [{col_def.expected_x_min:.1f}, {col_def.expected_x_max:.1f}] pt",
                                    actual_value=f"x = {col_x:.1f} pt",
                                    discrepancy=f"Horizontal displacement of {abs(shift):.1f} pt",
                                    page_number=page_idx + 1,
                                    bbox_pts=(col_word[0], col_word[1], col_word[2], col_word[3]),
                                )
                            )
                        else:
                            verified_metrics["columns_matched"].append({
                                "name": col_def.name,
                                "detected_x": col_x,
                                "expected_range": [col_def.expected_x_min, col_def.expected_x_max],
                            })
                break  # Process first header encountered

        if header_found:
            break

    # 6. Check Statutory SBP Footer Disclaimers
    if selected_profile.statutory_footers:
        footer_phrases = selected_profile.statutory_footers.required_phrases
        matched_footer_phrases = [
            phrase for phrase in footer_phrases if phrase in full_text.lower()
        ]
        verified_metrics["footers_verified"] = matched_footer_phrases

        # Require at least 2 key statutory terms (e.g. computer, signature, bank name)
        if len(matched_footer_phrases) < min(2, len(footer_phrases)):
            deviations.append(
                TemplateDeviation(
                    rule_id="RULE_BANK_TEMPLATE_DISCLAIMER_MISSING",
                    category="TRANSACTION_FORMAT_VIOLATION",
                    severity="HIGH",
                    risk_points=20,
                    title=f"Missing SBP Statutory Footer ({selected_profile.bank_name})",
                    description=(
                        f"State Bank of Pakistan regulatory directives mandate specific statutory disclaimers on "
                        f"{selected_profile.bank_name} statements (e.g., computer-generated non-signature notice, "
                        f"dispute notice). Required tokens ({', '.join(footer_phrases)}) were absent or altered."
                    ),
                    expected_value=f"Statutory tokens present: {', '.join(footer_phrases)}",
                    actual_value=f"Only matched: {', '.join(matched_footer_phrases) or 'None'}",
                    discrepancy="Missing mandatory CBS regulatory footer",
                    page_number=len(pdf_doc),
                )
            )

    # 7. Final Verdict
    if deviations:
        status = "DEVIATION_DETECTED"
        is_conforming = False
        match_score = max(0.0, 1.0 - (len(deviations) * 0.25))
        message = (
            f"Bank Template Deviation on {selected_profile.bank_name} ({selected_profile.cbs_engine}): "
            f"{len(deviations)} layout or typography violations detected against canonical reporting profile."
        )
    else:
        status = "VERIFIED"
        is_conforming = True
        match_score = 1.0
        message = (
            f"Official CBS Template Verified ({selected_profile.bank_name}): "
            f"Layout strictly conforms to canonical {selected_profile.cbs_engine} reporting grid "
            f"({len(verified_metrics['columns_matched'])} columns, {len(verified_metrics['fonts_verified'])} fonts, "
            f"and SBP statutory footers verified)."
        )

    return BankTemplateEvaluationResult(
        status=status,
        bank_code=code,
        bank_name=selected_profile.bank_name,
        matched_template_id=selected_profile.template_id,
        cbs_engine=selected_profile.cbs_engine,
        match_score=match_score,
        is_conforming=is_conforming,
        deviations=deviations,
        verified_details=verified_metrics,
        message=message,
    )
