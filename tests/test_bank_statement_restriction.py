"""
Automated Integration Tests for Bank Statement Restriction Enforcement.
Validates:
  1. Upload Gate: Non-bank documents (utility bills, salary slips, generic PDFs) are rejected with HTTP 422.
  2. Upload Gate: Legitimate bank statements (Meezan, HBL, standard SBP formats) are accepted with HTTP 201.
  3. Pipeline Gate: In run_pipeline_inline, if Stage 0 detects a non-bank document, downstream stages 1–8 are canceled
     and the PipelineRun and Investigation are marked FAILED with an explicit error message.
"""
import io
import time
import pytest
import pymupdf
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.client import db, connect, set_org_context
from app.core import security, storage
from app.config import get_settings
from app.features.pipeline.service import run_pipeline_inline, STAGE_FLOW

settings = get_settings()


def create_mock_bank_statement() -> bytes:
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 50), f"TEST_RUN_{time.time()}", fontsize=8)
    p.insert_text((50, 80), "MEEZAN BANK LIMITED - STATEMENT OF ACCOUNT", fontsize=16)
    p.insert_text((50, 110), "Account No: 0102-0103492819 | IBAN: PK36MEZN0001020103492819", fontsize=10)
    p.insert_text((50, 140), "Opening Balance: PKR 1,500,000.00", fontsize=10)
    p.insert_text((50, 160), "Total Debits: PKR 200,000.00 | Total Credits: PKR 500,000.00", fontsize=10)
    p.insert_text((50, 180), "Closing Balance: PKR 1,800,000.00", fontsize=10)
    b = doc.tobytes()
    doc.close()
    return b


def create_mock_utility_bill() -> bytes:
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 50), f"BILL_RUN_{time.time()}", fontsize=8)
    p.insert_text((50, 80), "K-ELECTRIC - ELECTRICITY CONSUMER BILL", fontsize=16)
    p.insert_text((50, 110), "Consumer No: 040009876543 | Tariff: A1-R Res", fontsize=10)
    p.insert_text((50, 140), "Units Consumed: 420 kWh | Due Date: 28-Mar-2026", fontsize=10)
    p.insert_text((50, 160), "Current Electricity Charges: PKR 18,500.00", fontsize=10)
    p.insert_text((50, 180), "Amount Payable Within Due Date: PKR 19,800.00", fontsize=10)
    b = doc.tobytes()
    doc.close()
    return b


def create_mock_salary_slip() -> bytes:
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 50), f"PAY_RUN_{time.time()}", fontsize=8)
    p.insert_text((50, 80), "CONFIDENTIAL PAYSLIP - MONTH OF FEBRUARY 2026", fontsize=16)
    p.insert_text((50, 110), "Employee ID: EMP-10928 | Designation: Senior Software Engineer", fontsize=10)
    p.insert_text((50, 140), "Basic Salary: PKR 300,000.00 | House Rent Allowance: PKR 120,000.00", fontsize=10)
    p.insert_text((50, 160), "Gross Salary: PKR 450,000.00 | Total Deductions: PKR 55,000.00", fontsize=10)
    p.insert_text((50, 180), "Net Salary: PKR 395,000.00 (Take Home Pay)", fontsize=10)
    b = doc.tobytes()
    doc.close()
    return b


