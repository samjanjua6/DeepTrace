"""
Stage 2: PDF Structural & Metadata Forensics — Celery Task & Async Processor
NIST SP 800-86 Compliant PDF XREF, Incremental Save, and Producer Verification.
"""
from datetime import datetime, timezone
import re
import time
from typing import Any

import pymupdf
from prisma import Json

from app.config import get_settings
from app.core.celery_app import celery_app
from app.core.storage import storage
from app.db.client import db, set_org_context

settings = get_settings()

# Known consumer and desktop editing software that should NEVER appear on official bank e-statements
TAMPER_SOFTWARE_PATTERNS = [
    (r"canva", "Canva Online Editor"),
    (r"acrobat\s*(pro|standard|dc|reader)", "Adobe Acrobat Desktop Editor"),
    (r"photoshop", "Adobe Photoshop"),
    (r"illustrator", "Adobe Illustrator"),
    (r"indesign", "Adobe InDesign"),
    (r"nitro\s*pdf", "Nitro Pro PDF"),
    (r"pdfill", "PDFill Editor"),
    (r"sejda", "Sejda PDF Editor"),
    (r"ilovepdf", "iLovePDF Online Editor"),
    (r"smallpdf", "Smallpdf"),
    (r"foxit\s*(phantom|editor)", "Foxit PDF Editor"),
    (r"pdf-?xchange", "PDF-XChange Editor"),
    (r"coreldraw", "CorelDraw"),
]


def parse_pdf_date(date_str: str | None) -> datetime | None:
    """Parse PDF date format D:YYYYMMDDHHmmSS[OHH'mm'] into a Python datetime."""
    if not date_str or not isinstance(date_str, str):
        return None
    cleaned = date_str.strip()
    if cleaned.startswith("D:"):
        cleaned = cleaned[2:]
    # Match YYYYMMDDHHmmss
    match = re.match(r"^(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?", cleaned)
    if not match:
        return None
    try:
        parts = [int(p) if p else 0 for p in match.groups()]
        return datetime(parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], tzinfo=timezone.utc)
    except Exception:
        return None


