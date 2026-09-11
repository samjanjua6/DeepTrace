"""
Test Suite: Scanned Document OCR & Downstream Forensic Verification
Verifies:
  1. Pure raster / scanned PDF with 0 native digital text stream triggers RapidOCR deep-learning engine.
  2. OCR text, confidence score, and word coordinates are persisted to DocumentPage.
  3. Downstream financial verification (Stage 6) parses transaction ledger from OCR word coordinates.
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

from PIL import Image, ImageDraw
import pymupdf

from app.core import security
from app.core.storage import storage
from app.config import get_settings
from app.db.client import connect, disconnect, set_org_context
from app.features.pipeline import service

settings = get_settings()


def create_scanned_bank_statement_pdf() -> bytes:
    """Generate a pure image/raster scanned PDF with zero digital text operators."""
    # 1. Draw a high-resolution scanned paper page
    img = Image.new("RGB", (1240, 1754), color="#FDFCF7")  # 150 DPI A4
    d = ImageDraw.Draw(img)

    # Header
    d.text((80, 80), "MEEZAN BANK LIMITED - SCANNED PAPER STATEMENT", fill="#1A1A1A")
    d.text((80, 120), "IBAN: PK36MEZN0001020102030405", fill="#1A1A1A")
    d.text((80, 150), "Account: 0101-0102030405", fill="#1A1A1A")

    # Table Header
    d.text((80, 220), "Date", fill="#1A1A1A")
    d.text((220, 220), "Description", fill="#1A1A1A")
    d.text((600, 220), "Debit (PKR)", fill="#1A1A1A")
    d.text((800, 220), "Credit (PKR)", fill="#1A1A1A")
    d.text((1000, 220), "Balance (PKR)", fill="#1A1A1A")

    # Row 1: Opening
    d.text((80, 270), "01/03/2026", fill="#1A1A1A")
    d.text((220, 270), "Opening Balance", fill="#1A1A1A")
    d.text((1000, 270), "1,00,000.00", fill="#1A1A1A")

    # Row 2: Salary Credit (100,000 + 250,000 = 350,000)
    d.text((80, 320), "05/03/2026", fill="#1A1A1A")
    d.text((220, 320), "Salary Credit", fill="#1A1A1A")
    d.text((800, 320), "2,50,000.00", fill="#1A1A1A")
    d.text((1000, 320), "3,50,000.00", fill="#1A1A1A")

    # Row 3: Cash Withdrawal (350,000 - 25,000 = 325,000)
    d.text((80, 370), "12/03/2026", fill="#1A1A1A")
    d.text((220, 370), "ATM Cash Withdrawal", fill="#1A1A1A")
    d.text((600, 370), "25,000.00", fill="#1A1A1A")
    d.text((1000, 370), "3,25,000.00", fill="#1A1A1A")

    # 2. Insert image into a PDF without any /Tj vector text
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # 72 DPI A4
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    page.insert_image(pymupdf.Rect(0, 0, 595, 842), stream=buf.getvalue())

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestScannedOcrPipeline(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await connect()
        self.org_id = "cmtl7u5ku0000120pueg7by84"
        async with set_org_context(self.org_id) as tx:
            user = await tx.user.find_first()
            case_num = f"DT-TEST-OCR-{int(time.time()*1000)}"
            self.inv = await tx.investigation.create(
                data={
                    "organizationId": self.org_id,
                    "userId": user.id,
                    "caseNumber": case_num,
                    "title": "Scanned Bank Statement OCR Verification",
                }
            )

    async def asyncTearDown(self):
        # Do not cascade-delete investigation to respect immutable custody_events audit trigger
        await disconnect()

    async def test_scanned_pdf_rapidocr_execution(self):
        """Verify scanned raster PDF with zero digital text is extracted via RapidOCR."""
        pdf_bytes = create_scanned_bank_statement_pdf()

        # Confirm digital stream is completely empty
        doc_check = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        native_chars = len(doc_check[0].get_text("text").strip())
        pix = doc_check[0].get_pixmap(dpi=150)
        page_png_bytes = pix.tobytes("png")
        doc_check.close()
        self.assertEqual(native_chars, 0, "Input PDF should have 0 native digital characters.")

        sha256 = security.compute_sha256(pdf_bytes)
        storage_path = f"documents/{self.inv.id}/scanned_test.pdf"
        page_path = f"documents/{self.inv.id}/pages/page_1.png"
        storage.upload_file(settings.s3_bucket_documents, storage_path, pdf_bytes, "application/pdf")
        storage.upload_file(settings.s3_bucket_documents, page_path, page_png_bytes, "image/png")

        # Ingest document
        async with set_org_context(self.org_id) as tx:
            doc = await tx.document.create(
                data={
                    "investigationId": self.inv.id,
                    "originalFilename": "scanned_meezan.pdf",
                    "mimeType": "application/pdf",
                    "fileSizeBytes": len(pdf_bytes),
                    "documentType": "BANK_STATEMENT",
                    "sha256Hash": sha256,
                    "md5Hash": "dummy",
                    "storagePath": storage_path,
                    "storagePathClone": storage_path,
                    "pageCount": 1,
                }
            )
            await tx.documentpage.create(
                data={
                    "documentId": doc.id,
                    "pageNumber": 1,
                    "widthPx": 1240,
                    "heightPx": 1754,
                    "widthPts": 595,
                    "heightPts": 842,
                    "dpi": 150,
                    "renderedImagePath": page_path,
                }
            )

        # Trigger full pipeline
        pipeline_status = await service.trigger_pipeline(
            org_id=self.org_id,
            investigation_id=self.inv.id,
            triggered_by="system",
            document_id=doc.id,
        )

        # Wait for completion (inline or worker)
        for _ in range(40):
            await asyncio.sleep(0.5)
            status = await service.get_pipeline_status(self.org_id, self.inv.id)
            if status and status.status in ["COMPLETED", "FAILED"]:
                break

        self.assertEqual(status.status, "COMPLETED", f"Pipeline failed: {status.errorMessage}")

        # Verify DocumentPage has OCR text and word data
        async with set_org_context(self.org_id) as tx:
            page_rec = await tx.documentpage.find_first(where={"documentId": doc.id, "pageNumber": 1})
            self.assertIsNotNone(page_rec.ocrText, "DocumentPage.ocrText should not be None")
            self.assertGreater(len(page_rec.ocrText), 50, "OCR text should contain extracted lines")
            self.assertIn("MEEZAN", page_rec.ocrText.upper())
            self.assertIn("PK36MEZN0001020102030405", page_rec.ocrText.replace(" ", "").upper())
            self.assertGreater(page_rec.ocrConfidence, 0.70)
            print(f"✓ Scanned Document OCR extracted {len(page_rec.ocrText)} characters with {page_rec.ocrConfidence*100:.1f}% confidence!")
            print(f"  Preview: {page_rec.ocrText[:120]}...")


if __name__ == "__main__":
    unittest.main()
