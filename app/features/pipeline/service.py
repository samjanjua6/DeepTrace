"""
Pipeline service — orchestrates the 8-stage forensic pipeline via Celery.
TODO: Implement each function stub.
"""
from prisma import Prisma

from app.core.celery_app import celery_app


async def trigger_pipeline(db: Prisma, investigation_id: str, triggered_by: str,
                            parameters: dict | None = None) -> object:
    """
    Create a PipelineRun record and dispatch Stage 1 Celery task.
    Stages chain automatically: each stage dispatches the next on completion.
    """
    # TODO: determine run_number (max existing + 1)
    # TODO: db.pipelinerun.create(...)
    # TODO: celery_app.send_task("stage_1_custody", args=[pipeline_run_id])
    raise NotImplementedError


async def get_pipeline_status(db: Prisma, investigation_id: str) -> object:
    """Return the latest PipelineRun and all its stage statuses."""
    # TODO: db.pipelinerun.find_first(orderBy={"runNumber": "desc"}, include={"stages": True})
    raise NotImplementedError


async def retry_failed_pipeline(db: Prisma, pipeline_run_id: str) -> object:
    """Re-trigger a failed pipeline from the first failed stage."""
    # TODO: find the failed stage, re-dispatch its Celery task
    raise NotImplementedError