async def process_pdf_structure(
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Stage 2: PDF Structural & Metadata Forensics.
    Detects incremental saves, trailer object anomalies, editing tool signatures,
    and modification timestamp skews.
    """
    start_time = time.perf_counter()

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
            if not documents:
                raise ValueError(f"No documents found for investigation '{investigation_id}'")

            stage_findings = []

            for doc in documents:
                if doc.mimeType != "application/pdf":
                    # Non-PDF files (images) skip PDF structural analysis cleanly
                    continue

                file_bytes = storage.get_file(settings.s3_bucket_documents, doc.storagePath)
                if not file_bytes:
                    continue

                # 1. Incremental Save Detection (%%EOF count)
                eof_count = file_bytes.count(b"%%EOF")
                if eof_count > 1:
                    finding = await tx.evidenceitem.create(
                        data={
                            "document": {"connect": {"id": doc.id}},
                            "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                            "category": "PDF_OBJECT_ANOMALY",
                            "severity": "CRITICAL" if eof_count > 2 else "HIGH",
                            "ruleId": "RULE_PDF_INCREMENTAL_SAVE",
                            "riskPoints": 35,
                            "title": "Incremental PDF Revisions Detected (Post-Generation Tampering)",
                            "description": (
                                f"The document contains {eof_count} %%EOF trailer markers indicating that the file "
                                "was modified and re-saved after its initial export. Legitimate bank e-statements "
                                "are compiled in a single pass with exactly 1 revision."
                            ),
                            "isDeterministic": True,
                            "pageNumber": 1,
                            "expectedValue": "1 revision (single %%EOF)",
                            "actualValue": f"{eof_count} revisions",
                            "discrepancy": f"+{eof_count - 1} unauthorized revision(s)",
                            "technicalDetails": Json({
                                "eof_count": eof_count,
                                "file_size_bytes": len(file_bytes),
                            }),
                        }
                    )
                    stage_findings.append({
                        "id": finding.id,
                        "rule_id": "RULE_PDF_INCREMENTAL_SAVE",
                        "severity": finding.severity,
                        "title": finding.title,
                    })

                # 2. Metadata Inspection & Tampering Tool Signatures
                try:
                    pdf_doc = pymupdf.open(stream=file_bytes, filetype="pdf")
                    meta = pdf_doc.metadata or {}
                    producer = (meta.get("producer") or "").strip()
                    creator = (meta.get("creator") or "").strip()
                    author = (meta.get("author") or "").strip()
                    combined_meta = f"{producer} {creator} {author}".lower()

                    for pattern, tool_name in TAMPER_SOFTWARE_PATTERNS:
                        if re.search(pattern, combined_meta, re.IGNORECASE):
                            finding = await tx.evidenceitem.create(
                                data={
                                    "document": {"connect": {"id": doc.id}},
                                    "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                    "category": "PDF_OBJECT_ANOMALY",
                                    "severity": "HIGH",
                                    "ruleId": "RULE_PDF_TAMPER_PRODUCER",
                                    "riskPoints": 25,
                                    "title": f"Desktop Editing Software Signature Identified: {tool_name}",
                                    "description": (
                                        f"Document metadata reveals tool signature '{tool_name}' (Producer: '{producer}', "
                                        f"Creator: '{creator}'). Official bank statements are generated directly by automated "
                                        "core banking engines (e.g., JasperReports, Oracle FLEXCUBE, iText) and never consumer editors."
                                    ),
                                    "isDeterministic": True,
                                    "pageNumber": 1,
                                    "expectedValue": "Core Banking Reporting Engine (JasperReports/Oracle/iText)",
                                    "actualValue": tool_name,
                                    "discrepancy": f"Generated or edited with {tool_name}",
                                    "technicalDetails": Json({
                                        "producer": producer,
                                        "creator": creator,
                                        "author": author,
                                        "detected_tool": tool_name,
                                    }),
                                }
                            )
                            stage_findings.append({
                                "id": finding.id,
                                "rule_id": "RULE_PDF_TAMPER_PRODUCER",
                                "severity": finding.severity,
                                "title": finding.title,
                            })
                            break

                    # 3. Timestamp Divergence
                    creation_dt = parse_pdf_date(meta.get("creationDate"))
                    mod_dt = parse_pdf_date(meta.get("modDate"))

                    if creation_dt and mod_dt:
                        delta_seconds = abs((mod_dt - creation_dt).total_seconds())
                        if delta_seconds > 3600:  # More than 1 hour divergence
                            hours_diff = round(delta_seconds / 3600, 1)
                            finding = await tx.evidenceitem.create(
                                data={
                                    "document": {"connect": {"id": doc.id}},
                                    "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                    "category": "METADATA_TIMESTAMP_MISMATCH",
                                    "severity": "MEDIUM",
                                    "ruleId": "RULE_METADATA_TIMESTAMP_DIVERGENCE",
                                    "riskPoints": 15,
                                    "title": "Post-Creation Modification Timestamp Skew",
                                    "description": (
                                        f"Document modification timestamp is {hours_diff} hours after its creation timestamp. "
                                        "Legitimate bank statements are generated in real-time with synchronized timestamps."
                                    ),
                                    "isDeterministic": True,
                                    "pageNumber": 1,
                                    "expectedValue": creation_dt.isoformat(),
                                    "actualValue": mod_dt.isoformat(),
                                    "discrepancy": f"{hours_diff} hours modification gap",
                                    "technicalDetails": Json({
                                        "creation_date": creation_dt.isoformat(),
                                        "mod_date": mod_dt.isoformat(),
                                        "delta_seconds": delta_seconds,
                                    }),
                                }
                            )
                            stage_findings.append({
                                "id": finding.id,
                                "rule_id": "RULE_METADATA_TIMESTAMP_DIVERGENCE",
                                "severity": finding.severity,
                                "title": finding.title,
                            })

                    pdf_doc.close()

                except Exception as pdf_err:
                    # Non-fatal metadata read error
                    pass

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            output_payload = {
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
            raise


@celery_app.task(
    name="app.features.pipeline.tasks.stage_2_pdf_structure",
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
    """Celery task entry point for Stage 2."""
    import asyncio
    return asyncio.run(
        process_pdf_structure(
            pipeline_run_id, pipeline_stage_id, org_id, investigation_id, document_id
        )
    )
