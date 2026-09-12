"""
Pipeline service — orchestrates the 8-stage forensic pipeline.
Supports dual execution: distributed Celery workers with automatic in-process async fallback
when Redis or worker processes are offline.
"""
import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any

from prisma import Json, Prisma

from app.config import get_settings
from app.core.celery_app import celery_app
from app.db.client import db, set_org_context
from app.features.pipeline.tasks.stage_1_custody import process_custody_lock
from app.features.pipeline.tasks.stage_2_pdf_structure import process_pdf_structure
from app.features.pipeline.tasks.stage_3_font_glyph import process_font_glyph
from app.features.pipeline.tasks.stage_4_vision_ela import process_vision_ela
from app.features.pipeline.tasks.stage_5_ocr import process_ocr
from app.features.pipeline.tasks.stage_6_financial import process_financial
from app.features.pipeline.tasks.stage_7_fusion import process_evidence_fusion
from app.features.pipeline.tasks.stage_8_report import process_report_generation

logger = logging.getLogger(__name__)
settings = get_settings()

# The 8 canonical forensic pipeline stages in strict execution order
STAGE_FLOW = [
    (1, "CUSTODY_LOCK", process_custody_lock, "stage_1_custody"),
    (2, "PDF_STRUCTURE", process_pdf_structure, "stage_2_pdf_structure"),
    (3, "FONT_GLYPH_ANALYSIS", process_font_glyph, "stage_3_font_glyph"),
    (4, "VISION_ELA", process_vision_ela, "stage_4_vision_ela"),
    (5, "OCR_EXTRACTION", process_ocr, "stage_5_ocr"),
    (6, "FINANCIAL_VERIFICATION", process_financial, "stage_6_financial"),
    (7, "EVIDENCE_FUSION", process_evidence_fusion, "stage_7_fusion"),
    (8, "REPORT_GENERATION", process_report_generation, "stage_8_report"),
]


def is_redis_available() -> bool:
    """Check if Redis broker is reachable for Celery dispatch."""
    try:
        import redis
        client = redis.from_url(settings.celery_broker_url, socket_timeout=0.4, socket_connect_timeout=0.4)
        return bool(client.ping())
    except Exception:
        return False


