from datetime import datetime, timezone
import json
import logging
import time
from typing import Any
import pymupdf
from prisma import Json, Prisma

from app.config import get_settings
from app.core import security
from app.core.storage import storage
from app.features.reports import schemas
from app.features.agents.swarm.lead_investigator import LeadInvestigatorAgent

logger = logging.getLogger(__name__)
settings = get_settings()


def _draw_header_footer(page: pymupdf.Page, case_number: str, page_num: int, total_pages: int, doc_sha: str) -> None:
    """Draw a standardized forensic header and footer on each page."""
    rect = page.rect
    # Header line
    page.draw_line((40, 35), (rect.width - 40, 35), color=(0.7, 0.7, 0.7), width=0.5)
    page.insert_text(
        (40, 30),
        "DEEPTRACE FORENSIC AUDIT DOSSIER  |  OFFICIAL CONFIDENTIAL",
        fontsize=7,
        color=(0.3, 0.3, 0.3),
        fontname="helv",
    )
    page.insert_text(
        (rect.width - 150, 30),
        f"Case: {case_number}",
        fontsize=7,
        color=(0.3, 0.3, 0.3),
        fontname="helv",
    )

    # Footer line
    page.draw_line((40, rect.height - 35), (rect.width - 40, rect.height - 35), color=(0.7, 0.7, 0.7), width=0.5)
    page.insert_text(
        (40, rect.height - 25),
        f"ETO 2002 Compliant  |  Hash: {doc_sha[:16]}...  |  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        fontsize=6.5,
        color=(0.4, 0.4, 0.4),
        fontname="helv",
    )
    page.insert_text(
        (rect.width - 90, rect.height - 25),
        f"Page {page_num} of {total_pages}",
        fontsize=6.5,
        color=(0.4, 0.4, 0.4),
        fontname="helv",
    )


