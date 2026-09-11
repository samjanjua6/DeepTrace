import io
import logging
import re
from datetime import datetime, timezone
import time
from typing import Any

import numpy as np
from PIL import Image
import pymupdf
from prisma import Json

from app.config import get_settings
from app.core.celery_app import celery_app
from app.core.storage import storage
from app.db.client import db, set_org_context
from app.features.pipeline.tasks.credential_verifier import extract_credential_urls, verify_coursera_credential

logger = logging.getLogger(__name__)
settings = get_settings()


async def audit_credential_urls(
    tx: Any,
    doc_id: str,
    pipeline_stage_id: str,
    page_num: int,
    page_text: str,
    standard_words: list,
    stage_findings: list,
) -> None:
    """
    Audit extracted text for online credential & certificate verification URLs.
    Validates against official issuer registries (Coursera, Udemy, edX).
    Flags non-existent credential IDs or recipient identity mismatches.
    """
    if not page_text:
        return

    cred_urls = extract_credential_urls(page_text)
    for cred in cred_urls:
        provider = cred["provider"]
        code = cred["code"]
        matched_text = cred["matched_text"]
        verification_url = cred["url"]

        if provider == "Coursera":
            is_valid, reason, details = verify_coursera_credential(code)

            # Locate bounding box for the credential URL from word coordinates
            bbox = None
            if standard_words:
                target_words = []
                for w in standard_words:
                    word_str = str(w[4] if len(w) > 4 else w.get("text", "") if isinstance(w, dict) else "").lower()
                    if any(term in word_str for term in (code.lower(), "coursera", "verify")):
                        target_words.append(w)
                if target_words:
                    try:
                        x0 = min(w[0] if not isinstance(w, dict) else w["bbox"][0] for w in target_words)
                        y0 = min(w[1] if not isinstance(w, dict) else w["bbox"][1] for w in target_words)
                        x1 = max(w[2] if not isinstance(w, dict) else w["bbox"][2] for w in target_words)
                        y1 = max(w[3] if not isinstance(w, dict) else w["bbox"][3] for w in target_words)
                        bbox = {"x": float(x0), "y": float(y0), "width": float(max(10, x1 - x0)), "height": float(max(10, y1 - y0))}
                    except Exception:
                        bbox = None

            if not is_valid:
                finding = await tx.evidenceitem.create(
                    data={
                        "document": {"connect": {"id": doc_id}},
                        "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                        "category": "OCR_CONFIDENCE_ANOMALY",
                        "severity": "CRITICAL",
                        "ruleId": "RULE_CREDENTIAL_REGISTRY_NOT_FOUND",
                        "riskPoints": 50,
                        "title": f"Academic Credential Registry Verification Failed ({provider} ID Not Found)",
                        "description": (
                            f"The document references an online verification link ({verification_url}) with certificate "
                            f"identifier '{code}'. Real-time registry verification against {provider} returned: {reason}. "
                            "Official certificates can always be validated on the issuer's public registry; a null record "
                            "indicates the credential was forged or fabricated."
                        ),
                        "isDeterministic": True,
                        "pageNumber": page_num,
                        "expectedValue": f"Active credential record registered on {provider}",
                        "actualValue": f"Registry failure: {reason}",
                        "discrepancy": f"Credential code '{code}' does not exist on issuer platform",
                        "technicalDetails": Json({
                            "provider": provider,
                            "code": code,
                            "verification_url": verification_url,
                            "error_reason": reason,
                            "matched_text": matched_text,
                        }),
                    }
                )
                if bbox:
                    await tx.boundingbox.create(
                        data={
                            "evidenceItem": {"connect": {"id": finding.id}},
                            "pageNumber": page_num,
                            "x": bbox["x"],
                            "y": bbox["y"],
                            "width": bbox["width"],
                            "height": bbox["height"],
                            "label": f"Invalid {provider} ID: {code}",
                            "color": "#BA2518",
                        }
                    )
                stage_findings.append({
                    "id": finding.id,
                    "rule_id": "RULE_CREDENTIAL_REGISTRY_NOT_FOUND",
                    "severity": finding.severity,
                    "title": finding.title,
                })
            else:
                # Credential code exists, check if recipient name matches
                if details and details.get("recipient_name"):
                    reg_name = details["recipient_name"].strip()
                    reg_norm = " ".join(reg_name.lower().split())
                    doc_norm = " ".join(page_text.lower().split())
                    reg_clean = re.sub(r"[^a-z0-9]", "", reg_norm)
                    doc_clean = re.sub(r"[^a-z0-9]", "", doc_norm)

                    if reg_clean and reg_clean not in doc_clean:
                        finding = await tx.evidenceitem.create(
                            data={
                                "document": {"connect": {"id": doc_id}},
                                "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                "category": "OCR_CONFIDENCE_ANOMALY",
                                "severity": "CRITICAL",
                                "ruleId": "RULE_CREDENTIAL_RECIPIENT_MISMATCH",
                                "riskPoints": 50,
                                "title": f"Certificate Registry Recipient Identity Mismatch",
                                "description": (
                                    f"Credential identifier '{code}' is registered on {provider}, but the official registry records "
                                    f"the recipient as '{reg_name}', whereas this name is not present on the submitted certificate. "
                                    "This indicates credential hijacking where a genuine verification link was pasted onto an altered document."
                                ),
                                "isDeterministic": True,
                                "pageNumber": page_num,
                                "expectedValue": f"Certificate issued to '{reg_name}'",
                                "actualValue": f"Issuer records recipient as '{reg_name}'",
                                "discrepancy": f"Recipient on certificate does not match registered owner '{reg_name}'",
                                "technicalDetails": Json({
                                    "provider": provider,
                                    "code": code,
                                    "registered_recipient": reg_name,
                                    "course_name": details.get("course_name"),
                                    "verification_url": verification_url,
                                }),
                            }
                        )
                        if bbox:
                            await tx.boundingbox.create(
                                data={
                                    "evidenceItem": {"connect": {"id": finding.id}},
                                    "pageNumber": page_num,
                                    "x": bbox["x"],
                                    "y": bbox["y"],
                                    "width": bbox["width"],
                                    "height": bbox["height"],
                                    "label": f"Recipient Mismatch (Issuer: {reg_name})",
                                    "color": "#BA2518",
                                }
                            )
                        stage_findings.append({
                            "id": finding.id,
                            "rule_id": "RULE_CREDENTIAL_RECIPIENT_MISMATCH",
                            "severity": finding.severity,
                            "title": finding.title,
                        })


