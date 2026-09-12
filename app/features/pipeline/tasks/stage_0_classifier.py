"""
Stage 0: Multi-Modal Document Classification & Layout Triage — Celery Task & Async Processor
NIST SP 800-86 Compliant Pre-Pipeline Document Triage.
"""
from datetime import datetime, timezone
import time
from typing import Any

from prisma import Json

from app.config import get_settings
from app.core.celery_app import celery_app
from app.core.storage import storage
from app.db.client import db, set_org_context
from app.features.pipeline.tasks.document_classifier import document_classifier

settings = get_settings()


async def process_document_classification(
    pipeline_run_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Stage 0: Multi-Modal Document Classification.
    Extracts 2D spatial layout tokens, matches Pakistani institutional anchors and identifiers
    (Bank Statement, Salary Slip, K-Electric Bill, FBR Challan, CNIC), calibrates probabilities,
    and updates the Document's canonical documentType in PostgreSQL.
    """
    start_time = time.perf_counter()

    async with set_org_context(org_id) as tx:
        where_doc: dict[str, Any] = {"investigationId": investigation_id}
        if document_id:
            where_doc["id"] = document_id

        documents = await tx.document.find_many(where=where_doc)
        if not documents:
            raise ValueError(f"No documents found for investigation '{investigation_id}'")

        classification_summaries = []

        for doc in documents:
            file_bytes = storage.get_file(settings.s3_bucket_documents, doc.storagePath)
            if not file_bytes:
                raise FileNotFoundError(
                    f"Document '{doc.id}' missing in storage path '{doc.storagePath}'"
                )

            # Execute multi-modal classifier
            result = document_classifier.classify_document(
                data=file_bytes,
                mime=doc.mimeType,
            )

            # Atomically update documentType in database
            await tx.document.update(
                where={"id": doc.id},
                data={"documentType": result.document_type},
            )

            summary = {
                "document_id": doc.id,
                "filename": doc.originalFilename,
                "classified_type": result.document_type,
                "subtype": result.subtype,
                "confidence": result.confidence,
                "matched_anchors": result.matched_anchors,
                "layout_signals": result.layout_signals,
                "candidate_scores": result.candidate_scores,
                "decision_rationale": result.decision_rationale,
            }
            classification_summaries.append(summary)

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Store classification telemetry in PipelineRun.parameters
        run = await tx.pipelinerun.find_unique(where={"id": pipeline_run_id})
        current_params = dict(run.parameters) if (run and run.parameters) else {}
        current_params["stage_0_classification"] = {
            "duration_ms": duration_ms,
            "documents": classification_summaries,
            "primary_classification": classification_summaries[0]["classified_type"] if classification_summaries else "OTHER",
            "primary_subtype": classification_summaries[0]["subtype"] if classification_summaries else "GENERIC",
        }
        await tx.pipelinerun.update(
            where={"id": pipeline_run_id},
            data={"parameters": Json(current_params)},
        )

        return current_params["stage_0_classification"]


@celery_app.task(
    name="app.features.pipeline.tasks.stage_0_classifier",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def stage_0_classifier_task(
    self,
    pipeline_run_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """Celery task entry point for Stage 0 Document Classification."""
    import asyncio
    try:
        return asyncio.run(
            process_document_classification(
                pipeline_run_id=pipeline_run_id,
                org_id=org_id,
                investigation_id=investigation_id,
                document_id=document_id,
            )
        )
    except Exception as exc:
        raise self.retry(exc=exc)
