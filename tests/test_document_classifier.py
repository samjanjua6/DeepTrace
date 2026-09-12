"""
Tests for Stage 0 Automated Document Classifier (LayoutLM & Institutional Multi-Modal Engine).
Validates auto-detection of:
  1. Bank Statements (Meezan, HBL, SBP IBAN, Ledger matrix)
  2. Salary Slips (Dual-column Earnings/Deductions, Basic Pay, Net Salary)
  3. K-Electric Bills (KE anchors, Consumer No, Tariff, Units Consumed, Due Date)
  4. FBR Challans (CPR regex, NTN, Tax Year, Head of Account)
  5. CNIC / Identity Documents (NADRA, 13-digit regex, ID-1 card geometry)
  6. Academic / Generic fallbacks (OTHER)
"""
import io
import pytest
import pymupdf
from PIL import Image, ImageDraw

from app.features.pipeline.tasks.document_classifier import (
    document_classifier,
    validate_iban_mod97,
    PK_IBAN_REGEX,
    PK_CNIC_REGEX,
    FBR_CPR_REGEX,
    KE_CONSUMER_REGEX,
)


def create_mock_pdf(text_lines: list[tuple[float, float, str]], width=595, height=842) -> bytes:
    """Helper to create an in-memory PDF with text positioned at specific coordinates."""
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    for x, y, text in text_lines:
        page.insert_text(pymupdf.Point(x, y), text, fontsize=10)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