async def process_ocr(
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Stage 5: Hybrid Text & Deep-Learning OCR Extraction.
    - Path A: Extracts native digital text streams for born-digital PDFs.
    - Path B: Triggers the configured OCR backend (PaddleOCR + PP-Structure by default,
              controlled by OCR_BACKEND env var) on rendered 150 DPI rasters for scanned
              paper, photocopies, and smartphone photos.
    - Persists full text, structured word coordinates, AND structured table cell data
      (DocumentPage.extractedTables) for downstream Stage 6 column-accurate parsing.
    """
    start_time = time.perf_counter()

    # Import the pluggable backend factory (lazy — avoids loading paddle at module level)
    from app.features.pipeline.tasks.ocr_backends import get_ocr_backend

    async with set_org_context(org_id) as tx:
        await tx.pipelinestage.update(
            where={"id": pipeline_stage_id},
            data={"status": "RUNNING", "startedAt": datetime.now(timezone.utc)},
        )

        try:
            where_doc: dict[str, Any] = {"investigationId": investigation_id}
            if document_id:
                where_doc["id"] = document_id

            documents = await tx.document.find_many(where=where_doc)
            extracted_pages = []
            stage_findings = []

            for doc in documents:
                file_bytes = storage.get_file(settings.s3_bucket_documents, doc.storagePath)
                if not file_bytes:
                    continue

                if doc.mimeType == "application/pdf":
                    pdf_doc = pymupdf.open(stream=file_bytes, filetype="pdf")
                    for page_idx in range(len(pdf_doc)):
                        page = pdf_doc[page_idx]
                        page_num = page_idx + 1

                        native_text = page.get_text("text") or ""
                        native_words = page.get_text("words") or []
                        is_scanned = len(native_text.strip()) < 30 or len(native_words) == 0

                        extracted_tables_json: dict | None = None
                        table_count = 0

                        if not is_scanned:
                            # ── Path A: Born-Digital Vector Text Stream ──────────────
                            # PyMuPDF gives exact glyph coordinates — no neural OCR needed.
                            page_text = native_text
                            ocr_confidence = 1.0
                            ocr_method = "NATIVE_DIGITAL"
                            standard_words = [list(w) for w in native_words]
                            # No table structure extraction for vector PDFs here;
                            # Stage 6 uses native word coords with cluster_words_into_lines.
                        else:
                            # ── Path B: Scanned / Raster Page — Neural OCR Backend ───
                            pix = page.get_pixmap(dpi=150)
                            img_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                                (pix.height, pix.width, pix.n)
                            )
                            if pix.n == 4:
                                img_arr = img_arr[:, :, :3]

                            # Scale pixel → PDF-point (for word bbox projection)
                            scale_x = (page.rect.width / pix.width) if pix.width else (72.0 / 150.0)
                            scale_y = (page.rect.height / pix.height) if pix.height else (72.0 / 150.0)

                            backend = get_ocr_backend()
                            ocr_result = backend.extract(img_arr, scale_x=scale_x, scale_y=scale_y)

                            page_text = ocr_result.page_text
                            ocr_confidence = ocr_result.confidence
                            ocr_method = ocr_result.method
                            standard_words = ocr_result.words

                            if not page_text:
                                ocr_method = "SCAN_NO_TEXT_DETECTED"

                            # Serialise structured table cells for Stage 6
                            table_count = len(ocr_result.tables)
                            if ocr_result.tables:
                                extracted_tables_json = {
                                    "tables": [
                                        {
                                            "bbox": list(tbl.bbox),
                                            "rows": tbl.rows,
                                            "cols": tbl.cols,
                                            "cells": [
                                                {
                                                    "row": c.row,
                                                    "col": c.col,
                                                    "text": c.text,
                                                    "bbox": list(c.bbox),
                                                    "is_header": c.is_header,
                                                }
                                                for c in tbl.cells
                                            ],
                                        }
                                        for tbl in ocr_result.tables
                                    ]
                                }

                        # ── Persist structured OCR results to DocumentPage ──────────
                        update_data: dict[str, Any] = {
                            "ocrText": page_text,
                            "ocrConfidence": ocr_confidence,
                            "ocrDataJson": Json({
                                "method": ocr_method,
                                "words": standard_words,
                                "char_count": len(page_text),
                            }),
                        }
                        if extracted_tables_json is not None:
                            update_data["extractedTables"] = Json(extracted_tables_json)

                        await tx.documentpage.update_many(
                            where={"documentId": doc.id, "pageNumber": page_num},
                            data=update_data,
                        )

                        # Audit extracted text for credential registries (Coursera, Udemy, etc.)
                        await audit_credential_urls(
                            tx, doc.id, pipeline_stage_id, page_num, page_text, standard_words, stage_findings
                        )

                        extracted_pages.append({
                            "document_id": doc.id,
                            "page_number": page_num,
                            "extraction_method": ocr_method,
                            "ocr_confidence": ocr_confidence,
                            "character_count": len(page_text),
                            "word_count": len(standard_words),
                            "table_count": table_count,
                            "preview": page_text[:200],
                        })
                    pdf_doc.close()

                elif doc.mimeType.startswith("image/"):
                    # ── Standalone Image Document (smartphone photo, scanned certificate) ──
                    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
                    img_arr = np.array(img)

                    backend = get_ocr_backend()
                    # No scale factor for standalone images — coordinates are already in pixels
                    ocr_result = backend.extract(img_arr, scale_x=1.0, scale_y=1.0)

                    page_text = ocr_result.page_text
                    ocr_confidence = ocr_result.confidence
                    standard_words = ocr_result.words
                    ocr_method = ocr_result.method if ocr_result.page_text else "SCAN_NO_TEXT_DETECTED"

                    image_update_data: dict[str, Any] = {
                        "ocrText": page_text,
                        "ocrConfidence": ocr_confidence,
                        "ocrDataJson": Json({
                            "method": ocr_method,
                            "words": standard_words,
                            "char_count": len(page_text),
                        }),
                    }
                    if ocr_result.tables:
                        image_update_data["extractedTables"] = Json({
                            "tables": [
                                {
                                    "bbox": list(tbl.bbox),
                                    "rows": tbl.rows,
                                    "cols": tbl.cols,
                                    "cells": [
                                        {
                                            "row": c.row,
                                            "col": c.col,
                                            "text": c.text,
                                            "bbox": list(c.bbox),
                                            "is_header": c.is_header,
                                        }
                                        for c in tbl.cells
                                    ],
                                }
                                for tbl in ocr_result.tables
                            ]
                        })

                    await tx.documentpage.update_many(
                        where={"documentId": doc.id, "pageNumber": 1},
                        data=image_update_data,
                    )

                    # Audit extracted text for credential registries (Coursera, Udemy, etc.)
                    await audit_credential_urls(
                        tx, doc.id, pipeline_stage_id, 1, page_text, standard_words, stage_findings
                    )

                    extracted_pages.append({
                        "document_id": doc.id,
                        "page_number": 1,
                        "extraction_method": ocr_method,
                        "ocr_confidence": ocr_confidence,
                        "character_count": len(page_text),
                        "word_count": len(standard_words),
                        "table_count": len(ocr_result.tables),
                        "preview": page_text[:200],
                    })

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            output_payload = {
                "total_pages_extracted": len(extracted_pages),
                "pages": extracted_pages,
                "findings_count": len(stage_findings),
                "findings": stage_findings,
                "duration_ms": duration_ms,
            }

            await tx.pipelinestage.update(
                where={"id": pipeline_stage_id},
                data={
                    "status": "COMPLETED",
                    "durationMs": duration_ms,
                    "completedAt": datetime.now(timezone.utc),
                    "outputPayload": Json(output_payload),
                },
            )
            return output_payload

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            try:
                await tx.pipelinestage.update(
                    where={"id": pipeline_stage_id},
                    data={
                        "status": "FAILED",
                        "durationMs": duration_ms,
                        "completedAt": datetime.now(timezone.utc),
                        "errorMessage": str(exc),
                        "errorStack": exc.__class__.__name__,
                    },
                )
            except Exception:
                pass
            raise


@celery_app.task(
    name="app.features.pipeline.tasks.stage_5_ocr",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run(
    self,
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict:
    """Celery task entry point for Stage 5."""
    import asyncio
    return asyncio.run(
        process_ocr(
            pipeline_run_id, pipeline_stage_id, org_id, investigation_id, document_id
        )
    )
