"""
Test Suite: Multi-Page Balance Continuity & Header Tampering Verification (Stage 6)
Verifies:
  1. Clean 2-page Meezan Bank statement maintains running balance across page boundaries (0 findings).
  2. Multi-page balance discontinuity without Brought Forward line (attacker inflated Page 2 starting transaction).
  3. Multi-page Brought Forward mismatch (Page 2 states higher B/F than Page 1 closing balance).
  4. Header Opening Balance tampering (header claims PKR 500,000, table starts at PKR 100,000).
  5. Header Closing Balance tampering (header claims PKR 950,000, ledger ends at PKR 350,000).
  6. Header Macro Summary tampering (Opening + Credits - Debits != Closing).
"""
import asyncio
import io
import sys
import time
from decimal import Decimal
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, r"d:\zylo\DeepTrace")

import pymupdf
from PIL import Image

from app.config import get_settings
from app.core import security
from app.core.storage import storage
from app.db.client import connect, disconnect, set_org_context
from app.features.pipeline import service

settings = get_settings()


def build_multipage_pdf(
    header_opening: str = "1,00,000.00",
    header_closing: str = "3,50,000.00",
    header_credits: str = "4,00,000.00",
    header_debits: str = "1,50,000.00",
    page1_p1_balance: str = "1,00,000.00",
    page2_bf_line: str | None = "3,00,000.00",  # None if no explicit B/F line
    page2_row1_balance: str = "4,50,000.00",    # Page 2 first tx resulting balance
) -> bytes:
    """Helper to generate a realistic 2-page Meezan Bank PDF statement."""
    doc = pymupdf.open()

    # ── Page 1 ──
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 40), f"TIMESTAMP: {time.time()}", fontsize=7)
    p1.insert_text((50, 70), "MEEZAN BANK LIMITED - STATEMENT OF ACCOUNT", fontsize=13, fontname="helv")
    p1.insert_text((50, 90), "IBAN: PK36MEZN0001020102030405", fontsize=9, fontname="helv")
    p1.insert_text((50, 105), "Account Title: MUHAMMAD HAMZA", fontsize=9, fontname="helv")

    # Header Summary Grid
    p1.insert_text((50, 125), f"Opening Balance (PKR): {header_opening}", fontsize=9, fontname="helv")
    p1.insert_text((220, 125), f"Total Credits: PKR {header_credits}", fontsize=9, fontname="helv")
    p1.insert_text((370, 125), f"Total Debits: PKR {header_debits}", fontsize=9, fontname="helv")
    p1.insert_text((50, 140), f"Closing Balance: PKR {header_closing}", fontsize=9, fontname="helv")

    # Table Header
    p1.insert_text((50, 170), "Date", fontsize=8, fontname="helv")
    p1.insert_text((130, 170), "Description", fontsize=8, fontname="helv")
    p1.insert_text((340, 170), "Debit (PKR)", fontsize=8, fontname="helv")
    p1.insert_text((420, 170), "Credit (PKR)", fontsize=8, fontname="helv")
    p1.insert_text((500, 170), "Balance (PKR)", fontsize=8, fontname="helv")

    # Page 1 Row 1: Opening
    p1.insert_text((50, 195), "01/03/2026", fontsize=8, fontname="helv")
    p1.insert_text((130, 195), "Opening Balance", fontsize=8, fontname="helv")
    p1.insert_text((500, 195), page1_p1_balance, fontsize=8, fontname="helv")

    # Page 1 Row 2: Salary Credit (100k + 250k = 350k)
    p1.insert_text((50, 220), "05/03/2026", fontsize=8, fontname="helv")
    p1.insert_text((130, 220), "1LINK/IBFT/Salary", fontsize=8, fontname="helv")
    p1.insert_text((420, 220), "2,50,000.00", fontsize=8, fontname="helv")
    p1.insert_text((500, 220), "3,50,000.00", fontsize=8, fontname="helv")

    # Page 1 Row 3: Cash Withdrawal (350k - 50k = 300k)
    p1.insert_text((50, 245), "10/03/2026", fontsize=8, fontname="helv")
    p1.insert_text((130, 245), "ATM Cash Withdrawal", fontsize=8, fontname="helv")
    p1.insert_text((340, 245), "50,000.00", fontsize=8, fontname="helv")
    p1.insert_text((500, 245), "3,00,000.00", fontsize=8, fontname="helv")

    # Page 1 Bottom: Carried Forward (300k)
    p1.insert_text((50, 280), "Balance Carried Forward", fontsize=8, fontname="helv")
    p1.insert_text((500, 280), "3,00,000.00", fontsize=8, fontname="helv")

    # ── Page 2 ──
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 40), f"TIMESTAMP: {time.time()}", fontsize=7)
    p2.insert_text((50, 70), "MEEZAN BANK LIMITED - STATEMENT OF ACCOUNT (PAGE 2)", fontsize=11, fontname="helv")
    p2.insert_text((50, 90), "IBAN: PK36MEZN0001020102030405", fontsize=9, fontname="helv")

    # Table Header on Page 2
    p2.insert_text((50, 130), "Date", fontsize=8, fontname="helv")
    p2.insert_text((130, 130), "Description", fontsize=8, fontname="helv")
    p2.insert_text((340, 130), "Debit (PKR)", fontsize=8, fontname="helv")
    p2.insert_text((420, 130), "Credit (PKR)", fontsize=8, fontname="helv")
    p2.insert_text((500, 130), "Balance (PKR)", fontsize=8, fontname="helv")

    curr_y = 155
    if page2_bf_line is not None:
        p2.insert_text((50, curr_y), "Balance Brought Forward", fontsize=8, fontname="helv")
        p2.insert_text((500, curr_y), page2_bf_line, fontsize=8, fontname="helv")
        curr_y += 25

    # Page 2 Row 1: Business Deposit (300k + 150k = 450k)
    p2.insert_text((50, curr_y), "15/03/2026", fontsize=8, fontname="helv")
    p2.insert_text((130, curr_y), "Online Transfer Inward", fontsize=8, fontname="helv")
    p2.insert_text((420, curr_y), "1,50,000.00", fontsize=8, fontname="helv")
    p2.insert_text((500, curr_y), page2_row1_balance, fontsize=8, fontname="helv")
    curr_y += 25

    # Page 2 Row 2: Supplier Payment (450k - 100k = 350k)
    p2.insert_text((50, curr_y), "25/03/2026", fontsize=8, fontname="helv")
    p2.insert_text((130, curr_y), "RAAST Payment to Supplier", fontsize=8, fontname="helv")
    p2.insert_text((340, curr_y), "1,00,000.00", fontsize=8, fontname="helv")
    p2.insert_text((500, curr_y), "3,50,000.00", fontsize=8, fontname="helv")

    doc.set_metadata({
        "producer": "JasperReports Library v6.20.0",
        "creator": "Meezan Core Banking Engine",
        "creationDate": "D:20260325120000Z",
        "modDate": "D:20260325120000Z",
    })

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestMultiPageFinancial(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await connect()
        self.org_id = "cmtl7u5ku0000120pueg7by84"
        async with set_org_context(self.org_id) as tx:
            user = await tx.user.find_first()
            self.user_id = user.id

    async def asyncTearDown(self):
        await disconnect()

    async def _run_doc_test(self, pdf_bytes: bytes, test_title: str) -> list[dict]:
        """Helper to upload PDF, run pipeline inline, and fetch evidence items."""
        case_num = f"DT-TEST-MP-{int(time.time()*1000)}"
        async with set_org_context(self.org_id) as tx:
            inv = await tx.investigation.create(
                data={
                    "organizationId": self.org_id,
                    "userId": self.user_id,
                    "caseNumber": case_num,
                    "title": test_title,
                }
            )

        sha256 = security.compute_sha256(pdf_bytes)
        storage_path = f"documents/{inv.id}/test_statement.pdf"
        storage.upload_file(settings.s3_bucket_documents, storage_path, pdf_bytes, "application/pdf")

        # Open doc to extract page dimensions
        pdf_doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(pdf_doc)

        async with set_org_context(self.org_id) as tx:
            doc = await tx.document.create(
                data={
                    "investigationId": inv.id,
                    "originalFilename": "meezan_multipage.pdf",
                    "mimeType": "application/pdf",
                    "fileSizeBytes": len(pdf_bytes),
                    "documentType": "BANK_STATEMENT",
                    "sha256Hash": sha256,
                    "md5Hash": "dummy",
                    "storagePath": storage_path,
                    "storagePathClone": storage_path,
                    "pageCount": page_count,
                }
            )
            for p_idx in range(page_count):
                p = pdf_doc[p_idx]
                pix = p.get_pixmap(dpi=150)
                png_bytes = pix.tobytes("png")
                page_path = f"documents/{inv.id}/pages/page_{p_idx+1}.png"
                storage.upload_file(settings.s3_bucket_documents, page_path, png_bytes, "image/png")
                await tx.documentpage.create(
                    data={
                        "documentId": doc.id,
                        "pageNumber": p_idx + 1,
                        "widthPx": pix.width,
                        "heightPx": pix.height,
                        "widthPts": float(p.rect.width),
                        "heightPts": float(p.rect.height),
                        "dpi": 150,
                        "renderedImagePath": page_path,
                    }
                )
        pdf_doc.close()

        # Trigger full pipeline
        await service.trigger_pipeline(
            org_id=self.org_id,
            investigation_id=inv.id,
            triggered_by="system",
            document_id=doc.id,
        )

        # Wait for completion
        for _ in range(50):
            await asyncio.sleep(0.3)
            status = await service.get_pipeline_status(self.org_id, inv.id)
            if status and status.status in ["COMPLETED", "FAILED"]:
                break

        # Fetch evidence items
        async with set_org_context(self.org_id) as tx:
            items = await tx.evidenceitem.find_many(where={"documentId": doc.id})
            return [
                {
                    "ruleId": it.ruleId,
                    "category": it.category,
                    "severity": it.severity,
                    "title": it.title,
                    "discrepancy": it.discrepancy,
                    "pageNumber": it.pageNumber,
                }
                for it in items
            ]

    async def test_01_clean_multipage_statement(self):
        """Clean 2-page statement must pass with 0 mathematical/forensic errors."""
        pdf_bytes = build_multipage_pdf()
        findings = await self._run_doc_test(pdf_bytes, "Clean Multi-Page Statement")
        math_findings = [f for f in findings if f["category"] == "MATHEMATICAL_MISMATCH"]
        self.assertEqual(len(math_findings), 0, f"Expected 0 mathematical findings on clean PDF, got: {math_findings}")
        print("  ✓ Clean 2-page Meezan Bank statement verified with 0 mathematical findings.")

    async def test_02_tampered_multipage_page2_first_transaction(self):
        """Attacker inflates Page 2 first transaction balance without a Brought Forward line."""
        # Page 1 ends at 300,000. Deposit is 150,000. Expected is 450,000.
        # Attacker forged row 1 balance to 9,50,000.00!
        pdf_bytes = build_multipage_pdf(
            page2_bf_line=None,
            page2_row1_balance="9,50,000.00",
        )
        findings = await self._run_doc_test(pdf_bytes, "Tampered Page 2 Row 1 Balance")
        discont_findings = [f for f in findings if f["ruleId"] in ["RULE_PK_PAGE_BALANCE_DISCONTINUITY", "RULE_PK_LEDGER_RECONCILIATION_FAIL"]]
        self.assertGreater(len(discont_findings), 0, "Expected page discontinuity finding across Page 1 -> Page 2!")
        print(f"  ✓ Caught multi-page balance discontinuity: '{discont_findings[0]['title']}' (Page {discont_findings[0]['pageNumber']})")

    async def test_03_tampered_multipage_brought_forward_mismatch(self):
        """Attacker inflates Page 2 Brought Forward line to PKR 750,000 (Page 1 closed at 300,000)."""
        pdf_bytes = build_multipage_pdf(
            page2_bf_line="7,50,000.00",  # Discrepancy: +450,000
        )
        findings = await self._run_doc_test(pdf_bytes, "Tampered Page 2 Brought Forward Line")
        bf_findings = [f for f in findings if f["ruleId"] == "RULE_PK_PAGE_BALANCE_DISCONTINUITY"]
        self.assertGreater(len(bf_findings), 0, "Expected RULE_PK_PAGE_BALANCE_DISCONTINUITY finding!")
        print(f"  ✓ Caught Page Brought Forward Mismatch: '{bf_findings[0]['title']}' - Discrepancy: {bf_findings[0]['discrepancy']}")

    async def test_04_tampered_header_opening_balance(self):
        """User tampered with Opening Balance in header (500,000 vs table 100,000)."""
        pdf_bytes = build_multipage_pdf(
            header_opening="5,00,000.00",  # Tampered!
            page1_p1_balance="1,00,000.00",
        )
        findings = await self._run_doc_test(pdf_bytes, "Tampered Header Opening Balance")
        op_findings = [f for f in findings if f["ruleId"] == "RULE_PK_OPENING_BALANCE_MISMATCH"]
        self.assertGreater(len(op_findings), 0, "Expected RULE_PK_OPENING_BALANCE_MISMATCH finding!")
        print(f"  ✓ Caught Header Opening Balance Mismatch: '{op_findings[0]['title']}' - Discrepancy: {op_findings[0]['discrepancy']}")

    async def test_05_tampered_header_closing_balance(self):
        """User tampered with Closing Balance in header (claims 850,000 vs final table 350,000)."""
        pdf_bytes = build_multipage_pdf(
            header_closing="8,50,000.00",  # Tampered!
        )
        findings = await self._run_doc_test(pdf_bytes, "Tampered Header Closing Balance")
        cl_findings = [f for f in findings if f["ruleId"] == "RULE_PK_CLOSING_BALANCE_MISMATCH"]
        self.assertGreater(len(cl_findings), 0, "Expected RULE_PK_CLOSING_BALANCE_MISMATCH finding!")
        print(f"  ✓ Caught Header Closing Balance Mismatch: '{cl_findings[0]['title']}' - Discrepancy: {cl_findings[0]['discrepancy']}")

    async def test_06_tampered_macro_summary_identity(self):
        """User tampered with summary totals (Opening 100k + Credits 400k - Debits 150k != Closing 600k)."""
        pdf_bytes = build_multipage_pdf(
            header_opening="1,00,000.00",
            header_credits="4,00,000.00",
            header_debits="1,50,000.00",
            header_closing="6,00,000.00",  # Tampered summary! Expected is 350,000
        )
        findings = await self._run_doc_test(pdf_bytes, "Tampered Macro Summary Identity")
        macro_findings = [f for f in findings if f["ruleId"] == "RULE_PK_STATEMENT_SUMMARY_TAMPER"]
        self.assertGreater(len(macro_findings), 0, "Expected RULE_PK_STATEMENT_SUMMARY_TAMPER finding!")
        print(f"  ✓ Caught Summary Formula Tampering: '{macro_findings[0]['title']}' - Discrepancy: {macro_findings[0]['discrepancy']}")


if __name__ == "__main__":
    unittest.main()
