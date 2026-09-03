"""api_keys router."""
from typing import Annotated
from fastapi import APIRouter, Depends
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth.dependencies import get_current_user
from app.features.api_keys import schemas, service

router = APIRouter()


@router.get("", response_model=list[schemas.ApiKeyResponse], summary="List API keys for the organization")
async def list_api_keys(
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    return await service.list_keys(db, user.organizationId)


@router.post("", response_model=schemas.ApiKeyCreatedResponse, status_code=201, summary="Create a new API key")
async def create_api_key(
    body: schemas.ApiKeyCreate,
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    return await service.create_key(db, user.organizationId, user.id, body.model_dump())


@router.delete("/{key_id}", status_code=204, summary="Revoke an API key")
async def revoke_api_key(
    key_id: str,
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    await service.revoke_key(db, user.organizationId, key_id)