@pytest.mark.asyncio
async def test_upload_rejection_for_non_bank_documents():
    """Verify upload endpoint strictly rejects non-bank documents with HTTP 422."""
    if not db.is_connected():
        await connect()

    org = await db.organization.find_first()
    if not org:
        pytest.skip("No organization found in database")

    t_now = int(time.time() * 1000)
    async with set_org_context(org.id) as tx:
        user = await tx.user.find_first(where={"organizationId": org.id})
        if not user:
            user = await tx.user.create(
                data={
                    "organizationId": org.id,
                    "email": f"analyst-{t_now}@deeptrace.test",
                    "firstName": "Forensic",
                    "lastName": "Analyst",
                    "passwordHash": security.hash_password("Analyst@12345"),
                    "role": "ANALYST",
                }
            )
        inv = await tx.investigation.create(
            data={
                "organizationId": org.id,
                "userId": user.id,
                "title": f"Upload Gate Test Case {t_now}",
                "caseNumber": f"DT-TEST-GATE-{t_now}",
                "status": "CREATED",
            }
        )

    token = security.create_access_token(user.id, {"org_id": org.id, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Attempt upload of Utility Bill -> Should be rejected with HTTP 422
        ke_bill = create_mock_utility_bill()
        resp_util = await client.post(
            f"/api/v1/investigations/{inv.id}/documents",
            headers=headers,
            files={"file": ("ke_bill.pdf", ke_bill, "application/pdf")},
            data={"document_type": "BANK_STATEMENT"},  # Even if spoofed by caller
        )
        assert resp_util.status_code == 422
        util_res = resp_util.json()
        util_err = util_res.get("error", {}).get("message") or util_res.get("detail", "") or str(util_res)
        assert "DeepTrace strictly accepts and analyzes Bank Statements" in util_err
        assert "Utility Bill" in util_err

        # 2. Attempt upload of Salary Slip -> Should be rejected with HTTP 422
        salary_slip = create_mock_salary_slip()
        resp_sal = await client.post(
            f"/api/v1/investigations/{inv.id}/documents",
            headers=headers,
            files={"file": ("payslip.pdf", salary_slip, "application/pdf")},
            data={"document_type": "BANK_STATEMENT"},
        )
        assert resp_sal.status_code == 422
        sal_res = resp_sal.json()
        sal_err = sal_res.get("error", {}).get("message") or sal_res.get("detail", "") or str(sal_res)
        assert "DeepTrace strictly accepts and analyzes Bank Statements" in sal_err
        assert "Salary Slip" in sal_err

        # 3. Upload genuine Bank Statement -> Should succeed with HTTP 201
        bank_stmt = create_mock_bank_statement()
        resp_bank = await client.post(
            f"/api/v1/investigations/{inv.id}/documents",
            headers=headers,
            files={"file": ("meezan_statement.pdf", bank_stmt, "application/pdf")},
            data={"document_type": "BANK_STATEMENT"},
        )
        assert resp_bank.status_code == 201
        data = resp_bank.json()
        assert data["document_type"] == "BANK_STATEMENT"

    # Cleanup test investigation
    async with set_org_context(org.id) as tx:
        await tx.execute_raw("SELECT set_config('app.allow_test_cleanup', 'true', false);")
        await tx.document.delete_many(where={"investigationId": inv.id})
        await tx.investigation.delete(where={"id": inv.id})


@pytest.mark.asyncio
async def test_pipeline_execution_gate_halts_non_bank_documents():
    """Verify run_pipeline_inline halts stages 1-8 if a non-bank document enters the pipeline."""
    if not db.is_connected():
        await connect()

    org = await db.organization.find_first()
    if not org:
        pytest.skip("No organization found in database")

    t_now = int(time.time() * 1000)
    async with set_org_context(org.id) as tx:
        user = await tx.user.find_first(where={"organizationId": org.id})
        if not user:
            user = await tx.user.create(
                data={
                    "organizationId": org.id,
                    "email": f"analyst-pipe-{t_now}@deeptrace.test",
                    "firstName": "Forensic",
                    "lastName": "Analyst",
                    "passwordHash": security.hash_password("Analyst@12345"),
                    "role": "ANALYST",
                }
            )
        inv = await tx.investigation.create(
            data={
                "organizationId": org.id,
                "userId": user.id,
                "title": f"Pipeline Gate Test Case {t_now}",
                "caseNumber": f"DT-TEST-PIPE-{t_now}",
                "status": "PROCESSING",
            }
        )

        # Directly store a non-bank PDF to test pipeline execution guard
        ke_bill = create_mock_utility_bill()
        doc_key = f"documents/{inv.id}/ke_bill_guard.pdf"
        storage.storage.upload_file(settings.s3_bucket_documents, doc_key, ke_bill, "application/pdf")

        doc = await tx.document.create(
            data={
                "investigationId": inv.id,
                "originalFilename": "ke_bill_guard.pdf",
                "mimeType": "application/pdf",
                "fileSizeBytes": len(ke_bill),
                "documentType": "OTHER",
                "sha256Hash": f"sha256_pipe_{t_now}",
                "storagePath": doc_key,
                "processingStatus": "UPLOADED",
            }
        )

        run = await tx.pipelinerun.create(
            data={
                "investigationId": inv.id,
                "runNumber": 1,
                "status": "PENDING",
                "triggerSource": "test",
                "triggerUserId": user.id,
            }
        )

        # Pre-create all stages
        for order, stage_type, _, _ in STAGE_FLOW:
            await tx.pipelinestage.create(
                data={
                    "pipelineRunId": run.id,
                    "stageType": stage_type,
                    "stageOrder": order,
                    "status": "PENDING",
                }
            )

    # Execute inline pipeline
    await run_pipeline_inline(
        pipeline_run_id=run.id,
        org_id=org.id,
        investigation_id=inv.id,
        document_id=doc.id,
    )

    # Verify pipeline run failed and downstream stages were cancelled
    async with set_org_context(org.id) as tx:
        updated_run = await tx.pipelinerun.find_unique(where={"id": run.id})
        assert updated_run.status == "FAILED"
        assert "DeepTrace strictly executes forensic analysis on Bank Statements" in updated_run.errorMessage
        assert "Utility Bill" in updated_run.errorMessage

        updated_inv = await tx.investigation.find_unique(where={"id": inv.id})
        assert updated_inv.status == "FAILED"

        stages = await tx.pipelinestage.find_many(where={"pipelineRunId": run.id})
        assert len(stages) == len(STAGE_FLOW)
        for s in stages:
            assert s.status == "CANCELLED"
            assert "Halted: Non-bank statement rejected" in (s.errorMessage or "")

        # Cleanup
        await tx.execute_raw("SELECT set_config('app.allow_test_cleanup', 'true', false);")
        await tx.pipelinestage.delete_many(where={"pipelineRunId": run.id})
        await tx.pipelinerun.delete(where={"id": run.id})
        await tx.document.delete(where={"id": doc.id})
        await tx.investigation.delete(where={"id": inv.id})
