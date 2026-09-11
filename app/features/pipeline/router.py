"""Pipeline router — /api/v1/investigations/{id}/... pipeline endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth.dependencies import get_current_user
from app.features.investigations.dependencies import get_investigation
from app.features.pipeline import schemas, service

router = APIRouter()


@router.post(
    "/{investigation_id}/analyze",
    response_model=schemas.PipelineRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger the 8-stage forensic pipeline",
)
async def trigger_pipeline(
    body: schemas.PipelineTriggerRequest = schemas.PipelineTriggerRequest(),
    investigation=Depends(get_investigation),
    user=Depends(get_current_user),
):
    """
    Initiate the full 8-stage forensic analysis pipeline for this investigation.
    Runs asynchronously and updates stage statuses in real-time.
    """
    run = await service.trigger_pipeline(
        org_id=investigation.organizationId,
        investigation_id=investigation.id,
        triggered_by=user.id,
        parameters=body.parameters,
        document_id=body.document_id,
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize forensic pipeline run.",
        )
    return run


@router.get(
    "/{investigation_id}/pipeline",
    response_model=schemas.PipelineRunResponse,
    summary="Get latest pipeline run status and stage breakdown",
)
async def get_pipeline_status(
    investigation=Depends(get_investigation),
):
    """Retrieve current execution status and stage-by-stage progress of the forensic pipeline."""
    run = await service.get_pipeline_status(
        org_id=investigation.organizationId,
        investigation_id=investigation.id,
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pipeline run has been triggered for this investigation yet.",
        )
    return run


@router.post(
    "/{investigation_id}/pipeline/retry",
    response_model=schemas.PipelineRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed pipeline",
)
async def retry_pipeline(
    investigation=Depends(get_investigation),
    user=Depends(get_current_user),
):
    """Re-trigger forensic pipeline execution for an investigation."""
    run = await service.retry_failed_pipeline(
        org_id=investigation.organizationId,
        investigation_id=investigation.id,
        user_id=user.id,
    )
    return run
