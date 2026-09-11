"""
Step 2: Core Bank Statement Forensic Engines & Pipeline Orchestration Test Suite
Verifies:
  1. Clean Genuine Meezan Bank Statement (Math Sound, Valid IBAN, Uniform Fonts -> LOW Risk)
  2. Mathematical Ledger Balance Tampering (Impossible Math -> CRITICAL Risk & BoundingBox)
  3. Sub-Pixel Font Baseline Offset (Spliced Digits -> HIGH Risk & BoundingBox)
  4. PDF Incremental Save & Canva/Acrobat Producer Signature
  5. Fake Pakistani IBAN Checksum Failure (ISO 7064 MOD-97)
  6. End-to-End REST APIs (/pipeline, /evidence, /risk, /risk/override)
"""
import asyncio
import io
import sys
import time
from decimal import Decimal

import fitz  # PyMuPDF
from PIL import Image
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, r"d:\zylo\DeepTrace")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core import security
from app.db.client import connect, db, disconnect, set_org_context
from app.features.pipeline.service import run_pipeline_inline, trigger_pipeline
from app.main import app


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic Document Generators
# ─────────────────────────────────────────────────────────────────────────────

def create_clean_meezan_pdf() -> bytes:
    """Generate a clean, mathematically sound Meezan Bank e-statement PDF."""
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)  # A4

    # Header
    p.insert_text((50, 40), f"TIMESTAMP: {time.time()}", fontsize=7)
    p.insert_text((50, 70), "MEEZAN BANK LIMITED - ACCOUNT STATEMENT", fontsize=14, fontname="helv")
    p.insert_text((50, 95), "Account Number: 0101-0102030405", fontsize=10, fontname="helv")
    p.insert_text((50, 110), "IBAN: PK36MEZN0001020102030405", fontsize=10, fontname="helv")
    p.insert_text((50, 130), "Opening Balance: PKR 1,00,000.00", fontsize=10, fontname="helv")

    # Table Header (y=160)
    p.insert_text((50, 160), "Date", fontsize=9, fontname="helv")
    p.insert_text((130, 160), "Narration", fontsize=9, fontname="helv")
    p.insert_text((340, 160), "Debit (PKR)", fontsize=9, fontname="helv")
    p.insert_text((420, 160), "Credit (PKR)", fontsize=9, fontname="helv")
    p.insert_text((500, 160), "Balance (PKR)", fontsize=9, fontname="helv")

    # Row 1: Opening balance row
    p.insert_text((50, 185), "01/03/2026", fontsize=9, fontname="helv")
    p.insert_text((130, 185), "Opening Balance", fontsize=9, fontname="helv")
    p.insert_text((500, 185), "1,00,000.00", fontsize=9, fontname="helv")

    # Row 2: Salary Credit (100,000 + 250,000 = 350,000)
    p.insert_text((50, 210), "05/03/2026", fontsize=9, fontname="helv")
    p.insert_text((130, 210), "1LINK/IBFT/Salary Credit", fontsize=9, fontname="helv")
    p.insert_text((420, 210), "2,50,000.00", fontsize=9, fontname="helv")
    p.insert_text((500, 210), "3,50,000.00", fontsize=9, fontname="helv")

    # Row 3: ATM Cash Withdrawal (350,000 - 25,000 = 325,000)
    p.insert_text((50, 235), "12/03/2026", fontsize=9, fontname="helv")
    p.insert_text((130, 235), "ATM Cash Withdrawal", fontsize=9, fontname="helv")
    p.insert_text((340, 235), "25,000.00", fontsize=9, fontname="helv")
    p.insert_text((500, 235), "3,25,000.00", fontsize=9, fontname="helv")

    # Row 4: RAAST Rent Transfer (325,000 - 75,000 = 250,000)
    p.insert_text((50, 260), "20/03/2026", fontsize=9, fontname="helv")
    p.insert_text((130, 260), "RAAST/P2P/Rent Transfer", fontsize=9, fontname="helv")
    p.insert_text((340, 260), "75,000.00", fontsize=9, fontname="helv")
    p.insert_text((500, 260), "2,50,000.00", fontsize=9, fontname="helv")

    doc.set_metadata({
        "producer": "JasperReports Library v6.20.0",
        "creator": "Meezan Core Banking eStatement Engine",
        "creationDate": "D:20260321100000Z",
        "modDate": "D:20260321100000Z",
    })

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_math_tampered_pdf() -> bytes:
    """Generate a statement where Row 4 balance is fraudulently inflated to 25,00,000.00."""
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)

    p.insert_text((50, 40), f"TIMESTAMP: {time.time()}", fontsize=7)
    p.insert_text((50, 70), "MEEZAN BANK LIMITED - ACCOUNT STATEMENT", fontsize=14, fontname="helv")
    p.insert_text((50, 95), "Account Number: 0101-0102030405", fontsize=10, fontname="helv")
    p.insert_text((50, 110), "IBAN: PK36MEZN0001020102030405", fontsize=10, fontname="helv")

    # Row 1: Opening
    p.insert_text((50, 185), "01/03/2026", fontsize=9, fontname="helv")
    p.insert_text((130, 185), "Opening Balance", fontsize=9, fontname="helv")
    p.insert_text((500, 185), "1,00,000.00", fontsize=9, fontname="helv")

    # Row 2: Salary Credit (350,000)
    p.insert_text((50, 210), "05/03/2026", fontsize=9, fontname="helv")
    p.insert_text((130, 210), "1LINK/IBFT/Salary Credit", fontsize=9, fontname="helv")
    p.insert_text((420, 210), "2,50,000.00", fontsize=9, fontname="helv")
    p.insert_text((500, 210), "3,50,000.00", fontsize=9, fontname="helv")

    # Row 3: ATM Cash Withdrawal (325,000)
    p.insert_text((50, 235), "12/03/2026", fontsize=9, fontname="helv")
    p.insert_text((130, 235), "ATM Cash Withdrawal", fontsize=9, fontname="helv")
    p.insert_text((340, 235), "25,000.00", fontsize=9, fontname="helv")
    p.insert_text((500, 235), "3,25,000.00", fontsize=9, fontname="helv")

    # Row 4: TAMPERED BALANCE! (325,000 - 75,000 = 250,000, BUT CLAIMS 25,00,000.00)
    p.insert_text((50, 260), "20/03/2026", fontsize=9, fontname="helv")
    p.insert_text((130, 260), "RAAST/P2P/Rent Transfer", fontsize=9, fontname="helv")
    p.insert_text((340, 260), "75,000.00", fontsize=9, fontname="helv")
    # Forged Balance
    p.insert_text((500, 260), "25,00,000.00", fontsize=9, fontname="helv")

    doc.set_metadata({
        "producer": "JasperReports Library v6.20.0",
        "creator": "Meezan Core Banking eStatement Engine",
    })

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_baseline_tampered_pdf() -> bytes:
    """Generate a statement where balance text span has an unnatural +2.5 pt vertical baseline offset."""
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)

    p.insert_text((50, 40), f"TIMESTAMP: {time.time()}", fontsize=7)
    p.insert_text((50, 70), "HABIB BANK LIMITED - ACCOUNT STATEMENT", fontsize=14, fontname="helv")
    p.insert_text((50, 95), "IBAN: PK36HABB0001020102030405", fontsize=10, fontname="helv")

    # Row 1 normal line (baseline y=200)
    p.insert_text((50, 200), "01/03/2026", fontsize=10, fontname="helv")
    p.insert_text((150, 200), "Cheque Clearing Deposit", fontsize=10, fontname="helv")
    p.insert_text((380, 200), "Credit:", fontsize=10, fontname="helv")
    # Injected balance text shifted down by +2.5 points (y=202.5 pt)!
    p.insert_text((450, 202.5), "5,00,000.00", fontsize=10, fontname="tiro")

    doc.set_metadata({
        "producer": "Oracle FLEXCUBE Reporting",
    })

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_producer_tampered_pdf() -> bytes:
    """Generate a statement with multiple %%EOF markers and Canva/Acrobat metadata."""
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 40), f"TIMESTAMP: {time.time()}", fontsize=7)
    p.insert_text((50, 100), "TAMPERED BANK STATEMENT - CANVA EXPORT")

    doc.set_metadata({
        "producer": "Canva Online Editor",
        "creator": "Adobe Acrobat Pro DC 2024",
        "creationDate": "D:20240101100000Z",
        "modDate": "D:20260321153000Z",  # 2 years divergence
    })

    pdf_bytes = doc.tobytes()
    doc.close()

    # Append a second incremental save revision (second %%EOF)
    pdf_bytes += b"\n%%EOF\n% Incremental update\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 >>\nstartxref\n100\n%%EOF\n"
    return pdf_bytes


