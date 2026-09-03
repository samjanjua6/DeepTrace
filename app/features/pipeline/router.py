"""Pipeline router — /api/v1/investigations/{id}/... pipeline endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth.dependencies import get_current_user
from app.features.investigations.dependencies import get_investigation
from app.features.pipeline import schemas, service

router = APIRouter()


@router.post("/{investigation_id}/analyze", response_model=schemas.PipelineRunResponse,
             status_code=202, summary="Trigger the 8-stage forensic pipeline")
async def trigger_pipeline(
    body: schemas.PipelineTriggerRequest,
    investigation=Depends(get_investigation),
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    # TODO: service.trigger_pipeline(...)
    raise NotImplementedError


@router.get("/{investigation_id}/pipeline", response_model=schemas.PipelineRunResponse,
            summary="Get latest pipeline run status and stage breakdown")
async def get_pipeline_status(
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    return await service.get_pipeline_status(db, investigation.id)


@router.post("/{investigation_id}/pipeline/retry", response_model=schemas.PipelineRunResponse,
             status_code=202, summary="Retry a failed pipeline")
async def retry_pipeline(
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    # TODO: service.retry_failed_pipeline(...)
    raise NotImplementedError
