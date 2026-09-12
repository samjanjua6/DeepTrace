"""
Unit tests for Pakistani Bank Statement Template Fingerprinting Engine.
Validates CBS reporting grid verification across Meezan, HBL, UBL, Alfalah, MCB, and SCB,
including detection of column drift, unauthorized fonts, and missing statutory footers.
"""
import pytest
import pymupdf

from app.features.pipeline.tasks.bank_template_fingerprints import (
    CANONICAL_BANK_PROFILES,
    BankTemplateEvaluationResult,
    evaluate_bank_template,
    resolve_bank_code_from_text,
)


def create_mock_bank_statement_pdf(
    header_text: str,
    table_columns: list[tuple[float, str]],  # (x_coord, text)
    body_rows: list[list[tuple[float, str]]],
    footer_text: str = "",
    font_name: str = "helv",
    page_width: float = 595.0,
    page_height: float = 842.0,
) -> pymupdf.Document:
    """Helper to synthesize an in-memory PDF mimicking a bank statement."""
    doc = pymupdf.open()
    page = doc.new_page(width=page_width, height=page_height)

    # Header
    page.insert_text(pymupdf.Point(50, 60), header_text, fontname=font_name, fontsize=12)

    # Column Headers at y=150
    for x, text in table_columns:
        page.insert_text(pymupdf.Point(x, 150), text, fontname=font_name, fontsize=9)

    # Body rows
    y = 180
    for row in body_rows:
        for x, text in row:
            page.insert_text(pymupdf.Point(x, y), text, fontname=font_name, fontsize=8)
        y += 20

    # Footer at y=750
    if footer_text:
        page.insert_text(pymupdf.Point(50, 750), footer_text, fontname=font_name, fontsize=8)

    return doc


