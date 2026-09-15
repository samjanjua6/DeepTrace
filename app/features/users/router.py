"""User & Role Administration router — /api/v1/users endpoints."""
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from prisma import Prisma

from app.db.client import get_db_dep
from app.db.enums import UserRole
from app.features.auth.dependencies import require_role
from app.features.users import schemas, service

router = APIRouter()
AdminUser = Depends(require_role(UserRole.ADMIN, UserRole.OWNER))


@router.get("", response_model=list[schemas.UserItemResponse], summary="List organization members and roles")
async def list_users(
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """List all members, roles, MFA status, and account lockout state for the current institutional tenant."""
    return await service.list_users(db, user.organizationId)


@router.post("/invite", response_model=schemas.InviteUserResponse, status_code=201, summary="Invite or onboard a new analyst")
async def invite_user(
    body: schemas.InviteUserRequest,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """
    Onboard an institutional analyst or admin with an SBP-compliant temporary credential
    and record an immutable compliance audit event.
    """
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    return await service.invite_user(
        db=db,
        org_id=user.organizationId,
        payload=body,
        actor_id=user.id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.patch("/{user_id}/role", response_model=schemas.UserItemResponse, summary="Change member role clearance")
async def update_role(
    user_id: str,
    body: schemas.UpdateUserRoleRequest,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """Promote or demote a member's institutional role clearance level."""
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    return await service.update_user_role(
        db=db,
        org_id=user.organizationId,
        user_id=user_id,
        new_role=body.role,
        actor=user,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.patch("/{user_id}/status", response_model=schemas.UserItemResponse, summary="Activate or suspend member account")
async def update_status(
    user_id: str,
    body: schemas.UpdateUserStatusRequest,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """Suspend or reactivate member account and revoke active sessions upon deactivation."""
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    return await service.update_user_status(
        db=db,
        org_id=user.organizationId,
        user_id=user_id,
        is_active=body.is_active,
        actor=user,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post("/{user_id}/unlock", response_model=schemas.ActionMessageResponse, summary="Unlock account after brute-force lockout")
async def unlock_user(
    user_id: str,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """Unlock an account that was locked after consecutive failed login attempts."""
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    return await service.unlock_user_account(
        db=db,
        org_id=user.organizationId,
        user_id=user_id,
        actor=user,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post("/{user_id}/reset-mfa", response_model=schemas.ActionMessageResponse, summary="Emergency reset of member 2FA")
async def reset_mfa(
    user_id: str,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """Emergency administrative override to reset a member's Two-Factor Authentication (TOTP)."""
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    return await service.reset_user_mfa(
        db=db,
        org_id=user.organizationId,
        user_id=user_id,
        actor=user,
        ip_address=ip,
        user_agent=user_agent,
    )
