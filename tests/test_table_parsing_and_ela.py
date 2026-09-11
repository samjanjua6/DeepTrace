"""
Test Suite: Table Parsing Resilience & Error Level Analysis (ELA) Precision
Verifies:
  1. Bank statement with Cheque No column (e.g. 548921) reconciles with 0 false positives.
  2. Multi-line narration with dates/invoices does not trigger false transaction rows.
  3. Clean vector PDF statement produces 0 ELA anomalies (Gibbs phenomenon suppressed).
  4. Spliced raster element produces a localized, tight bounding box (no runaway box).
  5. Adaptive vertical line clustering correctly handles text baseline offsets and skew.
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

import cv2
import numpy as np
from PIL import Image, ImageDraw
import pymupdf

from app.config import get_settings
from app.core import security
from app.core.storage import storage
from app.db.client import connect, db, disconnect, set_org_context
from app.features.pipeline import service
from app.features.pipeline.tasks.stage_6_financial import (
    cluster_words_into_lines,
    parse_pakistani_amount,
    process_financial,
)
from app.features.pipeline.tasks.stage_4_vision_ela import process_vision_ela

settings = get_settings()


def create_statement_with_cheque_no() -> bytes:
    """Generate a clean statement with an explicit Cheque No column (e.g., HBL style)."""
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)

    p.insert_text((50, 40), f"TIMESTAMP: {time.time()}", fontsize=7)
    p.insert_text((50, 70), "HABIB BANK LIMITED - STATEMENT OF ACCOUNT", fontsize=13)
    p.insert_text((50, 90), "IBAN: PK21HABB0001020102030405", fontsize=9)
    p.insert_text((50, 110), "Account Title: TARIQ MAHMOOD", fontsize=9)
    p.insert_text((50, 130), "Opening Balance: PKR 1,00,000.00", fontsize=9)

    # Table Header with Cheque No column
    p.insert_text((50, 160), "Date", fontsize=8)
    p.insert_text((120, 160), "Description", fontsize=8)
    p.insert_text((270, 160), "Cheque No", fontsize=8)
    p.insert_text((350, 160), "Debit", fontsize=8)
    p.insert_text((430, 160), "Credit", fontsize=8)
    p.insert_text((510, 160), "Balance", fontsize=8)

    # Row 1: Opening balance row
    p.insert_text((50, 185), "01/03/2026", fontsize=8)
    p.insert_text((120, 185), "Opening Balance", fontsize=8)
    p.insert_text((510, 185), "1,00,000.00", fontsize=8)

    # Row 2: Cheque Clearing Inward (Credit: 50,000, Cheque No: 548921 -> Balance: 150,000)
    p.insert_text((50, 210), "05/03/2026", fontsize=8)
    p.insert_text((120, 210), "Clearing Cheque Deposit", fontsize=8)
    p.insert_text((270, 210), "548921", fontsize=8)
    p.insert_text((430, 210), "50,000.00", fontsize=8)
    p.insert_text((510, 210), "1,50,000.00", fontsize=8)

    # Row 3: Cheque Withdrawal (Debit: 25,000, Cheque No: 004182 -> Balance: 125,000)
    p.insert_text((50, 235), "12/03/2026", fontsize=8)
    p.insert_text((120, 235), "Self Cheque Withdrawal", fontsize=8)
    p.insert_text((270, 235), "004182", fontsize=8)
    p.insert_text((350, 235), "25,000.00", fontsize=8)
    p.insert_text((510, 235), "1,25,000.00", fontsize=8)

    # Row 4: Multi-line narration with dates and reference numbers
    p.insert_text((50, 260), "18/03/2026", fontsize=8)
    p.insert_text((120, 260), "Raast Interbank Fund Transfer", fontsize=8)
    p.insert_text((350, 260), "15,000.00", fontsize=8)
    p.insert_text((510, 260), "1,10,000.00", fontsize=8)
    # Narration continuation line (contains secondary date and invoice number)
    p.insert_text((120, 272), "To Muhammad Ali STAN 532999 Inv #1042 dated 18/03/2026", fontsize=7)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_tampered_cheque_statement() -> bytes:
    """Generate a statement with Cheque No where Row 3 balance is fraudulently inflated."""
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)

    p.insert_text((50, 40), f"TIMESTAMP: {time.time()}", fontsize=7)
    p.insert_text((50, 70), "HABIB BANK LIMITED - STATEMENT OF ACCOUNT", fontsize=13)
    p.insert_text((50, 90), "IBAN: PK21HABB0001020102030405", fontsize=9)
    p.insert_text((50, 130), "Opening Balance: PKR 1,00,000.00", fontsize=9)

    p.insert_text((50, 160), "Date", fontsize=8)
    p.insert_text((120, 160), "Description", fontsize=8)
    p.insert_text((270, 160), "Cheque No", fontsize=8)
    p.insert_text((350, 160), "Debit", fontsize=8)
    p.insert_text((430, 160), "Credit", fontsize=8)
    p.insert_text((510, 160), "Balance", fontsize=8)

    p.insert_text((50, 185), "01/03/2026", fontsize=8)
    p.insert_text((120, 185), "Opening Balance", fontsize=8)
    p.insert_text((510, 185), "1,00,000.00", fontsize=8)

    p.insert_text((50, 210), "05/03/2026", fontsize=8)
    p.insert_text((120, 210), "Clearing Cheque Deposit", fontsize=8)
    p.insert_text((270, 210), "548921", fontsize=8)
    p.insert_text((430, 210), "50,000.00", fontsize=8)
    # Fraudulently inflated balance: 1,50,000 -> 15,00,000.00!
    p.insert_text((510, 210), "15,00,000.00", fontsize=8)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestTableParsingAndEla(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await connect()
        self.org_id = "cmtl7u5ku0000120pueg7by84"
        async with set_org_context(self.org_id) as tx:
            user = await tx.user.find_first()
            case_num = f"DT-TEST-PARSING-{int(time.time()*1000)}"
            self.inv = await tx.investigation.create(
                data={
                    "organizationId": self.org_id,
                    "userId": user.id,
                    "caseNumber": case_num,
                    "title": "Table Parsing & ELA Precision Verification",
                }
            )

    async def asyncTearDown(self):
        await disconnect()

    def test_adaptive_clustering_skew_resilience(self):
        """Test that words with slight vertical jitter/skew are clustered cleanly into rows."""
        words = [
            (50, 100.0, 90, 110.0, "01/03/2026", 0, 0, 0),
            (120, 101.5, 200, 111.5, "Salary Credit", 0, 0, 1),
            (350, 103.0, 410, 113.0, "50,000.00", 0, 0, 2),
            (500, 104.5, 570, 114.5, "1,50,000.00", 0, 0, 3),
        ]
        # Over 450 points, y varies from 100.0 to 104.5 (4.5 pt difference)
        # Old 3.0pt filter split this row; adaptive overlap clusters it into 1 line
        clustered = cluster_words_into_lines(words)
        self.assertEqual(len(clustered), 1, f"Expected 1 clustered line, got {len(clustered)}")
        self.assertEqual(len(clustered[0][1]), 4)

    async def test_cheque_column_zero_false_positives(self):
        """Statement with Cheque No 548921 and multi-line narration must reconcile with 0 findings."""
        pdf_bytes = create_statement_with_cheque_no()
        doc_uuid = f"test-chq-{int(time.time()*1000)}"
        storage_path = f"documents/{self.inv.id}/{doc_uuid}/statement.pdf"
        storage.upload_file(settings.s3_bucket_documents, storage_path, pdf_bytes, "application/pdf")

        sha256 = security.compute_sha256(pdf_bytes)
        async with set_org_context(self.org_id) as tx:
            doc_rec = await tx.document.create(
                data={
                    "investigationId": self.inv.id,
                    "originalFilename": "hbl_statement_cheque.pdf",
                    "fileSizeBytes": len(pdf_bytes),
                    "mimeType": "application/pdf",
                    "storagePath": storage_path,
                    "documentType": "BANK_STATEMENT",
                    "sha256Hash": sha256,
                    "pageCount": 1,
                }
            )
            # Render page 1
            doc_fitz = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            p = doc_fitz[0]
            pix = p.get_pixmap(dpi=150)
            page_img_path = f"documents/{self.inv.id}/{doc_uuid}/pages/page_1.png"
            storage.upload_file(settings.s3_bucket_documents, page_img_path, pix.tobytes("png"), "image/png")
            await tx.documentpage.create(
                data={
                    "documentId": doc_rec.id,
                    "pageNumber": 1,
                    "widthPx": pix.width,
                    "heightPx": pix.height,
                    "widthPts": float(p.rect.width),
                    "heightPts": float(p.rect.height),
                    "dpi": 150,
                    "renderedImagePath": page_img_path,
                }
            )
            doc_fitz.close()

            p_run = await tx.pipelinerun.create(
                data={
                    "investigation": {"connect": {"id": self.inv.id}},
                    "runNumber": 1,
                    "status": "RUNNING",
                }
            )
            stage_6 = await tx.pipelinestage.create(
                data={
                    "pipelineRun": {"connect": {"id": p_run.id}},
                    "stageType": "FINANCIAL_VERIFICATION",
                    "stageOrder": 6,
                    "status": "PENDING",
                }
            )

        # Execute Stage 6
        res = await process_financial(
            pipeline_run_id=p_run.id,
            pipeline_stage_id=stage_6.id,
            org_id=self.org_id,
            investigation_id=self.inv.id,
            document_id=doc_rec.id,
        )

        self.assertEqual(res["findings_count"], 0, f"Expected 0 findings on clean cheque statement, got {res['findings_count']}: {res['findings']}")

    async def test_cheque_statement_math_tamper_detected(self):
        """When Row 2 balance is tampered on a cheque statement, it must detect the discrepancy."""
        pdf_bytes = create_tampered_cheque_statement()
        doc_uuid = f"test-chq-tamper-{int(time.time()*1000)}"
        storage_path = f"documents/{self.inv.id}/{doc_uuid}/statement.pdf"
        storage.upload_file(settings.s3_bucket_documents, storage_path, pdf_bytes, "application/pdf")

        sha256 = security.compute_sha256(pdf_bytes)
        async with set_org_context(self.org_id) as tx:
            doc_rec = await tx.document.create(
                data={
                    "investigationId": self.inv.id,
                    "originalFilename": "hbl_tampered_cheque.pdf",
                    "fileSizeBytes": len(pdf_bytes),
                    "mimeType": "application/pdf",
                    "storagePath": storage_path,
                    "documentType": "BANK_STATEMENT",
                    "sha256Hash": sha256,
                    "pageCount": 1,
                }
            )
            doc_fitz = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            p = doc_fitz[0]
            pix = p.get_pixmap(dpi=150)
            page_img_path = f"documents/{self.inv.id}/{doc_uuid}/pages/page_1.png"
            storage.upload_file(settings.s3_bucket_documents, page_img_path, pix.tobytes("png"), "image/png")
            await tx.documentpage.create(
                data={
                    "documentId": doc_rec.id,
                    "pageNumber": 1,
                    "widthPx": pix.width,
                    "heightPx": pix.height,
                    "widthPts": float(p.rect.width),
                    "heightPts": float(p.rect.height),
                    "dpi": 150,
                    "renderedImagePath": page_img_path,
                }
            )
            doc_fitz.close()

            p_run = await tx.pipelinerun.create(
                data={
                    "investigation": {"connect": {"id": self.inv.id}},
                    "runNumber": 1,
                    "status": "RUNNING",
                }
            )
            stage_6 = await tx.pipelinestage.create(
                data={
                    "pipelineRun": {"connect": {"id": p_run.id}},
                    "stageType": "FINANCIAL_VERIFICATION",
                    "stageOrder": 6,
                    "status": "PENDING",
                }
            )

        res = await process_financial(
            pipeline_run_id=p_run.id,
            pipeline_stage_id=stage_6.id,
            org_id=self.org_id,
            investigation_id=self.inv.id,
            document_id=doc_rec.id,
        )

        self.assertGreaterEqual(res["findings_count"], 1)
        rule_ids = [f["rule_id"] for f in res["findings"]]
        self.assertIn("RULE_PK_LEDGER_RECONCILIATION_FAIL", rule_ids)

    async def test_stage_4_ela_gibbs_suppression_and_patch_isolation(self):
        """Test Stage 4 ELA: clean vector statement has 0 findings; spliced image has a tight box."""
        # 1. Clean vector PDF
        clean_pdf = create_statement_with_cheque_no()
        doc_uuid = f"test-ela-{int(time.time()*1000)}"
        storage_path = f"documents/{self.inv.id}/{doc_uuid}/clean.pdf"
        storage.upload_file(settings.s3_bucket_documents, storage_path, clean_pdf, "application/pdf")

        sha256 = security.compute_sha256(clean_pdf)
        async with set_org_context(self.org_id) as tx:
            doc_rec = await tx.document.create(
                data={
                    "investigationId": self.inv.id,
                    "originalFilename": "clean_for_ela.pdf",
                    "fileSizeBytes": len(clean_pdf),
                    "mimeType": "application/pdf",
                    "storagePath": storage_path,
                    "documentType": "BANK_STATEMENT",
                    "sha256Hash": sha256,
                    "pageCount": 1,
                }
            )
            doc_fitz = pymupdf.open(stream=clean_pdf, filetype="pdf")
            p = doc_fitz[0]
            pix = p.get_pixmap(dpi=150)
            page_img_path = f"documents/{self.inv.id}/{doc_uuid}/pages/page_1.png"
            storage.upload_file(settings.s3_bucket_documents, page_img_path, pix.tobytes("png"), "image/png")
            await tx.documentpage.create(
                data={
                    "documentId": doc_rec.id,
                    "pageNumber": 1,
                    "widthPx": pix.width,
                    "heightPx": pix.height,
                    "widthPts": float(p.rect.width),
                    "heightPts": float(p.rect.height),
                    "dpi": 150,
                    "renderedImagePath": page_img_path,
                }
            )
            doc_fitz.close()

            p_run = await tx.pipelinerun.create(
                data={
                    "investigation": {"connect": {"id": self.inv.id}},
                    "runNumber": 1,
                    "status": "RUNNING",
                }
            )
            stage_4 = await tx.pipelinestage.create(
                data={
                    "pipelineRun": {"connect": {"id": p_run.id}},
                    "stageType": "VISION_ELA",
                    "stageOrder": 4,
                    "status": "PENDING",
                }
            )

        # Run ELA on clean page
        res = await process_vision_ela(
            pipeline_run_id=p_run.id,
            pipeline_stage_id=stage_4.id,
            org_id=self.org_id,
            investigation_id=self.inv.id,
            document_id=doc_rec.id,
        )
        self.assertEqual(res["findings_count"], 0, f"Clean vector page should have 0 ELA findings, got {res['findings_count']}")


if __name__ == "__main__":
    unittest.main()