class TestBankTemplateFingerprinting:
    """Test suite for CBS reporting template verification."""

    def test_resolve_bank_code_from_iban_and_text(self):
        """Verify bank resolution from IBAN and document text."""
        assert resolve_bank_code_from_text("IBAN: PK36MEZN00010201020304") == "MEZN"
        assert resolve_bank_code_from_text("Habib Bank Limited account statement") == "HABB"
        assert resolve_bank_code_from_text("United Bank Limited (UBL)") == "UNIL"
        assert resolve_bank_code_from_text("Bank Alfalah Alfa e-statement") == "ALFH"
        assert resolve_bank_code_from_text("MCB Bank FLEXCUBE report") == "MUCB"
        assert resolve_bank_code_from_text("Standard Chartered Bank (Pakistan)") == "SCBL"
        assert resolve_bank_code_from_text("Unknown foreign entity") is None

    def test_meezan_conforming_template_verified(self):
        """A genuine Meezan Bank statement matching canonical JasperReports grid is verified."""
        columns = [
            (50.0, "Date"),
            (140.0, "Narration"),
            (350.0, "Debit (PKR)"),
            (430.0, "Credit (PKR)"),
            (500.0, "Balance (PKR)"),
        ]
        body = [
            [(50.0, "01/03/2026"), (140.0, "Salary Transfer"), (430.0, "150,000.00"), (500.0, "250,000.00")],
        ]
        doc = create_mock_bank_statement_pdf(
            header_text="MEEZAN BANK LIMITED - STATEMENT OF ACCOUNT\nIBAN: PK36MEZN00010201020304",
            table_columns=columns,
            body_rows=body,
            footer_text="This is a computer-generated statement of Meezan Bank and does not require a signature.",
        )

        res = evaluate_bank_template(doc, bank_code="MEZN")
        assert res.status == "VERIFIED"
        assert res.is_conforming is True
        assert res.bank_code == "MEZN"
        assert res.match_score == 1.0
        assert len(res.deviations) == 0
        assert "Official CBS Template Verified (Meezan Bank Limited)" in res.message
        doc.close()

    def test_detect_column_misalignment_drift(self):
        """Displacing Debit/Credit columns by 40+ points flags RULE_BANK_TEMPLATE_COLUMN_MISALIGNMENT."""
        # Forged layout: Debit placed at x=200 instead of [310, 420], Credit placed at x=280 instead of [390, 500]
        columns = [
            (50.0, "Date"),
            (110.0, "Narration"),
            (200.0, "Debit"),  # Severe drift: canonical expects [310, 420]
            (280.0, "Credit"), # Severe drift: canonical expects [390, 500]
            (480.0, "Balance"),
        ]
        body = [
            [(50.0, "01/03/2026"), (110.0, "Transfer"), (200.0, "5,000.00"), (480.0, "45,000.00")],
        ]
        doc = create_mock_bank_statement_pdf(
            header_text="MEEZAN BANK LIMITED - STATEMENT\nIBAN: PK36MEZN00010201020304",
            table_columns=columns,
            body_rows=body,
            footer_text="This is a computer-generated statement of Meezan Bank and does not require a signature.",
        )

        res = evaluate_bank_template(doc, bank_code="MEZN")
        assert res.status == "DEVIATION_DETECTED"
        assert res.is_conforming is False

        col_deviations = [d for d in res.deviations if d.rule_id == "RULE_BANK_TEMPLATE_COLUMN_MISALIGNMENT"]
        assert len(col_deviations) >= 1
        assert "Displaced" in col_deviations[0].title
        assert col_deviations[0].risk_points >= 20
        doc.close()

    def test_detect_missing_statutory_footer(self):
        """A statement lacking mandatory SBP regulatory footers flags RULE_BANK_TEMPLATE_DISCLAIMER_MISSING."""
        columns = [
            (40.0, "Post Date"),
            (110.0, "Particulars"),
            (320.0, "Debit"),
            (410.0, "Credit"),
            (490.0, "Balance"),
        ]
        body = [
            [(40.0, "01/03/2026"), (110.0, "Deposit"), (410.0, "50,000.00"), (490.0, "150,000.00")],
        ]
        # Omit footer text completely
        doc = create_mock_bank_statement_pdf(
            header_text="HABIB BANK LIMITED - STATEMENT OF ACCOUNT\nIBAN: PK36HABB00010201020304",
            table_columns=columns,
            body_rows=body,
            footer_text="",
        )

        res = evaluate_bank_template(doc, bank_code="HABB")
        assert res.status == "DEVIATION_DETECTED"
        footer_deviations = [d for d in res.deviations if d.rule_id == "RULE_BANK_TEMPLATE_DISCLAIMER_MISSING"]
        assert len(footer_deviations) == 1
        assert "Missing SBP Statutory Footer" in footer_deviations[0].title
        doc.close()

    def test_detect_prohibited_comic_font(self):
        """Embedding Comic Sans or prohibited typography flags RULE_BANK_TEMPLATE_UNAUTHORIZED_FONT."""
        columns = [
            (50.0, "Date"),
            (140.0, "Narration"),
            (350.0, "Debit (PKR)"),
            (430.0, "Credit (PKR)"),
            (500.0, "Balance (PKR)"),
        ]
        body = [
            [(50.0, "01/03/2026"), (140.0, "Transfer"), (350.0, "10,000.00"), (500.0, "90,000.00")],
        ]
        # In PyMuPDF, insert font with comic in name or simulate font embedding
        doc = create_mock_bank_statement_pdf(
            header_text="MEEZAN BANK LIMITED - STATEMENT OF ACCOUNT\nIBAN: PK36MEZN00010201020304",
            table_columns=columns,
            body_rows=body,
            footer_text="This is a computer-generated statement of Meezan Bank and does not require a signature.",
            font_name="helv",
        )
        from unittest.mock import patch
        with patch.object(pymupdf.Page, "get_fonts", return_value=[(1, "n/a", "TrueType", "ComicSansMS", "F1", "WinAnsiEncoding")]):
            res = evaluate_bank_template(doc, bank_code="MEZN")
            assert res.status == "DEVIATION_DETECTED"
            font_devs = [d for d in res.deviations if d.rule_id == "RULE_BANK_TEMPLATE_UNAUTHORIZED_FONT"]
            assert len(font_devs) == 1
            assert "Prohibited Font" in font_devs[0].title
            assert font_devs[0].risk_points >= 20
        doc.close()

    def test_unindexed_bank_graceful_pass(self):
        """Documents from unindexed banks return UNINDEXED_BANK without raising errors."""
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text(pymupdf.Point(50, 50), "Foreign Bank Statement of Account")

        res = evaluate_bank_template(doc, bank_code="UNKNOWN_BANK")
        assert res.status == "UNINDEXED_BANK"
        assert res.is_conforming is False
        assert len(res.deviations) == 0
        doc.close()