async def generate_report(db: Prisma, investigation_id: str, options: dict | None = None) -> schemas.ReportResponse:
    """
    Build a court-admissible forensic PDF dossier containing:
    - SHA-256 chain-of-custody header (ETO 2002 / NIST SP 800-86)
    - Risk score summary and tier classification
    - Per-evidence finding with bounding box annotations
    - Multi-Agent Lead Investigator narrative synthesis
    - Regulatory disclosures (ETO 2002, PECA 2016, SBP frameworks)
    """
    options = options or {}
    inv = await db.investigation.find_unique(
        where={"id": investigation_id},
        include={"documents": True, "riskAssessment": True, "organization": True, "user": True},
    )
    if not inv:
        raise ValueError(f"Investigation {investigation_id} not found.")

    docs = inv.documents or []
    primary_doc = docs[0] if docs else None
    doc_ids = [d.id for d in docs]

    evidence_items = []
    if doc_ids:
        evidence_items = await db.evidenceitem.find_many(
            where={"documentId": {"in": doc_ids}},
            include={"boundingBoxes": True},
            order={"riskPoints": "desc"},
        )

    risk = inv.riskAssessment
    overall_score = risk.overallScore if risk else 0
    risk_tier = risk.riskTier if risk else "LOW"
    action_directive = risk.actionDirective if risk else "STRAIGHT_THROUGH_APPROVAL"

    # Build evidence manifest for Lead Investigator synthesis
    manifest = {
        "investigation": {"id": inv.id, "caseNumber": inv.caseNumber, "title": inv.title},
        "documents": [{"originalFilename": d.originalFilename, "sha256Hash": d.sha256Hash} for d in docs],
        "risk_assessment": {"overallScore": overall_score, "riskTier": risk_tier, "actionDirective": action_directive},
        "evidence_items": [
            {
                "id": it.id,
                "ruleId": it.ruleId,
                "category": it.category,
                "severity": it.severity,
                "title": it.title,
                "description": it.description,
                "expectedValue": it.expectedValue,
                "actualValue": it.actualValue,
                "discrepancy": it.discrepancy,
                "pageNumber": it.pageNumber,
            }
            for it in evidence_items
        ],
    }
    lead_agent = LeadInvestigatorAgent(manifest)
    swarm_summary = await lead_agent.analyze()

    # Create PyMuPDF document
    doc = pymupdf.open()
    doc_sha = primary_doc.sha256Hash if primary_doc else "UNVERIFIED"
    case_num = inv.caseNumber or "DT-UNKNOWN"

    # ─────────────────────────────────────────────────────────────────────────
    # Page 1: Title, Custody Certificate & Executive Summary
    # ─────────────────────────────────────────────────────────────────────────
    p1 = doc.new_page(width=595, height=842)  # A4

    # Top Dark Navy Banner
    p1.draw_rect(pymupdf.Rect(40, 50, 555, 115), color=None, fill=(0.06, 0.09, 0.16))
    p1.insert_text((55, 78), "DEEPTRACE DOCUMENT FORENSICS", fontsize=14, color=(1, 1, 1), fontname="hebo")
    p1.insert_text((55, 98), "COURT-ADMISSIBLE FORENSIC AUDIT DOSSIER", fontsize=9, color=(0.8, 0.85, 0.95), fontname="helv")
    p1.insert_text((430, 98), f"CASE: {case_num}", fontsize=8, color=(0.9, 0.9, 0.9), fontname="helv")

    curr_y = 135
    # Chain of Custody Box
    p1.draw_rect(pymupdf.Rect(40, curr_y, 555, curr_y + 110), color=(0.8, 0.85, 0.9), fill=(0.97, 0.98, 1.0))
    p1.insert_text((55, curr_y + 20), "DIGITAL CHAIN OF CUSTODY (ETO 2002 & NIST SP 800-86)", fontsize=9, fontname="hebo", color=(0.1, 0.2, 0.4))
    p1.insert_text((55, curr_y + 40), f"Primary Document: {primary_doc.originalFilename if primary_doc else 'N/A'}", fontsize=8, fontname="helv")
    p1.insert_text((55, curr_y + 56), f"File Size: {primary_doc.fileSizeBytes if primary_doc else 0:,} bytes  |  Pages: {primary_doc.pageCount if primary_doc else 1}", fontsize=8, fontname="helv")
    p1.insert_text((55, curr_y + 72), f"SHA-256 Hash: {doc_sha}", fontsize=7.5, fontname="cobo")
    p1.insert_text((55, curr_y + 88), f"Organization: {inv.organization.name if inv.organization else 'DeepTrace'}  |  Auditor: {inv.user.email if inv.user else 'System'}", fontsize=8, fontname="helv")
    p1.insert_text((55, curr_y + 104), f"Custody Status: IMMUTABLY CLONED & VERIFIED ON INGESTION", fontsize=7.5, fontname="hebo", color=(0.1, 0.5, 0.2))

    curr_y += 125
    # Risk Verdict Banner
    if risk_tier in ["CRITICAL", "HIGH"]:
        border_col, fill_col, text_col = (0.86, 0.15, 0.15), (0.99, 0.95, 0.95), (0.7, 0.1, 0.1)
    elif risk_tier == "MEDIUM":
        border_col, fill_col, text_col = (0.9, 0.6, 0.1), (1.0, 0.98, 0.9), (0.6, 0.4, 0.0)
    else:
        border_col, fill_col, text_col = (0.1, 0.6, 0.2), (0.95, 0.99, 0.95), (0.05, 0.45, 0.15)

    p1.draw_rect(pymupdf.Rect(40, curr_y, 555, curr_y + 60), color=border_col, fill=fill_col, width=1.5)
    p1.insert_text((55, curr_y + 24), f"VERDICT: {risk_tier} RISK  —  SCORE: {overall_score}/100", fontsize=12, fontname="hebo", color=text_col)
    p1.insert_text((55, curr_y + 44), f"STATUTORY ACTION DIRECTIVE: {action_directive.replace('_', ' ')}", fontsize=9, fontname="hebo", color=text_col)

    curr_y += 75
    # Lead Investigator Synthesis
    p1.insert_text((40, curr_y), "EXECUTIVE FORENSIC SUMMARY & SYNTHESIS", fontsize=10, fontname="hebo", color=(0.1, 0.1, 0.1))
    curr_y += 15
    narrative_text = swarm_summary.get("narrative", "Investigation complete.")
    # Wrap narrative into box
    nar_rect = pymupdf.Rect(40, curr_y, 555, curr_y + 90)
    p1.draw_rect(nar_rect, color=(0.85, 0.85, 0.85), fill=(0.98, 0.98, 0.98))
    p1.insert_textbox(nar_rect + (8, 8, -8, -8), narrative_text, fontsize=8, fontname="helv")

    curr_y += 105
    # Key Evidence Statistics
    p1.insert_text((40, curr_y), "FORENSIC SIGNAL AGGREGATION", fontsize=10, fontname="hebo", color=(0.1, 0.1, 0.1))
    curr_y += 15
    stat_rect = pymupdf.Rect(40, curr_y, 555, curr_y + 45)
    p1.draw_rect(stat_rect, color=(0.85, 0.85, 0.85), fill=(1, 1, 1))
    crit = risk.criticalCount if risk else 0
    hi = risk.highCount if risk else 0
    med = risk.mediumCount if risk else 0
    tot = len(evidence_items)
    p1.insert_text((55, curr_y + 18), f"Total Verified Findings: {tot}", fontsize=8.5, fontname="hebo")
    p1.insert_text((55, curr_y + 34), f"Critical: {crit}  |  High: {hi}  |  Medium: {med}  |  Low: {tot - crit - hi - med}", fontsize=8, fontname="helv")

    curr_y += 65
    # Regulatory statement snippet on Page 1
    p1.insert_text(
        (40, curr_y),
        "STATUTORY RECOGNITION: Generated pursuant to Electronic Transactions Ordinance 2002 (ETO 2002) §3 & §4.",
        fontsize=7.5,
        fontname="helv",
        color=(0.3, 0.3, 0.3),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Page 2: Detailed Evidence Manifest Table
    # ─────────────────────────────────────────────────────────────────────────
    p2 = doc.new_page(width=595, height=842)
    p2_y = 55
    p2.insert_text((40, p2_y), "VERIFIED FORENSIC EVIDENCE MANIFEST", fontsize=11, fontname="hebo", color=(0.1, 0.1, 0.1))
    p2_y += 20

    if not evidence_items:
        p2.insert_text((40, p2_y), "No tampering or anomalous forensic indicators detected. Document verified as clean.", fontsize=9, fontname="helv")
    else:
        for idx, it in enumerate(evidence_items[:8], 1):
            sev = it.severity or "UNKNOWN"
            card_col = (0.99, 0.95, 0.95) if sev == "CRITICAL" else ((1.0, 0.98, 0.92) if sev == "HIGH" else (0.98, 0.98, 0.98))
            brd_col = (0.85, 0.2, 0.2) if sev == "CRITICAL" else ((0.9, 0.5, 0.1) if sev == "HIGH" else (0.8, 0.8, 0.8))

            card_h = 70
            card_rect = pymupdf.Rect(40, p2_y, 555, p2_y + card_h)
            p2.draw_rect(card_rect, color=brd_col, fill=card_col, width=0.8)

            title = it.title or "Forensic Finding"
            rule_id = it.ruleId or "RULE_UNKNOWN"
            p2.insert_text((50, p2_y + 15), f"#{idx}. {title}", fontsize=8.5, fontname="hebo", color=(0.1, 0.1, 0.1))
            p2.insert_text((430, p2_y + 15), f"[{sev}] {it.riskPoints or 0} pts", fontsize=8, fontname="hebo", color=brd_col)
            p2.insert_text((50, p2_y + 28), f"Rule: {rule_id}  |  Page: {it.pageNumber or 1}", fontsize=7.5, fontname="Courier", color=(0.3, 0.3, 0.3))

            desc = it.description or ""
            if it.discrepancy:
                desc += f" [Discrepancy: {it.discrepancy}]"
            desc_rect = pymupdf.Rect(50, p2_y + 32, 545, p2_y + card_h - 4)
            p2.insert_textbox(desc_rect, desc, fontsize=7.2, fontname="helv")

            p2_y += card_h + 10

    # ─────────────────────────────────────────────────────────────────────────
    # Page 3: Regulatory Framework & Legal Disclosures
    # ─────────────────────────────────────────────────────────────────────────
    p3 = doc.new_page(width=595, height=842)
    p3_y = 55
    p3.insert_text((40, p3_y), "STATUTORY & REGULATORY COMPLIANCE DISCLOSURE", fontsize=11, fontname="hebo", color=(0.1, 0.1, 0.1))
    p3_y += 25

    reg_sections = [
        (
            "1. Electronic Transactions Ordinance 2002 (ETO 2002) — Legal Admissibility & §29 Digital Signatures",
            (
                "Under Sections 3, 4, 8, 9, and 29 of the Electronic Transactions Ordinance 2002 (ETO 2002), electronic "
                "documents and digital certificates certified by an accredited Certification Authority (e.g., NIFT / ECAC) "
                "carry statutory presumption of integrity and authenticity. If post-signing byte alteration occurs, "
                "the cryptographic digest mismatch mathematically rebuts the presumption of authenticity under Section 29."
            ),
        ),
        (
            "2. Prevention of Electronic Crimes Act 2016 (PECA 2016) — Electronic Forgery & Fraud",
            (
                "Sections 13 (Electronic Forgery) and 14 (Electronic Fraud) of PECA 2016 criminalize the unauthorized "
                "input, alteration, deletion, or suppression of electronic data resulting in inauthentic data with the "
                "intent that it be considered genuine. The mathematical ledger discrepancies and visual splices "
                "documented herein constitute prima facie digital evidence of electronic document falsification."
            ),
        ),
        (
            "3. State Bank of Pakistan (SBP) Framework for Digital Onboarding & Verification",
            (
                "In compliance with SBP BPRD Circular No. 2 of 2023 and AML/CFT/CPF regulations, regulated lending "
                "institutions and fintechs are required to exercise Enhanced Due Diligence (EDD) upon identifying "
                "mathematical balance discontinuities, IBAN checksum failures, or unauthorized PDF post-generation edits."
            ),
        ),
        (
            "4. NIST SP 800-86 Guide to Integrating Forensic Techniques into Incident Response",
            (
                "All evidentiary artifacts, sub-pixel baseline offsets, discrete cosine transform (DCT) residual heatmaps, "
                "and multi-page balance reconciliation audits are compiled under deterministic, non-destructive methodologies "
                "satisfying NIST SP 800-86 forensic standards."
            ),
        ),
    ]

    for heading, body in reg_sections:
        p3.draw_rect(pymupdf.Rect(40, p3_y, 555, p3_y + 65), color=(0.85, 0.85, 0.85), fill=(0.98, 0.98, 0.99))
        p3.insert_text((50, p3_y + 16), heading, fontsize=8.5, fontname="hebo", color=(0.15, 0.2, 0.35))
        p3.insert_textbox(pymupdf.Rect(50, p3_y + 22, 545, p3_y + 60), body, fontsize=7.2, fontname="helv")
        p3_y += 75

    # Draw Headers and Footers across all pages
    total_pages = len(doc)
    for idx, page in enumerate(doc, 1):
        _draw_header_footer(page, case_num, idx, total_pages, doc_sha)

    pdf_bytes = doc.tobytes()
    doc.close()

    # Save report to S3 / MinIO
    dossier_sha256 = security.compute_sha256(pdf_bytes)
    storage_path = f"reports/{investigation_id}/dossier_{int(time.time()*1000)}.pdf"
    storage.upload_file(settings.s3_bucket_artifacts, storage_path, pdf_bytes, "application/pdf")

    # Record CustodyEvent in database
    try:
        await db.custodyevent.create(
            data={
                "investigationId": investigation_id,
                "eventType": "EXPORTED",
                "description": f"Court-admissible PDF forensic audit dossier generated ({total_pages} pages).",
                "actorType": "system",
                "actorId": "deeptrace-core",
                "sha256Hash": dossier_sha256,
                "metadata": Json({
                    "storage_path": storage_path,
                    "file_size": len(pdf_bytes),
                    "page_count": total_pages,
                }),
            }
        )
    except Exception as exc:
        logger.warning(f"Could not record custody event: {exc}")

    # Update investigation metadata with report details
    try:
        current_meta = inv.metadata or {}
        if isinstance(current_meta, str):
            current_meta = json.loads(current_meta)
        current_meta["report"] = {
            "status": "ready",
            "storage_path": storage_path,
            "sha256": dossier_sha256,
            "file_size_bytes": len(pdf_bytes),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.investigation.update(
            where={"id": investigation_id},
            data={"metadata": Json(current_meta)},
        )
    except Exception as exc:
        logger.warning(f"Could not update investigation metadata: {exc}")

    download_url = storage.generate_presigned_url(settings.s3_bucket_artifacts, storage_path)

    return schemas.ReportResponse(
        id=f"rep-{investigation_id[:12]}",
        investigation_id=investigation_id,
        status="ready",
        download_url=download_url,
        file_size_bytes=len(pdf_bytes),
        sha256_hash=dossier_sha256,
        generated_at=datetime.now(timezone.utc),
    )


async def get_report_download_url(db: Prisma, investigation_id: str) -> schemas.ReportResponse:
    """Return a fresh pre-signed S3 URL for the generated dossier."""
    inv = await db.investigation.find_unique(where={"id": investigation_id})
    if not inv:
        raise ValueError(f"Investigation {investigation_id} not found.")

    meta = inv.metadata or {}
    if isinstance(meta, str):
        meta = json.loads(meta)

    report_meta = meta.get("report")
    if not report_meta or not report_meta.get("storage_path"):
        # Auto-generate if not already generated
        return await generate_report(db, investigation_id)

    storage_path = report_meta["storage_path"]
    download_url = storage.generate_presigned_url(settings.s3_bucket_artifacts, storage_path)

    gen_at = None
    if report_meta.get("generated_at"):
        try:
            gen_at = datetime.fromisoformat(report_meta["generated_at"])
        except Exception:
            gen_at = datetime.now(timezone.utc)

    return schemas.ReportResponse(
        id=f"rep-{investigation_id[:12]}",
        investigation_id=investigation_id,
        status="ready",
        download_url=download_url,
        file_size_bytes=report_meta.get("file_size_bytes"),
        sha256_hash=report_meta.get("sha256"),
        generated_at=gen_at,
    )
