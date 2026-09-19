"""
DeepTrace — Celery Pipeline Orchestrator & Lifecycle Management
Provides:
  1. orchestrate_pipeline: Runs the full 8-stage pipeline inside a background Celery worker.
  2. finalize_pipeline_run: Canvas completion callback to compute total runtime and update investigation status.
  3. handle_pipeline_failure: Canvas errback to mark the run and investigation as FAILED upon unexpected errors.
"""
import asyncio
from datetime import datetime, timezone
import logging
import time

from app.core.celery_app import celery_app
from app.db.client import set_org_context

logger = logging.getLogger(__name__)


async def _async_finalize(pipeline_run_id: str, org_id: str, investigation_id: str) -> dict:
    """Async logic to finalize a successful pipeline run."""
    async with set_org_context(org_id) as tx:
        run = await tx.pipelinerun.find_unique(where={"id": pipeline_run_id})
        now = datetime.now(timezone.utc)
        duration_ms = 0
        if run and run.startedAt:
            duration_ms = int((now - run.startedAt).total_seconds() * 1000)

        await tx.pipelinerun.update(
            where={"id": pipeline_run_id},
            data={
                "status": "COMPLETED",
                "totalDurationMs": duration_ms,
                "completedAt": now,
            },
        )

        risk = await tx.riskassessment.find_unique(where={"investigationId": investigation_id})
        adverse_count = (risk.criticalCount + risk.highCount + risk.mediumCount + risk.lowCount) if risk else 0
        new_status = (
            "AWAITING_REVIEW"
            if (risk and (risk.overallScore > 20 or adverse_count > 0))
            else "REVIEWED"
        )
        await tx.investigation.update(
            where={"id": investigation_id},
            data={"status": new_status},
        )

        logger.info(f"Pipeline run {pipeline_run_id} finalized as COMPLETED ({duration_ms}ms). Investigation status: {new_status}")
        return {"status": "COMPLETED", "duration_ms": duration_ms, "investigation_status": new_status}


async def _async_handle_failure(pipeline_run_id: str, org_id: str, error_msg: str, investigation_id: str | None = None) -> None:
    """Async logic to mark a pipeline run and its investigation as FAILED."""
    async with set_org_context(org_id) as tx:
        run = await tx.pipelinerun.find_unique(where={"id": pipeline_run_id})
        now = datetime.now(timezone.utc)
        duration_ms = 0
        if run and run.startedAt:
            duration_ms = int((now - run.startedAt).total_seconds() * 1000)

        await tx.pipelinerun.update(
            where={"id": pipeline_run_id},
            data={
                "status": "FAILED",
                "totalDurationMs": duration_ms,
                "completedAt": now,
                "errorMessage": error_msg,
            },
        )

        target_inv_id = investigation_id or (run.investigationId if run else None)
        if target_inv_id:
            await tx.investigation.update(
                where={"id": target_inv_id},
                data={"status": "FAILED"},
            )

        logger.error(f"Pipeline run {pipeline_run_id} marked as FAILED: {error_msg}")


@celery_app.task(
    name="app.features.pipeline.tasks.orchestrator.orchestrate_pipeline",
    bind=True,
    max_retries=1,
)
def orchestrate_pipeline(
    self,
    pipeline_run_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> None:
    """
    Execute the entire 8-stage forensic pipeline sequentially inside a Celery worker.
    Offloads execution from the API web process to the Celery worker pool.
    """
    from app.features.pipeline.service import run_pipeline_inline
    logger.info(f"[Celery Worker] Starting orchestrated pipeline run {pipeline_run_id} for investigation {investigation_id}")
    asyncio.run(
        run_pipeline_inline(
            pipeline_run_id=pipeline_run_id,
            org_id=org_id,
            investigation_id=investigation_id,
            document_id=document_id,
        )
    )


@celery_app.task(
    name="app.features.pipeline.tasks.orchestrator.finalize_pipeline_run",
    bind=True,
)
def finalize_pipeline_run(
    self,
    pipeline_run_id: str,
    org_id: str,
    investigation_id: str,
) -> dict:
    """Celery task callback to finalize a completed canvas pipeline run."""
    return asyncio.run(_async_finalize(pipeline_run_id, org_id, investigation_id))


@celery_app.task(
    name="app.features.pipeline.tasks.orchestrator.handle_pipeline_failure",
    bind=True,
)
def handle_pipeline_failure(
    self,
    request=None,
    exc=None,
    traceback=None,
    pipeline_run_id: str | None = None,
    org_id: str | None = None,
    investigation_id: str | None = None,
    **kwargs,
) -> None:
    """
    Celery errback callback when any task in a pipeline chain fails.
    Receives request, exc, traceback from Celery canvas errback.
    """
    error_msg = str(exc) if exc else "Pipeline stage failed with an unhandled exception."
    run_id = pipeline_run_id or kwargs.get("pipeline_run_id")
    target_org = org_id or kwargs.get("org_id", "org_default")
    target_inv = investigation_id or kwargs.get("investigation_id")

    if run_id:
        asyncio.run(_async_handle_failure(run_id, target_org, error_msg, target_inv))
    else:
        logger.error(f"handle_pipeline_failure called without pipeline_run_id: {error_msg}")
