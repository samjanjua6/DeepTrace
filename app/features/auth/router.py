"""Auth router — /api/v1/auth endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth import schemas, service
from app.features.auth.dependencies import CurrentUser

router = APIRouter()


@router.post("/login", response_model=schemas.TokenResponse, summary="Login with email + password")
async def login(
    body: schemas.LoginRequest,
    request: Request,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    return await service.login(db, body.email, body.password, ip_address=request.client.host if request.client else None)


@router.post("/logout", status_code=204, summary="Revoke current session")
async def logout(
    body: schemas.RefreshRequest,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    from app.core.security import hash_token
    await service.logout(db, hash_token(body.refresh_token))


@router.get("/me", response_model=schemas.MeResponse, summary="Get current authenticated user")
async def me(current_user: CurrentUser):
    return schemas.MeResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.firstName,
        last_name=current_user.lastName,
        role=current_user.role,
        organization_id=current_user.organizationId,
        mfa_enabled=current_user.mfaEnabled,
    )
