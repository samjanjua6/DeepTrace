"""
Step 1: Document Ingestion, Custody Lock, and Page Rendering Test Suite
"""
import asyncio
import io
import sys
from pathlib import Path
sys.path.insert(0, r"d:\zylo\DeepTrace")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import fitz
from PIL import Image
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.client import db, connect, disconnect, set_org_context
from app.core import security


import time

def create_sample_pdf() -> bytes:
    doc = fitz.open()
    # Page 1
    p1 = doc.new_page(width=595, height=842)  # A4
    p1.insert_text((50, 50), f"RUN_ID: {time.time()}", fontsize=8)
    p1.insert_text((50, 80), "MEEZAN BANK STATEMENT - FORENSIC SAMPLE", fontsize=16)
    p1.insert_text((50, 120), "Account: 0102-0103492819 (PK36MEZN0001020103492819)", fontsize=11)
    p1.insert_text((50, 160), "Opening Balance: PKR 1,000,000.00", fontsize=11)
    p1.insert_text((50, 200), "Total Credits:   PKR   250,000.00", fontsize=11)
    p1.insert_text((50, 240), "Total Debits:    PKR    70,000.00", fontsize=11)
    p1.insert_text((50, 280), "Closing Balance: PKR 1,180,000.00", fontsize=11)
    # Page 2
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 80), "PAGE 2 - AUDIT TRAIL & TAX CHALLAN", fontsize=14)
    p2.insert_text((50, 120), "Tax deduction certificate ref # FBR-7749201", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_encrypted_pdf() -> bytes:
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 50), f"RUN_ID: {time.time()}", fontsize=8)
    p.insert_text((50, 100), "ENCRYPTED CONFIDENTIAL STATEMENT")
    pdf_bytes = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret123")
    doc.close()
    return pdf_bytes


