"""Investigations router — /api/v1/investigations."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth.dependencies import get_current_user
from app.features.investigations import schemas, service
from app.features.investigations.dependencies import get_investigation

router = APIRouter()


@router.post("", response_model=schemas.InvestigationResponse, status_code=201,
             summary="Create a new forensic investigation")
async def create_investigation(
    body: schemas.InvestigationCreate,
    db: Annotated[Prisma, Depends(get_db_dep)],
    user=Depends(get_current_user),
):
    return await service.create_investigation(db, user.organizationId, user.id, body.model_dump())


@router.get("", response_model=list[schemas.InvestigationResponse],
            summary="List investigations (paginated, filterable)")
async def list_investigations(
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
    status: str | None = Query(default=None),
    priority: int | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    filters = {"status": status, "priority": priority, "search": search}
    return await service.list_investigations(db, user.organizationId, filters, page, page_size)


@router.get("/{investigation_id}", response_model=schemas.InvestigationResponse,
            summary="Get a single investigation by ID")
async def get_investigation_detail(investigation=Depends(get_investigation)):
    return investigation


@router.patch("/{investigation_id}", response_model=schemas.InvestigationResponse,
              summary="Update an investigation")
async def update_investigation(
    body: schemas.InvestigationUpdate,
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    return await service.update_investigation(
        db, investigation.organizationId, investigation.id, body.model_dump(exclude_unset=True)
    )


@router.post("/{investigation_id}/close", status_code=204,
             summary="Close an investigation")
async def close_investigation(
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    await service.close_investigation(db, investigation.organizationId, investigation.id)