async def run_pipeline_inline(
    pipeline_run_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> None:
    """
    In-process asynchronous pipeline runner.
    Executes each stage sequentially under tenant RLS context, updating database state in real-time.
    Used for local development and test environments when Celery is offline.
    """
    start_time = time.perf_counter()

    async with set_org_context(org_id) as tx:
        # Mark run as RUNNING
        await tx.pipelinerun.update(
            where={"id": pipeline_run_id},
            data={"status": "RUNNING", "startedAt": datetime.now(timezone.utc)},
        )

        stages = await tx.pipelinestage.find_many(
            where={"pipelineRunId": pipeline_run_id},
            order={"stageOrder": "asc"},
        )
        stage_map = {s.stageOrder: s for s in stages}

    # Stage 0: Automated Multi-Modal Document Classification & Layout Triage
    try:
        logger.info(f"Executing Stage 0: DOCUMENT_CLASSIFICATION for run {pipeline_run_id}")
        from app.features.pipeline.tasks.stage_0_classifier import process_document_classification
        await process_document_classification(
            pipeline_run_id=pipeline_run_id,
            org_id=org_id,
            investigation_id=investigation_id,
            document_id=document_id,
        )
    except Exception as cls_exc:
        logger.warning(f"Stage 0 document classification encountered an error (proceeding): {cls_exc}", exc_info=True)

    failed = False
    failure_reason = None

    for order, stage_type, stage_func, _ in STAGE_FLOW:
        stage_record = stage_map.get(order)
        if not stage_record:
            continue

        try:
            logger.info(f"Executing pipeline stage {order}: {stage_type} for run {pipeline_run_id}")
            await stage_func(
                pipeline_run_id=pipeline_run_id,
                pipeline_stage_id=stage_record.id,
                org_id=org_id,
                investigation_id=investigation_id,
                document_id=document_id,
            )
        except Exception as exc:
            logger.error(f"Pipeline stage {stage_type} failed: {exc}", exc_info=True)
            failed = True
            failure_reason = str(exc)
            break

    total_duration_ms = int((time.perf_counter() - start_time) * 1000)

    async with set_org_context(org_id) as tx:
        if failed:
            await tx.pipelinerun.update(
                where={"id": pipeline_run_id},
                data={
                    "status": "FAILED",
                    "totalDurationMs": total_duration_ms,
                    "completedAt": datetime.now(timezone.utc),
                    "errorMessage": failure_reason,
                },
            )
            await tx.investigation.update(
                where={"id": investigation_id},
                data={"status": "FAILED"},
            )
        else:
            await tx.pipelinerun.update(
                where={"id": pipeline_run_id},
                data={
                    "status": "COMPLETED",
                    "totalDurationMs": total_duration_ms,
                    "completedAt": datetime.now(timezone.utc),
                },
            )
            # Sync Investigation status based on computed risk
            risk = await tx.riskassessment.find_unique(where={"investigationId": investigation_id})
            new_status = (
                "AWAITING_REVIEW"
                if (risk and (risk.overallScore > 20 or risk.totalEvidenceCount > 0))
                else "REVIEWED"
            )
            await tx.investigation.update(
                where={"id": investigation_id},
                data={"status": new_status},
            )

    # Dispatch outbound webhook events (after pipeline transaction commits)
    try:
        from app.features.webhooks.service import dispatch_event
        async with set_org_context(org_id) as hook_tx:
            if failed:
                await dispatch_event(hook_tx, org_id, "pipeline.failed", {
                    "investigation_id": investigation_id,
                    "pipeline_run_id": pipeline_run_id,
                    "status": "FAILED",
                })
            else:
                event_payload = {
                    "investigation_id": investigation_id,
                    "pipeline_run_id": pipeline_run_id,
                    "status": "COMPLETED",
                    "overall_score": risk.overallScore if risk else 0,
                    "risk_tier": risk.riskTier if risk else "LOW",
                    "action_directive": risk.actionDirective if risk else "STRAIGHT_THROUGH_APPROVAL",
                }
                await dispatch_event(hook_tx, org_id, "investigation.completed", event_payload)
                if risk and risk.riskTier == "CRITICAL":
                    await dispatch_event(hook_tx, org_id, "risk.critical", event_payload)
    except Exception as webhook_err:
        logger.warning(f"Could not dispatch pipeline webhooks: {webhook_err}")


def build_celery_canvas_chain(
    pipeline_run_id: str,
    stage_map: dict[int, Any],
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
):
    """Build a Celery canvas chain of all 8 stages with finalizer and per-stage error handlers."""
    from celery import chain

    errback = celery_app.signature(
        "app.features.pipeline.tasks.orchestrator.handle_pipeline_failure",
        args=[pipeline_run_id, org_id],
        kwargs={"investigation_id": investigation_id},
        queue="pipeline",
    )

    signatures = []
    for order, _, _, task_module in STAGE_FLOW:
        stage_rec = stage_map.get(order)
        stage_id = stage_rec.id if stage_rec else ""
        sig = celery_app.signature(
            f"app.features.pipeline.tasks.{task_module}",
            args=[pipeline_run_id, stage_id, org_id, investigation_id, document_id],
            immutable=True,
            queue="pipeline",
        )
        sig.set(link_error=errback)
        signatures.append(sig)

    # Append completion finalizer
    finalizer = celery_app.signature(
        "app.features.pipeline.tasks.orchestrator.finalize_pipeline_run",
        args=[pipeline_run_id, org_id, investigation_id],
        immutable=True,
        queue="pipeline",
    )
    finalizer.set(link_error=errback)
    signatures.append(finalizer)

    return chain(*signatures)


async def trigger_pipeline(
    org_id: str,
    investigation_id: str,
    triggered_by: str,
    parameters: dict | None = None,
    document_id: str | None = None,
    use_canvas_chain: bool = False,
) -> Any:
    """
    Create a PipelineRun record and initialize the 8 PipelineStages.
    Dispatches via Celery if Redis is available, or runs in-process async fallback.
    """
    stage_map: dict[int, Any] = {}

    async with set_org_context(org_id) as tx:
        # Determine monotonic run number
        existing_runs = await tx.pipelinerun.find_many(
            where={"investigationId": investigation_id},
            order={"runNumber": "desc"},
            take=1,
        )
        run_number = (existing_runs[0].runNumber + 1) if existing_runs else 1

        # Create PipelineRun record
        pipeline_run = await tx.pipelinerun.create(
            data={
                "investigation": {"connect": {"id": investigation_id}},
                "runNumber": run_number,
                "status": "PENDING",
                "triggerSource": "api",
                "triggerUserId": triggered_by,
                "parameters": Json(parameters or {}),
            }
        )

        # Pre-create all 8 stages with PENDING status and record in stage_map
        for order, stage_type, _, _ in STAGE_FLOW:
            stage_rec = await tx.pipelinestage.create(
                data={
                    "pipelineRun": {"connect": {"id": pipeline_run.id}},
                    "stageType": stage_type,
                    "stageOrder": order,
                    "status": "PENDING",
                }
            )
            stage_map[order] = stage_rec

        # Update Investigation to PROCESSING
        await tx.investigation.update(
            where={"id": investigation_id},
            data={"status": "PROCESSING"},
        )

    # Dispatch: Check Celery / Redis availability
    if is_redis_available():
        logger.info(f"Redis reachable. Dispatching pipeline run {pipeline_run.id} to Celery worker queue")
        if use_canvas_chain:
            # Granular stage-by-stage Celery canvas chain
            chain_workflow = build_celery_canvas_chain(
                pipeline_run_id=pipeline_run.id,
                stage_map=stage_map,
                org_id=org_id,
                investigation_id=investigation_id,
                document_id=document_id,
            )
            chain_workflow.apply_async()
        else:
            # Dedicated background Celery worker orchestrator (atomic & resilient)
            celery_app.send_task(
                "app.features.pipeline.tasks.orchestrator.orchestrate_pipeline",
                args=[pipeline_run.id, org_id, investigation_id, document_id],
                queue="pipeline",
            )
    else:
        logger.info(f"Redis offline. Executing pipeline run {pipeline_run.id} via in-process async worker")
        asyncio.create_task(
            run_pipeline_inline(pipeline_run.id, org_id, investigation_id, document_id)
        )

    # Return created run with stages
    return await get_pipeline_status(org_id, investigation_id)


async def get_pipeline_status(org_id: str, investigation_id: str) -> Any:
    """Return the latest PipelineRun and all its stage statuses."""
    async with set_org_context(org_id) as tx:
        run = await tx.pipelinerun.find_first(
            where={"investigationId": investigation_id},
            order={"runNumber": "desc"},
            include={"stages": True},
        )
        if not run:
            return None

        # Sort stages by stageOrder
        if run.stages:
            run.stages = sorted(run.stages, key=lambda s: s.stageOrder)

        return run


async def retry_failed_pipeline(org_id: str, investigation_id: str, user_id: str) -> Any:
    """Re-trigger a fresh pipeline run for the investigation after resetting partial artifacts."""
    async with set_org_context(org_id) as tx:
        docs = await tx.document.find_many(where={"investigationId": investigation_id})
        doc_ids = [d.id for d in docs]
        if doc_ids:
            await tx.evidenceitem.delete_many(where={"documentId": {"in": doc_ids}})
        await tx.riskassessment.delete_many(where={"investigationId": investigation_id})

    return await trigger_pipeline(
        org_id=org_id,
        investigation_id=investigation_id,
        triggered_by=user_id,
    )