class TestDocumentClassifier:
    """Institutional classification test suite."""

    def test_iban_mod97_validation(self):
        """Verify Pakistani IBAN ISO 7064 MOD-97 algorithm."""
        # Valid Meezan IBAN
        valid_iban = "PK56MEZN0001234567890123"
        assert validate_iban_mod97(valid_iban) is True

        # Invalid checksum
        invalid_iban = "PK99MEZN0001234567890123"
        assert validate_iban_mod97(invalid_iban) is False

        # Malformed length
        assert validate_iban_mod97("PK12MEZN123") is False

    def test_classify_bank_statement(self):
        """Test auto-detection of Pakistani bank statements."""
        lines = [
            (50, 60, "MEEZAN BANK LIMITED - THE PREMIER ISLAMIC BANK"),
            (50, 80, "STATEMENT OF ACCOUNT"),
            (50, 100, "IBAN: PK36MEZN0001234567890123"),
            (50, 120, "Opening Balance: PKR 2,50,000.00"),
            (50, 140, "Closing Balance: PKR 25,00,000.00"),
            (50, 180, "Date | Value Date | Description | Debit | Credit | Running Balance"),
            (50, 200, "12-Jan-2026 | 12-Jan-2026 | 1LINK Raast Transfer | 0.00 | 22,50,000.00 | 25,00,000.00"),
        ]
        pdf_bytes = create_mock_pdf(lines)

        res = document_classifier.classify_document(pdf_bytes, "application/pdf")
        assert res.document_type == "BANK_STATEMENT"
        assert "STATEMENT" in res.subtype
        assert res.confidence >= 0.85
        assert any("MEEZAN" in a["anchor"] for a in res.matched_anchors)

    def test_classify_salary_slip(self):
        """Test auto-detection of corporate/government salary slips."""
        lines = [
            (200, 50, "CONFIDENTIAL PAYSLIP FOR THE MONTH OF JANUARY 2026"),
            (50, 80, "Employee ID: EMP-94821 | Designation: Lead Systems Architect"),
            (50, 100, "Department: Engineering | Working Days: 30 | Days Paid: 30"),
            (50, 140, "EARNINGS:"),
            (50, 160, "Basic Salary: PKR 350,000.00"),
            (50, 180, "House Rent Allowance (HRA): PKR 150,000.00"),
            (50, 200, "Conveyance Allowance: PKR 50,000.00"),
            (50, 220, "Gross Earnings: PKR 550,000.00"),
            (300, 140, "DEDUCTIONS:"),
            (300, 160, "Income Tax Deduction: PKR 45,000.00"),
            (300, 180, "Provident Fund (PF): PKR 25,000.00"),
            (300, 200, "EOBI Contribution: PKR 1,500.00"),
            (300, 220, "Total Deductions: PKR 71,500.00"),
            (150, 270, "NET SALARY PAYABLE: PKR 478,500.00 (Take Home Pay)"),
        ]
        pdf_bytes = create_mock_pdf(lines)

        res = document_classifier.classify_document(pdf_bytes, "application/pdf")
        assert res.document_type == "SALARY_SLIP"
        assert res.subtype == "PAYROLL_SALARY_SLIP"
        assert res.confidence >= 0.85
        assert any("PAYSLIP" in a["anchor"] or "SALARY" in a["anchor"] for a in res.matched_anchors)

    def test_classify_k_electric_bill(self):
        """Test auto-detection of K-Electric consumer bills."""
        lines = [
            (50, 50, "K-ELECTRIC - ELECTRICITY CONSUMER BILL"),
            (50, 70, "KE Bill for Billing Month: March 2026"),
            (50, 90, "Consumer No: 040001234567 | Account No: 1234567890"),
            (50, 110, "Tariff: A1-R Res | Sanctioned Load: 5.0 kW | Meter No: 987654"),
            (50, 130, "Units Consumed: 485 kWh | Reading Date: 15-Mar-2026"),
            (50, 160, "Current Electricity Charges: PKR 18,540.00"),
            (50, 180, "Electricity Duty: PKR 280.00 | Fuel Charges Adjustment (FCA): PKR 1,420.00"),
            (50, 200, "Total Current Bill: PKR 21,240.00 | Arrears: PKR 0.00"),
            (50, 230, "Amount Payable Within Due Date: PKR 21,240.00"),
            (50, 250, "Late Payment Surcharge: PKR 1,850.00"),
            (50, 270, "Amount Payable After Due Date: PKR 23,090.00"),
            (50, 290, "Due Date: 28-Mar-2026"),
        ]
        pdf_bytes = create_mock_pdf(lines)

        res = document_classifier.classify_document(pdf_bytes, "application/pdf")
        assert res.document_type == "UTILITY_BILL"
        assert res.subtype == "K_ELECTRIC_BILL"
        assert res.confidence >= 0.90
        assert any("K-ELECTRIC" in a["anchor"] for a in res.matched_anchors)

    def test_classify_fbr_challan(self):
        """Test auto-detection of FBR Computerized Payment Receipts (CPR)."""
        lines = [
            (100, 50, "GOVERNMENT OF PAKISTAN - REVENUE DIVISION"),
            (120, 70, "FEDERAL BOARD OF REVENUE (FBR) - e-FBR IRIS"),
            (80, 90, "COMPUTERIZED PAYMENT RECEIPT (CPR)"),
            (50, 120, "CPR No: CPR-20260312-0101-9876543 | Tax Year: 2026"),
            (50, 140, "National Tax Number (NTN): 1234567-8"),
            (50, 160, "Taxpayer Name: ZYLO TECHNOLOGIES PRIVATE LIMITED"),
            (50, 180, "Head of Account: 0100 - Income Tax | Payment Section: 147"),
            (50, 200, "Tax Period: 2026-Q1 | Direct Taxes Directorate"),
            (50, 220, "Amount in Figures: PKR 450,000.00"),
            (50, 240, "Amount in Words: Rupees Four Hundred Fifty Thousand Only"),
            (50, 270, "Authorized Officer / National Bank of Pakistan (NBP) Cashier Stamp"),
        ]
        pdf_bytes = create_mock_pdf(lines)

        res = document_classifier.classify_document(pdf_bytes, "application/pdf")
        assert res.document_type == "TAX_CERTIFICATE"
        assert res.subtype == "FBR_CPR_CHALLAN"
        assert res.confidence >= 0.90
        assert any("FEDERAL BOARD OF REVENUE" in a["anchor"] or "FBR" in a["anchor"] for a in res.matched_anchors)

    def test_classify_cnic_document(self):
        """Test auto-detection of Pakistani CNIC cards."""
        lines = [
            (80, 40, "ISLAMIC REPUBLIC OF PAKISTAN"),
            (70, 60, "NATIONAL DATABASE AND REGISTRATION AUTHORITY (NADRA)"),
            (90, 80, "NATIONAL IDENTITY CARD"),
            (50, 110, "Name: Muhammad Shaheer"),
            (50, 130, "Father Name: Tariq Mehmood"),
            (50, 150, "Gender: M | Country of Stay: Pakistan"),
            (50, 170, "Identity Number: 35201-1234567-1"),
            (50, 190, "Date of Birth: 14.08.1998 | Date of Issue: 12.01.2024"),
            (50, 210, "Date of Expiry: 12.01.2034 | Family No: 8492019"),
            (50, 230, "Holder's Signature"),
        ]
        # ID-1 Card dimensions (width=400, height=252 => ~1.587:1 aspect ratio)
        pdf_bytes = create_mock_pdf(lines, width=400, height=252)

        res = document_classifier.classify_document(pdf_bytes, "application/pdf")
        assert res.document_type == "IDENTITY_DOCUMENT"
        assert res.subtype == "NADRA_CNIC_CARD"
        assert res.confidence >= 0.90
        assert any("NADRA" in a["anchor"] or "NATIONAL IDENTITY CARD" in a["anchor"] for a in res.matched_anchors)

    def test_classify_academic_other_fallback(self):
        """Test fallback to OTHER for academic degrees, transcripts, and generic docs."""
        lines = [
            (100, 60, "BOARD OF INTERMEDIATE AND SECONDARY EDUCATION LAHORE"),
            (120, 90, "HIGHER SECONDARY SCHOOL CERTIFICATE EXAMINATION"),
            (50, 130, "This is to certify that Muhammad Ali, son of Ahmed Ali,"),
            (50, 150, "has successfully passed the Intermediate Examination in Pre-Engineering Group"),
            (50, 170, "awarded Grade A with 940 marks out of 1100."),
            (50, 200, "Controller of Examinations | Chairman BISE"),
        ]
        pdf_bytes = create_mock_pdf(lines)

        res = document_classifier.classify_document(pdf_bytes, "application/pdf")
        assert res.document_type == "OTHER"
        assert res.subtype == "GENERIC_DOCUMENT"
        assert res.confidence >= 0.80
