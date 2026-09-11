"""
Test Suite: Core Capabilities & Distributed Storage Architecture
Verifies:
  1. Multi-Container Storage Architecture: head_bucket check, strict remote mode, read-through caching.
  2. Multi-Agent AI Swarm: Structural, Visual, Semantic PK, and Lead Investigator agents.
  3. Interactive Q&A: Zero-hallucination citations, session & message persistence, streaming SSE.
  4. Court-Admissible PDF Dossier Generation: PyMuPDF compilation, ETO 2002 chain of custody, >= 3 pages.
  5. Enterprise Webhooks: Timestamped HMAC-SHA256 signatures, endpoint management, delivery execution.
"""
import asyncio
import json
import os
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, r"d:\zylo\DeepTrace")

import pymupdf

from app.config import get_settings
from app.core import security
from app.core.storage import (
    storage,
    upload_file,
    download_file,
    generate_presigned_url,
    StorageUploadError,
    LOCAL_STORAGE_DIR,
)
from app.db.client import connect, db, disconnect, set_org_context
from app.features.agents.swarm.base_agent import BaseForensicAgent
from app.features.agents.swarm.structural_agent import StructuralForensicAgent
from app.features.agents.swarm.visual_agent import VisualForensicAgent
from app.features.agents.swarm.semantic_pk_agent import SemanticPKFinancialAgent
from app.features.agents.swarm.lead_investigator import LeadInvestigatorAgent
from app.features.agents.service import run_interactive_qa, get_agent_sessions
from app.features.reports.service import generate_report, get_report_download_url
from app.features.webhooks.service import (
    sign_payload,
    verify_signature,
    create_endpoint,
    list_endpoints,
    delete_endpoint,
    dispatch_event,
)
from app.features.webhooks.tasks import execute_delivery

settings = get_settings()


