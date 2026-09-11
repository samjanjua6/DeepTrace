import io
import logging
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

logger = logging.getLogger(__name__)
settings = get_settings()


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
