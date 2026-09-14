"""api_keys router — Institutional Administrative Credential Gateway."""
from typing import Annotated
from fastapi import APIRouter, Depends, Request, Query
from prisma import Prisma

from app.db.client import get_db_dep
from app.db.enums import UserRole
from app.features.auth.dependencies import require_role
from app.features.api_keys import schemas, service

router = APIRouter()

# Restrict all API key operations to institutional administrators (ADMIN and OWNER)
AdminUser = Depends(require_role(UserRole.ADMIN, UserRole.OWNER))


@router.get("", response_model=list[schemas.ApiKeyResponse], summary="List API keys for the organization (Admin only)")
async def list_api_keys(
    include_revoked: bool = Query(default=False, description="Include revoked historical keys"),
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    return await service.list_keys(db, user.organizationId, include_revoked=include_revoked)


@router.post("", response_model=schemas.ApiKeyCreatedResponse, status_code=201, summary="Create a new API key (Admin only)")
async def create_api_key(
    body: schemas.ApiKeyCreate,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.create_key(
        db,
        user.organizationId,
        user.id,
        body.model_dump(),
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.delete("/{key_id}", status_code=204, summary="Revoke an API key (Admin only)")
async def revoke_api_key(
    key_id: str,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await service.revoke_key(
        db,
        user.organizationId,
        key_id,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