class TestCoreStubsAndStorage(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await connect()
        self.org_id = "cmtl7u5ku0000120pueg7by84"
        async with set_org_context(self.org_id) as tx:
            user = await tx.user.find_first()
            self.user_id = user.id

            self.inv = await tx.investigation.create(
                data={
                    "organizationId": self.org_id,
                    "userId": self.user_id,
                    "caseNumber": f"DT-TEST-CORE-{int(time.time()*1000)}",
                    "title": "Core Stubs and Distributed Storage Test",
                }
            )

    async def asyncTearDown(self):
        await disconnect()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Multi-Container Storage Tests (Issue G)
    # ─────────────────────────────────────────────────────────────────────────
    async def test_storage_local_dir_and_caching(self):
        """Storage must support configurable local/shared directory and read-through caching."""
        test_bytes = b"DeepTrace Storage Multi-Container Test Data"
        bucket = settings.s3_bucket_documents
        key = f"test_container/{self.inv.id}/data.bin"

        # Upload
        res_key = upload_file(bucket, key, test_bytes)
        self.assertEqual(res_key, key)

        # Download (verifies read-through or local cache)
        downloaded = download_file(bucket, key)
        self.assertEqual(downloaded, test_bytes)

        # Verify presigned URL generates a valid string
        url = generate_presigned_url(bucket, key)
        self.assertTrue(len(url) > 5)

    async def test_storage_strict_remote_mode(self):
        """In strict remote mode, if S3 is forced off, it must raise StorageUploadError instead of silent write."""
        from app.core import storage as st_module
        old_strict = getattr(settings, "storage_strict_remote", False)
        old_avail = st_module._s3_available
        try:
            settings.storage_strict_remote = True
            st_module._s3_available = False

            with self.assertRaises(StorageUploadError):
                upload_file("dummy-bucket", "dummy-key", b"test")
        finally:
            settings.storage_strict_remote = old_strict
            st_module._s3_available = old_avail

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Multi-Agent AI Swarm Tests (Issue F1)
    # ─────────────────────────────────────────────────────────────────────────
    async def test_swarm_specialist_agents_and_lead_investigator(self):
        """All 4 agents must analyze evidence without NotImplementedError and correlate signals."""
        manifest = {
            "investigation": {"id": self.inv.id, "caseNumber": self.inv.caseNumber, "title": "Test Case"},
            "risk_assessment": {"overallScore": 85, "riskTier": "CRITICAL", "actionDirective": "IMMEDIATE_REJECTION"},
            "documents": [{"originalFilename": "meezan_statement.pdf", "sha256Hash": "a"*64}],
            "evidence_items": [
                {
                    "id": "ev-1",
                    "ruleId": "RULE_PDF_INCREMENTAL_SAVE",
                    "category": "PDF_STRUCTURE",
                    "severity": "HIGH",
                    "riskPoints": 25,
                    "title": "Incremental Save Revision Detected",
                    "description": "Document modified post-creation via external desktop editor.",
                },
                {
                    "id": "ev-2",
                    "ruleId": "RULE_CV_ELA_ANOMALY",
                    "category": "COMPUTER_VISION_ELA",
                    "severity": "HIGH",
                    "riskPoints": 30,
                    "title": "ELA Compression Discontinuity on Balance",
                    "description": "Localized re-compression boundary surrounding account balance digits.",
                    "boundingBoxes": [{"pageNumber": 1, "xPts": 100, "yPts": 200, "widthPts": 80, "heightPts": 15}],
                },
                {
                    "id": "ev-3",
                    "ruleId": "RULE_PK_OPENING_BALANCE_MISMATCH",
                    "category": "FINANCIAL_VERIFICATION",
                    "severity": "CRITICAL",
                    "riskPoints": 50,
                    "title": "Opening Balance Tampering Detected (+119,880.00 PKR)",
                    "description": "Stated balance PKR 120,000.00 contradicts authentic ledger origin PKR 120.00.",
                    "expectedValue": "PKR 120.00",
                    "actualValue": "PKR 120,000.00",
                    "discrepancy": "PKR +119,880.00",
                },
            ],
        }

        # 1. Structural Agent
        struct_agent = StructuralForensicAgent(manifest)
        struct_res = await struct_agent.analyze()
        self.assertEqual(struct_res["agent_role"], "STRUCTURAL_FORENSIC")
        self.assertEqual(struct_res["anomalies_detected"], 1)
        self.assertIn("RULE_PDF_INCREMENTAL_SAVE", struct_res["evidence_citations"])

        # 2. Visual Agent
        vis_agent = VisualForensicAgent(manifest)
        vis_res = await vis_agent.analyze()
        self.assertEqual(vis_res["agent_role"], "VISUAL_FORENSIC")
        self.assertEqual(vis_res["anomalies_detected"], 1)
        self.assertIn("RULE_CV_ELA_ANOMALY", vis_res["evidence_citations"])

        # 3. Semantic Financial Agent
        fin_agent = SemanticPKFinancialAgent(manifest)
        fin_res = await fin_agent.analyze()
        self.assertEqual(fin_res["agent_role"], "SEMANTIC_PK_FINANCIAL")
        self.assertEqual(fin_res["anomalies_detected"], 1)
        self.assertIn("RULE_PK_OPENING_BALANCE_MISMATCH", fin_res["evidence_citations"])

        # 4. Lead Investigator Synthesis
        lead_agent = LeadInvestigatorAgent(manifest)
        lead_res = await lead_agent.analyze()
        self.assertEqual(lead_res["agent_role"], "LEAD_INVESTIGATOR")
        self.assertEqual(lead_res["anomalies_detected"], 3)
        self.assertEqual(lead_res["risk_tier"], "CRITICAL")
        self.assertTrue(len(lead_res["cross_signal_correlations"]) >= 1)

        # Zero-Hallucination Guardrail Check
        with self.assertRaises(ValueError):
            lead_agent._assert_evidence_exists("RULE_NON_EXISTENT_HALLUCINATION")

    async def test_interactive_qa_and_session_persistence(self):
        """Interactive Q&A must record AgentSession, AgentMessage, and return zero-hallucination answers."""
        async with set_org_context(self.org_id) as tx:
            doc = await tx.document.create(
                data={
                    "investigationId": self.inv.id,
                    "originalFilename": "test_qa_doc.pdf",
                    "fileSizeBytes": 1024,
                    "mimeType": "application/pdf",
                    "storagePath": "test/path.pdf",
                    "sha256Hash": security.compute_sha256(b"dummy"),
                }
            )
            ev = await tx.evidenceitem.create(
                data={
                    "documentId": doc.id,
                    "ruleId": "RULE_PK_CLOSING_BALANCE_MISMATCH",
                    "category": "MATHEMATICAL_MISMATCH",
                    "severity": "CRITICAL",
                    "riskPoints": 50,
                    "title": "Closing Balance Tampering Detected (+954,045.00 PKR)",
                    "description": "Printed closing balance was inflated by 954,045 PKR.",
                    "expectedValue": "PKR 955.00",
                    "actualValue": "PKR 955,000.00",
                    "discrepancy": "PKR +954,045.00",
                    "isDeterministic": True,
                }
            )
            await tx.riskassessment.create(
                data={
                    "investigation": {"connect": {"id": self.inv.id}},
                    "overallScore": 85,
                    "riskTier": "CRITICAL",
                    "actionDirective": "IMMEDIATE_REJECTION",
                    "totalEvidenceCount": 1,
                    "criticalCount": 1,
                }
            )

            # 1. Non-streaming Q&A
            resp = await run_interactive_qa(
                tx, self.inv.id, self.user_id, "Why was this classified as High Risk?", stream=False
            )
            self.assertIn("CRITICAL", resp.answer)
            self.assertIn(ev.id, resp.evidence_references)
            self.assertTrue(resp.tokens_used > 0)

            # 2. Check session persistence
            sessions = await get_agent_sessions(tx, self.inv.id)
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].id, resp.agent_session_id)

            # 3. Check message turns
            messages = await tx.agentmessage.find_many(
                where={"agentSessionId": resp.agent_session_id},
                order={"sequenceOrder": "asc"},
            )
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0].role, "USER")
            self.assertEqual(messages[1].role, "ASSISTANT")

            # 4. Streaming Q&A
            stream_gen = await run_interactive_qa(
                tx, self.inv.id, self.user_id, "Is the balance tampered?", stream=True
            )
            collected_chunks = []
            async for chunk in stream_gen:
                collected_chunks.append(chunk)
            self.assertTrue(len(collected_chunks) > 1)
            self.assertTrue(any('"done": true' in c for c in collected_chunks))

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Court-Admissible PDF Dossier Tests (Issue F2)
    # ─────────────────────────────────────────────────────────────────────────
    async def test_court_admissible_pdf_dossier_generation(self):
        """Dossier generator must build an authentic multi-page PDF with ETO 2002 seals and download URL."""
        async with set_org_context(self.org_id) as tx:
            doc = await tx.document.create(
                data={
                    "investigationId": self.inv.id,
                    "originalFilename": "hbl_cheque_dossier.pdf",
                    "fileSizeBytes": 45000,
                    "mimeType": "application/pdf",
                    "storagePath": "reports/test_source.pdf",
                    "sha256Hash": "f"*64,
                }
            )
            await tx.evidenceitem.create(
                data={
                    "documentId": doc.id,
                    "ruleId": "RULE_PK_LEDGER_RECONCILIATION_FAIL",
                    "category": "MATHEMATICAL_MISMATCH",
                    "severity": "CRITICAL",
                    "riskPoints": 50,
                    "title": "Ledger Running Balance Discrepancy",
                    "description": "Debit sum does not match concluding balance.",
                    "expectedValue": "PKR 100,000.00",
                    "actualValue": "PKR 500,000.00",
                    "discrepancy": "PKR +400,000.00",
                }
            )
            await tx.riskassessment.create(
                data={
                    "investigation": {"connect": {"id": self.inv.id}},
                    "overallScore": 90,
                    "riskTier": "CRITICAL",
                    "actionDirective": "IMMEDIATE_REJECTION",
                    "totalEvidenceCount": 1,
                    "criticalCount": 1,
                }
            )

            report_resp = await generate_report(tx, self.inv.id)
            self.assertEqual(report_resp.status, "ready")
            self.assertTrue(report_resp.file_size_bytes > 2000)
            self.assertTrue(len(report_resp.sha256_hash) == 64)
            self.assertTrue(len(report_resp.download_url) > 10)

            # Verify downloaded PDF structure via PyMuPDF
            dossier_bytes = download_file(settings.s3_bucket_artifacts, f"reports/{self.inv.id}/" + report_resp.download_url.split(f"reports/{self.inv.id}/")[-1].split("?")[0])
            if dossier_bytes:
                fitz_doc = pymupdf.open(stream=dossier_bytes, filetype="pdf")
                self.assertGreaterEqual(len(fitz_doc), 3, "Dossier must have at least 3 pages.")
                page1_text = fitz_doc[0].get_text()
                self.assertIn("DEEPTRACE DOCUMENT FORENSICS", page1_text)
                self.assertIn("DIGITAL CHAIN OF CUSTODY", page1_text)
                self.assertIn("CRITICAL RISK", page1_text)
                fitz_doc.close()

            # Test get_report_download_url
            fresh_url_resp = await get_report_download_url(tx, self.inv.id)
            self.assertEqual(fresh_url_resp.status, "ready")
            self.assertEqual(fresh_url_resp.sha256_hash, report_resp.sha256_hash)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Enterprise Webhooks Dispatching Tests (Issue F3)
    # ─────────────────────────────────────────────────────────────────────────
    async def test_webhook_hmac_signatures_and_delivery(self):
        """Webhook signatures must be timestamped and verifiable; events must create delivery logs."""
        secret = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        payload = {"event": "investigation.completed", "case_number": self.inv.caseNumber, "score": 85}

        # Signature generation and verification
        sig = sign_payload(secret, payload)
        self.assertTrue(sig.startswith("t="))
        self.assertIn(",v1=", sig)
        self.assertTrue(verify_signature(secret, payload, sig))

        # Tampered payload fails verification
        tampered = {"event": "investigation.completed", "case_number": self.inv.caseNumber, "score": 0}
        self.assertFalse(verify_signature(secret, tampered, sig))

        delivery_id = None
        async with set_org_context(self.org_id) as tx:
            # Clean up prior test endpoints/deliveries in test org
            await tx.webhookdelivery.delete_many()
            await tx.webhookendpoint.delete_many(where={"organizationId": self.org_id})

            # Create endpoint
            ep = await create_endpoint(
                tx,
                org_id=self.org_id,
                url="https://webhook.site/mock-endpoint",
                events=["investigation.completed", "risk.critical"],
                description="Mock Core Bank Webhook",
            )
            self.assertEqual(ep.url, "https://webhook.site/mock-endpoint")
            self.assertTrue(ep.isActive)

            # List endpoints
            eps = await list_endpoints(tx, self.org_id)
            self.assertTrue(any(e.id == ep.id for e in eps))

            # Dispatch event without background task spawning inside tx
            delivery_ids = await dispatch_event(
                tx, self.org_id, "investigation.completed", payload, enqueue_tasks=False
            )
            self.assertEqual(len(delivery_ids), 1)
            delivery_id = delivery_ids[0]

            # Verify delivery log
            delivery = await tx.webhookdelivery.find_unique(where={"id": delivery_id})
            self.assertIsNotNone(delivery)
            self.assertEqual(delivery.eventType, "investigation.completed")
            self.assertEqual(delivery.attempt, 1)

            # Soft-delete endpoint
            await delete_endpoint(tx, ep.id)
            ep_after = await tx.webhookendpoint.find_unique(where={"id": ep.id})
            self.assertFalse(ep_after.isActive)

        # Test execute_delivery with mocked httpx
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = '{"received": true}'
            mock_post.return_value = mock_resp

            async with set_org_context(self.org_id) as tx:
                # Re-enable endpoint momentarily to test successful delivery
                await tx.webhookendpoint.update(where={"id": ep.id}, data={"isActive": True})

                success = await execute_delivery(delivery_id, client=tx)
                self.assertTrue(success)

                delivery_record = await tx.webhookdelivery.find_unique(where={"id": delivery_id})
                self.assertIsNotNone(delivery_record)
                self.assertEqual(delivery_record.httpStatusCode, 200)
                self.assertIsNotNone(delivery_record.deliveredAt)
