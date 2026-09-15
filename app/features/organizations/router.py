"""organizations router."""
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from prisma import Prisma

from app.db.client import get_db_dep
from app.db.enums import UserRole
from app.features.auth.dependencies import get_current_user, require_role
from app.features.organizations import schemas, service

router = APIRouter()
AdminUser = Depends(require_role(UserRole.ADMIN, UserRole.OWNER))


@router.get("", response_model=schemas.OrgResponse, summary="Get current organization")
async def get_org(
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """Retrieve organization metadata, licensed subscription tier, and quota overview."""
    return await service.get_org(db, user.organizationId)


@router.patch("/settings", response_model=schemas.OrgResponse, summary="Update organization settings")
async def update_settings(
    body: schemas.OrgSettingsUpdate,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """
    Update organization settings (institutional administrators only).
    Logs immutable audit entry into PostgreSQL audit_logs under SBP compliance.
    """
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    return await service.update_settings(
        db,
        user.organizationId,
        body.model_dump(exclude_unset=True),
        user_id=user.id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get("/usage", response_model=schemas.UsageStatsResponse, summary="Get current usage statistics")
async def get_usage(
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """
    Retrieve document usage metrics, remaining quota, days until billing cycle renewal,
    and volume breakdown by document classification type.
    """
    return await service.get_usage_stats(db, user.organizationId)


@router.post("/tier", response_model=schemas.OrgResponse, summary="Upgrade or modify subscription tier")
async def upgrade_tier(
    body: schemas.TierUpgradeRequest,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """
    Upgrade or switch institutional subscription tier (ADMIN and OWNER only).
    Recalculates monthly document allowance and creates immutable SBP audit trail.
    """
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    return await service.upgrade_tier(
        db,
        user.organizationId,
        body.target_tier.value,
        user_id=user.id,
        ip_address=ip,
        user_agent=user_agent,
    )
