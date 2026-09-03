"""organizations router."""
from typing import Annotated
from fastapi import APIRouter, Depends
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth.dependencies import get_current_user
from app.features.organizations import schemas, service

router = APIRouter()


@router.get("", response_model=schemas.OrgResponse, summary="Get current organization")
async def get_org(
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    return await service.get_org(db, user.organizationId)


@router.patch("/settings", response_model=schemas.OrgResponse, summary="Update organization settings")
async def update_settings(
    body: schemas.OrgSettingsUpdate,
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    return await service.update_settings(db, user.organizationId, body.model_dump(exclude_unset=True))


@router.get("/usage", response_model=schemas.UsageStatsResponse, summary="Get current usage statistics")
async def get_usage(
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    return await service.get_usage_stats(db, user.organizationId)
