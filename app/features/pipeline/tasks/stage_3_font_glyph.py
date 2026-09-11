"""
Stage 3: Sub-Pixel Typography & Baseline Geometry Forensics — Celery Task & Async Processor
NIST SP 800-86 Compliant Font Baseline Offset and Glyph Geometry Analysis.
"""
from datetime import datetime, timezone
import statistics
import time
from typing import Any

import pymupdf
from prisma import Json

from app.config import get_settings
from app.core.celery_app import celery_app
from app.core.storage import storage
from app.db.client import db, set_org_context

settings = get_settings()


async def process_font_glyph(
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Stage 3: Sub-Pixel Typography & Baseline Geometry Forensics.
    Extracts text spans from PDF pages, measures baseline vertical alignment (y-offset),
    detects spliced numbers and un-embedded font subset discrepancies.
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

            documents = await tx.document.find_many(
                where=where_doc,
                include={"pages": True},
            )
            if not documents:
                raise ValueError(f"No documents found for investigation '{investigation_id}'")

            stage_findings = []

            for doc in documents:
                if doc.mimeType != "application/pdf":
                    continue

                file_bytes = storage.get_file(settings.s3_bucket_documents, doc.storagePath)
                if not file_bytes:
                    continue

                pdf_doc = pymupdf.open(stream=file_bytes, filetype="pdf")

                # Map page number to DocumentPage record for scaling
                page_meta_map = {p.pageNumber: p for p in (doc.pages or [])}

                for page_idx in range(len(pdf_doc)):
                    page_num = page_idx + 1
                    page = pdf_doc[page_idx]
                    page_meta = page_meta_map.get(page_num)

                    # Compute scale factor from PDF points (72 DPI) to rendered pixel canvas
                    scale_x = (page_meta.widthPx / page_meta.widthPts) if (page_meta and page_meta.widthPts) else (150.0 / 72.0)
                    scale_y = (page_meta.heightPx / page_meta.heightPts) if (page_meta and page_meta.heightPts) else (150.0 / 72.0)

                    # Extract structured dictionary of blocks, lines, and spans
                    text_dict = page.get_text("dict", flags=pymupdf.TEXTFLAGS_SEARCH)
                    blocks = text_dict.get("blocks", [])

                    all_spans = []
                    for b in blocks:
                        if b.get("type") != 0:  # 0 is text, 1 is image
                            continue
                        for line in b.get("lines", []):
                            for s in line.get("spans", []):
                                if s.get("text", "").strip():
                                    all_spans.append(s)

                    # Cluster spans into logical horizontal rows by baseline proximity (threshold <= 4.0 pt)
                    sorted_spans = sorted(all_spans, key=lambda s: s.get("origin", (0, 0))[1])
                    rows: list[list[dict[str, Any]]] = []
                    for s in sorted_spans:
                        origin_y = s.get("origin", (0, 0))[1]
                        matched_row = None
                        for r in rows:
                            avg_y = sum(x.get("origin", (0, 0))[1] for x in r) / len(r)
                            if abs(origin_y - avg_y) <= 4.0:
                                matched_row = r
                                break
                        if matched_row is not None:
                            matched_row.append(s)
                        else:
                            rows.append([s])

                    for r in rows:
                        if len(r) < 2:
                            continue

                        # Collect baseline y-coordinates of spans in this row
                        origins_y = [s["origin"][1] for s in r if "origin" in s]
                        if len(origins_y) < 2:
                            continue

                        median_baseline = statistics.median(origins_y)

                        # Find standard body font for this row
                        font_names = [s.get("font", "") for s in r if s.get("font")]
                        majority_font = max(set(font_names), key=font_names.count) if font_names else ""

                        for s in r:
                                text = s.get("text", "").strip()
                                if not text:
                                    continue

                                origin_y = s["origin"][1]
                                y_offset = abs(origin_y - median_baseline)
                                span_font = s.get("font", "")
                                span_size = s.get("size", 0.0)
                                bbox = s.get("bbox", [0, 0, 0, 0])  # x0, y0, x1, y1

                                # Check 1: Significant vertical baseline offset (> 0.75 pt)
                                # Attacker typed or pasted replacement text manually in Acrobat
                                has_digits = any(char.isdigit() for char in text)
                                if y_offset > 0.75 and has_digits:
                                    finding = await tx.evidenceitem.create(
                                        data={
                                            "document": {"connect": {"id": doc.id}},
                                            "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                            "category": "FONT_BASELINE_INCONSISTENCY",
                                            "severity": "CRITICAL" if y_offset > 2.0 else "HIGH",
                                            "ruleId": "RULE_FONT_BASELINE_OFFSET",
                                            "riskPoints": 30,
                                            "title": "Sub-Pixel Typography Baseline Offset on Financial Value",
                                            "description": (
                                                f"Text span '{text}' has a vertical baseline deviation of {y_offset:.2f} pt "
                                                f"from the line median ({median_baseline:.2f} pt). In programmatic bank statements, "
                                                "all text on a line shares a strictly identical baseline coordinate (jitter < 0.05 pt). "
                                                "This physical artifact indicates spliced or inserted text."
                                            ),
                                            "isDeterministic": True,
                                            "pageNumber": page_num,
                                            "expectedValue": f"{median_baseline:.2f} pt baseline",
                                            "actualValue": f"{origin_y:.2f} pt baseline",
                                            "discrepancy": f"{y_offset:.2f} pt vertical offset",
                                            "technicalDetails": Json({
                                                "text": text,
                                                "span_font": span_font,
                                                "span_size": span_size,
                                                "y_offset_pt": round(y_offset, 3),
                                                "median_baseline_pt": round(median_baseline, 3),
                                                "bbox_pts": bbox,
                                            }),
                                        }
                                    )

                                    # Create BoundingBox for evidence canvas
                                    x0_pts, y0_pts, x1_pts, y1_pts = bbox
                                    width_pts = max(1.0, x1_pts - x0_pts)
                                    height_pts = max(1.0, y1_pts - y0_pts)

                                    await tx.boundingbox.create(
                                        data={
                                            "evidenceItem": {"connect": {"id": finding.id}},
                                            "pageNumber": page_num,
                                            "x": float(x0_pts * scale_x),
                                            "y": float(y0_pts * scale_y),
                                            "width": float(width_pts * scale_x),
                                            "height": float(height_pts * scale_y),
                                            "xPts": float(x0_pts),
                                            "yPts": float(y0_pts),
                                            "widthPts": float(width_pts),
                                            "heightPts": float(height_pts),
                                            "label": f"Baseline Offset ({y_offset:.2f}pt)",
                                            "color": "#ef4444",
                                        }
                                    )

                                    stage_findings.append({
                                        "id": finding.id,
                                        "rule_id": "RULE_FONT_BASELINE_OFFSET",
                                        "severity": finding.severity,
                                        "page": page_num,
                                        "title": finding.title,
                                    })

                                # Check 2: Font Family / Subset mismatch on financial amount
                                elif majority_font and span_font and span_font != majority_font and has_digits:
                                    # Strip subset prefix (e.g. "ABCDEE+Calibri" -> "Calibri")
                                    clean_span_font = span_font.split("+")[-1]
                                    clean_majority = majority_font.split("+")[-1]

                                    if clean_span_font.lower() != clean_majority.lower():
                                        finding = await tx.evidenceitem.create(
                                            data={
                                                "document": {"connect": {"id": doc.id}},
                                                "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                                "category": "FONT_BASELINE_INCONSISTENCY",
                                                "severity": "HIGH",
                                                "ruleId": "RULE_FONT_FAMILY_MISMATCH",
                                                "riskPoints": 25,
                                                "title": "Font Family Mismatch on Financial Amount",
                                                "description": (
                                                    f"Text '{text}' is rendered in font '{span_font}' while the rest of "
                                                    f"the row uses '{majority_font}'. Spliced digits typically use desktop "
                                                    "fallback fonts rather than the bank's embedded document font subset."
                                                ),
                                                "isDeterministic": True,
                                                "pageNumber": page_num,
                                                "expectedValue": majority_font,
                                                "actualValue": span_font,
                                                "discrepancy": f"Font mismatch: {span_font} vs {majority_font}",
                                                "technicalDetails": Json({
                                                    "text": text,
                                                    "line_font": majority_font,
                                                    "span_font": span_font,
                                                    "bbox_pts": bbox,
                                                }),
                                            }
                                        )

                                        x0_pts, y0_pts, x1_pts, y1_pts = bbox
                                        width_pts = max(1.0, x1_pts - x0_pts)
                                        height_pts = max(1.0, y1_pts - y0_pts)

                                        await tx.boundingbox.create(
                                            data={
                                                "evidenceItem": {"connect": {"id": finding.id}},
                                                "pageNumber": page_num,
                                                "x": float(x0_pts * scale_x),
                                                "y": float(y0_pts * scale_y),
                                                "width": float(width_pts * scale_x),
                                                "height": float(height_pts * scale_y),
                                                "xPts": float(x0_pts),
                                                "yPts": float(y0_pts),
                                                "widthPts": float(width_pts),
                                                "heightPts": float(height_pts),
                                                "label": f"Font Mismatch ({clean_span_font})",
                                                "color": "#f59e0b",
                                            }
                                        )

                                        stage_findings.append({
                                            "id": finding.id,
                                            "rule_id": "RULE_FONT_FAMILY_MISMATCH",
                                            "severity": finding.severity,
                                            "page": page_num,
                                            "title": finding.title,
                                        })

                pdf_doc.close()

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
    name="app.features.pipeline.tasks.stage_3_font_glyph",
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
    """Celery task entry point for Stage 3."""
    import asyncio
    return asyncio.run(
        process_font_glyph(
            pipeline_run_id, pipeline_stage_id, org_id, investigation_id, document_id
        )
    )