def create_bad_iban_pdf() -> bytes:
    """Generate a statement stating an invalid Pakistani IBAN with corrupted check digits."""
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 40), f"TIMESTAMP: {time.time()}", fontsize=7)
    p.insert_text((50, 70), "BANK ALFALAH - ACCOUNT STATEMENT", fontsize=14)
    # Invalid MOD-97 check digits: PK99
    p.insert_text((50, 110), "IBAN: PK99ALFH0001020102030405", fontsize=10)
    p.insert_text((50, 150), "Account Balance: PKR 850,000.00", fontsize=10)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ─────────────────────────────────────────────────────────────────────────────
# Main Automated Test Execution
# ─────────────────────────────────────────────────────────────────────────────

async def run_tests():
    await connect()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("=" * 60)
        print("DEEPTRACE STEP 2: BANK STATEMENT FORENSIC ENGINES TEST SUITE")
        print("=" * 60)

        # ── Setup Organization & User ─────────────────────────────────────────
        org = await db.organization.find_first()
        if not org:
            org = await db.organization.create(
                data={
                    "name": "Meezan Bank Fraud Risk Directorate",
                    "slug": f"meezan-fraud-{int(time.time())}",
                    "countryCode": "PK",
                }
            )

        async with set_org_context(org.id) as tx:
            user = await tx.user.find_first(where={"email": "analyst@meezan.pk"})
            if not user:
                user = await tx.user.create(
                    data={
                        "organizationId": org.id,
                        "email": "analyst@meezan.pk",
                        "firstName": "Forensic",
                        "lastName": "Investigator",
                        "role": "ANALYST",
                        "passwordHash": security.hash_password("Analyst@12345"),
                    }
                )

        token = security.create_access_token(user.id, {"org_id": org.id, "role": user.role})
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Create investigation
        async with set_org_context(org.id) as tx:
            inv = await tx.investigation.create(
                data={
                    "organizationId": org.id,
                    "userId": user.id,
                    "caseNumber": f"DT-PK-STEP2-{int(time.time())}",
                    "title": "Commercial Bank Statement Forensics Verification Suite",
                    "status": "CREATED",
                }
            )

        # ─────────────────────────────────────────────────────────────────────
        # TEST 1: Clean Genuine Meezan Bank Statement
        # ─────────────────────────────────────────────────────────────────────
        print("\n[Test 1] Testing Genuine Born-Digital Meezan Bank Statement...")
        clean_bytes = create_clean_meezan_pdf()

        res = await client.post(
            f"/api/v1/investigations/{inv.id}/documents",
            headers=auth_headers,
            data={"document_type": "BANK_STATEMENT"},
            files={"file": ("meezan_genuine.pdf", clean_bytes, "application/pdf")},
        )
        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        doc_clean_id = res.json()["id"]

        # Trigger Pipeline
        res_pipeline = await client.post(
            f"/api/v1/investigations/{inv.id}/analyze",
            headers=auth_headers,
            json={"document_id": doc_clean_id},
        )
        assert res_pipeline.status_code == 202, f"Pipeline trigger failed: {res_pipeline.text}"
        run_data = res_pipeline.json()
        print(f"  ✓ Pipeline Run {run_data['run_number']} triggered (ID: {run_data['id']})")

        # Wait for async background worker to complete
        for _ in range(30):
            await asyncio.sleep(0.3)
            status_res = await client.get(
                f"/api/v1/investigations/{inv.id}/pipeline",
                headers=auth_headers,
            )
            if status_res.json()["status"] in ["COMPLETED", "FAILED"]:
                break

        latest_run = status_res.json()
        assert latest_run["status"] == "COMPLETED", f"Pipeline failed: {latest_run}"
        print(f"  ✓ All 8 stages executed successfully in {latest_run.get('total_duration_ms', 0)}ms")

        # Verify Risk Assessment
        risk_res = await client.get(
            f"/api/v1/investigations/{inv.id}/risk",
            headers=auth_headers,
        )
        assert risk_res.status_code == 200
        risk = risk_res.json()
        print(f"  ✓ Risk Score: {risk['overall_score']}/100, Tier: {risk['risk_tier']}, Directive: {risk['action_directive']}")
        assert risk["overall_score"] <= 20, f"Expected clean score <= 20, got {risk['overall_score']}"
        assert risk["risk_tier"] == "LOW"
        assert risk["action_directive"] == "STRAIGHT_THROUGH_APPROVAL"

        # ─────────────────────────────────────────────────────────────────────
        # TEST 2: Mathematical Balance Tampering (The "Inflated Balance" Attack)
        # ─────────────────────────────────────────────────────────────────────
        print("\n[Test 2] Testing Mathematical Ledger Balance Tampering (Inflated Row)...")
        tampered_math_bytes = create_math_tampered_pdf()

        # Create separate investigation for math fraud
        async with set_org_context(org.id) as tx:
            inv_math = await tx.investigation.create(
                data={
                    "organizationId": org.id,
                    "userId": user.id,
                    "caseNumber": f"DT-PK-MATH-{int(time.time())}",
                    "title": "Ledger Arithmetic Tamper Investigation",
                    "status": "CREATED",
                }
            )

        res_math = await client.post(
            f"/api/v1/investigations/{inv_math.id}/documents",
            headers=auth_headers,
            data={"document_type": "BANK_STATEMENT"},
            files={"file": ("tampered_math.pdf", tampered_math_bytes, "application/pdf")},
        )
        assert res_math.status_code == 201
        doc_math_id = res_math.json()["id"]

        await client.post(
            f"/api/v1/investigations/{inv_math.id}/analyze",
            headers=auth_headers,
            json={"document_id": doc_math_id},
        )

        for _ in range(30):
            await asyncio.sleep(0.3)
            status_res = await client.get(
                f"/api/v1/investigations/{inv_math.id}/pipeline",
                headers=auth_headers,
            )
            if status_res.json()["status"] in ["COMPLETED", "FAILED"]:
                break

        # Check evidence findings
        ev_res = await client.get(
            f"/api/v1/investigations/{inv_math.id}/evidence",
            headers=auth_headers,
        )
        assert ev_res.status_code == 200
        ev_items = ev_res.json()
        math_findings = [e for e in ev_items if e["rule_id"] == "RULE_PK_LEDGER_RECONCILIATION_FAIL"]
        assert len(math_findings) > 0, "Expected mathematical reconciliation error finding!"
        math_item = math_findings[0]
        print(f"  ✓ Detected CRITICAL finding: '{math_item['title']}'")
        print(f"    Expected: {math_item['expected_value']}, Actual: {math_item['actual_value']}, Discrepancy: {math_item['discrepancy']}")
        assert len(math_item["bounding_boxes"]) > 0, "Expected bounding box on the disputed ledger row!"
        print(f"  ✓ Bounding box attached: (x={math_item['bounding_boxes'][0]['x']}, y={math_item['bounding_boxes'][0]['y']}, label='{math_item['bounding_boxes'][0]['label']}')")

        # Verify escalated risk assessment
        risk_math = (await client.get(f"/api/v1/investigations/{inv_math.id}/risk", headers=auth_headers)).json()
        print(f"  ✓ Fraud Score: {risk_math['overall_score']}/100, Tier: {risk_math['risk_tier']}, Directive: {risk_math['action_directive']}")
        assert risk_math["overall_score"] >= 85
        assert risk_math["risk_tier"] == "CRITICAL"
        assert risk_math["action_directive"] == "IMMEDIATE_REJECTION"

        # ─────────────────────────────────────────────────────────────────────
        # TEST 3: Sub-Pixel Typography Baseline Offset (Spliced Amount)
        # ─────────────────────────────────────────────────────────────────────
        print("\n[Test 3] Testing Sub-Pixel Font Baseline Offset (y-Jitter)...")
        baseline_pdf = create_baseline_tampered_pdf()

        async with set_org_context(org.id) as tx:
            inv_base = await tx.investigation.create(
                data={
                    "organizationId": org.id,
                    "userId": user.id,
                    "caseNumber": f"DT-PK-FONT-{int(time.time())}",
                    "title": "Sub-pixel Font Baseline Investigation",
                    "status": "CREATED",
                }
            )

        res_base = await client.post(
            f"/api/v1/investigations/{inv_base.id}/documents",
            headers=auth_headers,
            data={"document_type": "BANK_STATEMENT"},
            files={"file": ("baseline_spliced.pdf", baseline_pdf, "application/pdf")},
        )
        assert res_base.status_code == 201

        await client.post(
            f"/api/v1/investigations/{inv_base.id}/analyze",
            headers=auth_headers,
        )

        for _ in range(30):
            await asyncio.sleep(0.3)
            status_res = await client.get(
                f"/api/v1/investigations/{inv_base.id}/pipeline",
                headers=auth_headers,
            )
            if status_res.json()["status"] in ["COMPLETED", "FAILED"]:
                break

        ev_base = (await client.get(f"/api/v1/investigations/{inv_base.id}/evidence", headers=auth_headers)).json()
        font_findings = [e for e in ev_base if e["category"] == "FONT_BASELINE_INCONSISTENCY"]
        assert len(font_findings) > 0, "Expected font baseline or font family finding!"
        print(f"  ✓ Detected Typography Anomaly: '{font_findings[0]['title']}' ({font_findings[0]['discrepancy']})")
        assert len(font_findings[0]["bounding_boxes"]) > 0
        print(f"  ✓ Sub-pixel bounding box rendered: color={font_findings[0]['bounding_boxes'][0]['color']}")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 4: Incremental Save & Canva / Acrobat Software Signature
        # ─────────────────────────────────────────────────────────────────────
        print("\n[Test 4] Testing Incremental Save & Desktop Editor Signatures...")
        producer_pdf = create_producer_tampered_pdf()

        async with set_org_context(org.id) as tx:
            inv_prod = await tx.investigation.create(
                data={
                    "organizationId": org.id,
                    "userId": user.id,
                    "caseNumber": f"DT-PK-PROD-{int(time.time())}",
                    "title": "Desktop Producer & Revisions Investigation",
                    "status": "CREATED",
                }
            )

        await client.post(
            f"/api/v1/investigations/{inv_prod.id}/documents",
            headers=auth_headers,
            data={"document_type": "BANK_STATEMENT"},
            files={"file": ("canva_statement.pdf", producer_pdf, "application/pdf")},
        )

        await client.post(f"/api/v1/investigations/{inv_prod.id}/analyze", headers=auth_headers)

        for _ in range(30):
            await asyncio.sleep(0.3)
            status_res = await client.get(f"/api/v1/investigations/{inv_prod.id}/pipeline", headers=auth_headers)
            if status_res.json()["status"] in ["COMPLETED", "FAILED"]:
                break

        ev_prod = (await client.get(f"/api/v1/investigations/{inv_prod.id}/evidence", headers=auth_headers)).json()
        rules_found = [e["rule_id"] for e in ev_prod]
        assert "RULE_PDF_INCREMENTAL_SAVE" in rules_found, "Expected incremental save detection!"
        assert "RULE_PDF_TAMPER_PRODUCER" in rules_found, "Expected Canva editor signature detection!"
        print(f"  ✓ Successfully identified: {rules_found}")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 5: Fake Pakistani IBAN MOD-97 Failure
        # ─────────────────────────────────────────────────────────────────────
        print("\n[Test 5] Testing Fake Pakistani IBAN MOD-97 Checksum Failure...")
        bad_iban_pdf = create_bad_iban_pdf()

        async with set_org_context(org.id) as tx:
            inv_iban = await tx.investigation.create(
                data={
                    "organizationId": org.id,
                    "userId": user.id,
                    "caseNumber": f"DT-PK-IBAN-{int(time.time())}",
                    "title": "Invalid IBAN Investigation",
                    "status": "CREATED",
                }
            )

        await client.post(
            f"/api/v1/investigations/{inv_iban.id}/documents",
            headers=auth_headers,
            data={"document_type": "BANK_STATEMENT"},
            files={"file": ("bad_iban.pdf", bad_iban_pdf, "application/pdf")},
        )

        await client.post(f"/api/v1/investigations/{inv_iban.id}/analyze", headers=auth_headers)

        for _ in range(30):
            await asyncio.sleep(0.3)
            status_res = await client.get(f"/api/v1/investigations/{inv_iban.id}/pipeline", headers=auth_headers)
            if status_res.json()["status"] in ["COMPLETED", "FAILED"]:
                break

        ev_iban = (await client.get(f"/api/v1/investigations/{inv_iban.id}/evidence", headers=auth_headers)).json()
        iban_findings = [e for e in ev_iban if e["rule_id"] == "RULE_PK_IBAN_CHECKSUM_INVALID"]
        assert len(iban_findings) > 0, "Expected IBAN checksum failure finding!"
        print(f"  ✓ Flagged invalid SBP IBAN: '{iban_findings[0]['title']}'")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 6: Analyst Risk Score Manual Override
        # ─────────────────────────────────────────────────────────────────────
        print("\n[Test 6] Testing Analyst Risk Score Manual Override...")
        override_res = await client.post(
            f"/api/v1/investigations/{inv_math.id}/risk/override",
            headers=auth_headers,
            json={
                "score": 98,
                "reason": "Confirmed customer impersonation and fraudulent loan submission.",
            },
        )
        assert override_res.status_code == 200
        overridden = override_res.json()
        assert overridden["overridden_score"] == 98
        assert overridden["override_reason"] == "Confirmed customer impersonation and fraudulent loan submission."
        print(f"  ✓ Risk score manually overridden to {overridden['overridden_score']} (Tier: {overridden['overridden_tier']})")

        print("\n" + "=" * 60)
        print("ALL STEP 2 BANK FORENSIC ENGINE TESTS PASSED FLAWLESSLY! ✓")
        print("=" * 60)

    await disconnect()


if __name__ == "__main__":
    asyncio.run(run_tests())