def create_sample_png() -> bytes:
    import random
    img = Image.new("RGB", (800, 600), color=(random.randint(200, 250), 244, 248))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def run_tests():
    await connect()

    print("--- Setting up test organization, user & investigation ---")
    org = await db.organization.find_first(where={"slug": "meezan-bank"})
    if not org:
        org = await db.organization.create(
            data={"name": "Meezan Bank Ltd", "slug": "meezan-bank", "plan": "ENTERPRISE"}
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

        inv = await tx.investigation.find_first(where={"organizationId": org.id})
        if not inv:
            inv = await tx.investigation.create(
                data={
                    "organizationId": org.id,
                    "caseNumber": "DT-PK-TEST-0001",
                    "title": "Test Case Ingestion",
                    "createdById": user.id,
                }
            )

    token = security.create_access_token(user.id, {"org_id": org.id, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ── Test 1: Upload Born-Digital PDF ──────────────────────────────────
        print("\n[Test 1] Uploading Born-Digital Bank Statement (2-page PDF)...")
        pdf_bytes = create_sample_pdf()
        resp1 = await client.post(
            f"/api/v1/investigations/{inv.id}/documents",
            headers=headers,
            files={"file": ("meezan_statement.pdf", pdf_bytes, "application/pdf")},
            data={"document_type": "BANK_STATEMENT"},
        )
        assert resp1.status_code == 201, f"Expected 201, got {resp1.status_code}: {resp1.text}"
        data1 = resp1.json()
        doc_id = data1["id"]
        assert data1["original_filename"] == "meezan_statement.pdf"
        assert data1["page_count"] == 2
        assert data1["processing_status"] == "UPLOADED"
        assert len(data1["sha256_hash"]) == 64
        print(f"✓ Document uploaded successfully: ID={doc_id}, SHA-256={data1['sha256_hash'][:16]}..., Pages={data1['page_count']}")

        # ── Test 2: Check Rendered Pages and Point Dimensions ────────────────
        print("\n[Test 2] Verifying Rendered Page Images and Coordinates...")
        resp_pages = await client.get(
            f"/api/v1/investigations/{inv.id}/documents/{doc_id}/pages",
            headers=headers,
        )
        assert resp_pages.status_code == 200, f"Expected 200, got {resp_pages.status_code}: {resp_pages.text}"
        pages = resp_pages.json()
        assert len(pages) == 2
        for p in pages:
            assert p["width_pts"] == 595.0
            assert p["height_pts"] == 842.0
            assert p["dpi"] == 150
            assert p["rendered_image_url"] is not None
            print(f"✓ Page {p['page_number']}: {p['width_px']}x{p['height_px']}px, URL={p['rendered_image_url']}")

        # Test viewing the rendered image via the local storage streaming route
        page1_url = pages[0]["rendered_image_url"]
        resp_img = await client.get(page1_url, headers=headers)
        assert resp_img.status_code == 200
        assert resp_img.headers["content-type"] == "image/png"
        assert len(resp_img.content) > 1000
        print(f"✓ Rendered page 1 image streamed successfully ({len(resp_img.content)} bytes PNG)")

        # ── Test 3: Check Custody Log Event (NIST SP 800-86 / ETO 2002) ─────
        print("\n[Test 3] Verifying Digital Chain of Custody Event...")
        resp_custody = await client.get(
            f"/api/v1/investigations/{inv.id}/custody",
            headers=headers,
        )
        assert resp_custody.status_code == 200
        custody_list = resp_custody.json()
        assert len(custody_list) >= 1
        acq_event = [c for c in custody_list if c["event_type"] == "ACQUISITION"][-1]
        assert acq_event["sha256_hash"] == data1["sha256_hash"]
        print(f"✓ Custody event confirmed: EventType={acq_event['event_type']}, Actor={acq_event['actor_type']}")

        # ── Test 4: Idempotency (Duplicate Upload Prevention) ───────────────
        print("\n[Test 4] Testing Duplicate Document Upload (Expect 409 Conflict)...")
        resp_dup = await client.post(
            f"/api/v1/investigations/{inv.id}/documents",
            headers=headers,
            files={"file": ("duplicate_statement.pdf", pdf_bytes, "application/pdf")},
            data={"document_type": "BANK_STATEMENT"},
        )
        assert resp_dup.status_code == 409
        dup_msg = resp_dup.json().get("error", {}).get("message", resp_dup.text)
        print(f"✓ Duplicate rejected with 409 Conflict: {dup_msg[:60]}...")

        # ── Test 5: Password-Protected PDF Rejection ─────────────────────────
        print("\n[Test 5] Testing Encrypted PDF Detection (Expect 422 Unprocessable)...")
        enc_bytes = create_encrypted_pdf()
        resp_enc = await client.post(
            f"/api/v1/investigations/{inv.id}/documents",
            headers=headers,
            files={"file": ("encrypted_statement.pdf", enc_bytes, "application/pdf")},
            data={"document_type": "BANK_STATEMENT"},
        )
        assert resp_enc.status_code == 422
        enc_msg = resp_enc.json().get("error", {}).get("message", resp_enc.text)
        assert "PASSWORD_PROTECTED_PDF" in enc_msg
        print(f"✓ Encrypted PDF caught: {enc_msg[:70]}...")

        # ── Test 6: Extension Spoofing Rejection ─────────────────────────────
        print("\n[Test 6] Testing File Extension Spoofing (Expect 422 Unprocessable)...")
        fake_bytes = b"This is plain text pretending to be a PDF statement."
        resp_fake = await client.post(
            f"/api/v1/investigations/{inv.id}/documents",
            headers=headers,
            files={"file": ("fake_statement.pdf", fake_bytes, "application/pdf")},
            data={"document_type": "BANK_STATEMENT"},
        )
        assert resp_fake.status_code == 422
        fake_msg = resp_fake.json().get("error", {}).get("message", resp_fake.text)
        print(f"✓ Spoofed extension rejected: {fake_msg}")

        # ── Test 7: Upload Scanned Image (PNG) ───────────────────────────────
        print("\n[Test 7] Uploading Scanned Image Document (PNG)...")
        png_bytes = create_sample_png()
        resp_png = await client.post(
            f"/api/v1/investigations/{inv.id}/documents",
            headers=headers,
            files={"file": ("salary_slip_scan.png", png_bytes, "image/png")},
            data={"document_type": "SALARY_SLIP"},
        )
        assert resp_png.status_code == 201
        data_png = resp_png.json()
        assert data_png["page_count"] == 1
        print(f"✓ Image document uploaded: ID={data_png['id']}, Type={data_png['document_type']}, Pages={data_png['page_count']}")

        # ── Test 8: List Documents in Investigation ──────────────────────────
        print("\n[Test 8] Listing Documents in Investigation...")
        resp_list = await client.get(
            f"/api/v1/investigations/{inv.id}/documents",
            headers=headers,
        )
        assert resp_list.status_code == 200
        docs = resp_list.json()
        assert len(docs) >= 2
        print(f"✓ Listed {len(docs)} documents in investigation {inv.caseNumber}")

    await disconnect()
    print("\n======================================================")
    print("ALL 8 STEP 1 INGESTION TESTS PASSED FLAWLESSLY! ✓")
    print("======================================================")


if __name__ == "__main__":
    asyncio.run(run_tests())
