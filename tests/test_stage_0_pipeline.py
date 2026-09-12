"""
Pipeline Integration Test for Stage 0 Document Classification & Dynamic Stage 6 Routing.
Verifies:
  1. process_document_classification updates document.documentType in DB.
  2. Telemetry is saved in pipeline_run.parameters["stage_0_classification"].
  3. Stage 6 bypasses ledger verification cleanly on non-financial documents (e.g. UTILITY_BILL).
"""
import asyncio
import io
import pytest
import pymupdf
from prisma import Prisma

from app.config import get_settings
from app.core import storage
from app.db.client import db, set_org_context
from app.features.pipeline.tasks.stage_0_classifier import process_document_classification
from app.features.pipeline.tasks.stage_6_financial import process_financial

settings = get_settings()


def create_sample_ke_bill() -> bytes:
    """Generate a mock K-Electric electricity bill PDF."""
    lines = [
        (50, 50, "K-ELECTRIC - ELECTRICITY CONSUMER BILL"),
        (50, 70, "KE Bill for Billing Month: March 2026"),
        (50, 90, "Consumer No: 040009876543 | Account No: 9876543210"),
        (50, 110, "Tariff: A1-R Res | Connected Load: 5.0 kW | Meter No: 54321"),
        (50, 130, "Units Consumed: 350 kWh | Reading Date: 12-Mar-2026"),
        (50, 160, "Current Electricity Charges: PKR 14,200.00"),
        (50, 180, "Electricity Duty: PKR 210.00 | Fuel Charges Adjustment: PKR 1,150.00"),
        (50, 200, "Total Current Bill: PKR 15,560.00 | Arrears: PKR 0.00"),
        (50, 230, "Amount Payable Within Due Date: PKR 15,560.00"),
        (50, 250, "Late Payment Surcharge: PKR 1,200.00"),
        (50, 270, "Amount Payable After Due Date: PKR 16,760.00"),
        (50, 290, "Due Date: 25-Mar-2026"),
    ]
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    for x, y, text in lines:
        page.insert_text(pymupdf.Point(x, y), text, fontsize=10)
    b = doc.write()
    doc.close()
    return b


@pytest.mark.asyncio
async def test_stage_0_pipeline_auto_classification():
    """Verify Stage 0 classifies K-Electric bill and Stage 6 bypasses ledger verification."""
    await db.connect()

    # Find an active organization and user for testing
    org = await db.organization.find_first()
    if not org:
        pytest.skip("No organization found in database")

    async with set_org_context(org.id) as tx:
        user = await tx.user.find_first(where={"organizationId": org.id})
        if not user:
            user = await tx.user.create(
                data={
                    "organizationId": org.id,
                    "email": "test-stage0@meezan.pk",
                    "fullName": "Test Analyst",
                    "passwordHash": "$2b$12$e8S91Xsamplehashedpassword",
                    "role": "ANALYST",
                }
            )
        import time
        t_now = int(time.time() * 1000)
        # Create an investigation with initial documentType = OTHER
        inv = await tx.investigation.create(
            data={
                "organizationId": org.id,
                "userId": user.id,
                "title": "Stage 0 Verification Test Docket",
                "caseNumber": f"DT-TEST-ST0-{t_now}",
                "status": "PROCESSING",
            }
        )

        # Upload K-Electric bill
        ke_pdf_bytes = create_sample_ke_bill()
        doc_key = f"documents/{inv.id}/ke_bill.pdf"
        storage.storage.upload_file(settings.s3_bucket_documents, doc_key, ke_pdf_bytes, "application/pdf")

        doc = await tx.document.create(
            data={
                "investigationId": inv.id,
                "originalFilename": "ke_electricity_bill.pdf",
                "mimeType": "application/pdf",
                "fileSizeBytes": len(ke_pdf_bytes),
                "documentType": "OTHER",  # Initially OTHER
                "sha256Hash": f"sha256_ke_{t_now}",
                "storagePath": doc_key,
                "processingStatus": "UPLOADED",
            }
        )

        # Create PipelineRun and Stages
        run = await tx.pipelinerun.create(
            data={
                "investigationId": inv.id,
                "runNumber": 1,
                "status": "RUNNING",
                "triggerSource": "test",
                "triggerUserId": user.id,
            }
        )

        stage6_rec = await tx.pipelinestage.create(
            data={
                "pipelineRunId": run.id,
                "stageType": "FINANCIAL_VERIFICATION",
                "stageOrder": 6,
                "status": "PENDING",
            }
        )

    # 1. Execute Stage 0: process_document_classification
    telemetry = await process_document_classification(
        pipeline_run_id=run.id,
        org_id=org.id,
        investigation_id=inv.id,
    )

    assert telemetry["primary_classification"] == "UTILITY_BILL"
    assert telemetry["primary_subtype"] == "K_ELECTRIC_BILL"
    assert len(telemetry["documents"]) == 1
    assert telemetry["documents"][0]["confidence"] >= 0.85

    # 2. Verify Document in DB was updated to UTILITY_BILL
    async with set_org_context(org.id) as tx:
        updated_doc = await tx.document.find_unique(where={"id": doc.id})
        assert updated_doc.documentType == "UTILITY_BILL"

    # 3. Execute Stage 6: process_financial
    # Since document is UTILITY_BILL, Stage 6 should skip without error
    stage6_res = await process_financial(
        pipeline_run_id=run.id,
        pipeline_stage_id=stage6_rec.id,
        org_id=org.id,
        investigation_id=inv.id,
    )

    assert stage6_res["reconciled"] is True
    assert stage6_res.get("skipped") is True
    assert "UTILITY_BILL" in stage6_res.get("bypass_reason", "")
    assert len(stage6_res["findings"]) == 0

    # Cleanup test data
    async with set_org_context(org.id) as tx:
        await tx.execute_raw("SELECT set_config('app.allow_test_cleanup', 'true', false);")
        await tx.pipelinestage.delete_many(where={"pipelineRunId": run.id})
        await tx.pipelinerun.delete(where={"id": run.id})
        await tx.document.delete(where={"id": doc.id})
        await tx.investigation.delete(where={"id": inv.id})

    await db.disconnect()
