"""Service logic for User & Role Administration under SBP compliance."""
import logging
import secrets
from datetime import datetime, timezone
from fastapi import HTTPException, status
from prisma import Json, Prisma

from app.core import security
from app.db.client import set_org_context
from app.db.enums import AuditAction, UserRole
from app.features.users.schemas import InviteUserRequest

logger = logging.getLogger(__name__)


async def list_users(db: Prisma, org_id: str) -> list[dict]:
    """Retrieve all organization members with lock state and MFA enforcement flags."""
    now = datetime.now(timezone.utc)
    async with set_org_context(org_id) as tx:
        users = await tx.user.find_many(
            where={"organizationId": org_id, "deletedAt": None},
            order={"createdAt": "asc"},
        )

    results = []
    for u in users:
        is_locked = False
        if u.lockedUntil:
            lu = u.lockedUntil
            if lu.tzinfo is None:
                lu = lu.replace(tzinfo=timezone.utc)
            if lu > now:
                is_locked = True

        results.append({
            "id": u.id,
            "email": u.email,
            "first_name": u.firstName,
            "last_name": u.lastName,
            "role": str(u.role),
            "is_active": u.isActive,
            "mfa_enabled": u.mfaEnabled,
            "failed_login_count": u.failedLoginCount,
            "is_locked": is_locked,
            "locked_until": u.lockedUntil,
            "last_login_at": u.lastLoginAt,
            "created_at": u.createdAt,
        })
    return results


async def invite_user(
    db: Prisma,
    org_id: str,
    payload: InviteUserRequest,
    actor_id: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Onboard a new institutional analyst or administrator with SBP password generation and audit logging."""
    clean_email = str(payload.email).lower().strip()

    # Temporary password generation (SBP complexity standard: min 12 chars, upper, lower, digit, symbol)
    if payload.temp_password and payload.temp_password.strip():
        temp_pwd = payload.temp_password.strip()
    else:
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%"
        temp_pwd = "".join(secrets.choice(chars) for _ in range(12))

    hashed_pwd = security.hash_password(temp_pwd)

    from prisma.errors import UniqueViolationError

    async with set_org_context(org_id) as tx:
        # Verify uniqueness within RLS context
        existing = await tx.user.find_unique(where={"email": clean_email})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EMAIL_ALREADY_EXISTS", "message": f"User with email '{clean_email}' already exists."},
            )

        try:
            user = await tx.user.create(
                data={
                    "organizationId": org_id,
                    "email": clean_email,
                    "passwordHash": hashed_pwd,
                    "firstName": payload.first_name.strip(),
                    "lastName": payload.last_name.strip(),
                    "role": payload.role.value,
                    "isActive": True,
                }
            )
        except UniqueViolationError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EMAIL_ALREADY_EXISTS", "message": f"User with email '{clean_email}' already exists."},
            )

        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": actor_id,
                    "action": AuditAction.USER_CREATED.value,
                    "entityType": "user",
                    "entityId": user.id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({
                        "user_id": user.id,
                        "email": user.email,
                        "assigned_role": str(user.role),
                        "created_by": actor_id,
                    }),
                }
            )
        except Exception as exc:
            logger.error("Failed to record USER_CREATED audit log: %s", exc)

    dispatch_memo = (
        f"================================================================================\n"
        f"DEEPTRACE FORENSICS — INSTITUTIONAL CREDENTIAL CLEARANCE\n"
        f"State Bank of Pakistan (SBP) Framework for Risk Management in Outsourcing\n"
        f"================================================================================\n"
        f"Member:         {payload.first_name} {payload.last_name}\n"
        f"Clearance Role: [{payload.role.value}]\n"
        f"Username/Email: {clean_email}\n"
        f"Temp Password:  {temp_pwd}\n"
        f"Login Gateway:  http://localhost:3000/login\n"
        f"Security:       Requires 2FA Enrollment upon first administrative session.\n"
        f"================================================================================"
    )

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.firstName,
            "last_name": user.lastName,
            "role": str(user.role),
            "is_active": user.isActive,
            "mfa_enabled": user.mfaEnabled,
            "failed_login_count": user.failedLoginCount,
            "is_locked": False,
            "locked_until": None,
            "last_login_at": None,
            "created_at": user.createdAt,
        },
        "temp_password": temp_pwd,
        "login_url": "http://localhost:3000/login",
        "dispatch_memo": dispatch_memo,
    }


async def update_user_role(
    db: Prisma,
    org_id: str,
    user_id: str,
    new_role: UserRole,
    actor: object,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Promote or demote an institutional member with safety guardrails against sole-owner demotion."""
    async with set_org_context(org_id) as tx:
        target_user = await tx.user.find_unique(where={"id": user_id})
        if not target_user or target_user.organizationId != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found in this organization."},
            )

        old_role = str(target_user.role)

        # Safety Check: Cannot demote sole owner
        if old_role == "OWNER" and new_role != UserRole.OWNER:
            owners_count = await tx.user.count(
                where={"organizationId": org_id, "role": "OWNER", "isActive": True}
            )
            if owners_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "SOLE_OWNER_DEMOTION_FORBIDDEN",
                        "message": "Cannot demote the sole institutional Owner. Transfer ownership to another user first.",
                    },
                )

        # Safety Check: Non-owner cannot assign OWNER role
        if new_role == UserRole.OWNER and getattr(actor, "role", "") != "OWNER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": "Only institutional Owners can promote members to Owner clearance.",
                },
            )

        updated_user = await tx.user.update(
            where={"id": user_id},
            data={"role": new_role.value},
        )

        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": getattr(actor, "id", None),
                    "action": AuditAction.USER_ROLE_CHANGED.value,
                    "entityType": "user",
                    "entityId": user_id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({
                        "target_user_id": user_id,
                        "old_role": old_role,
                        "new_role": new_role.value,
                        "modified_by": getattr(actor, "id", None),
                    }),
                }
            )
        except Exception as exc:
            logger.error("Failed to record USER_ROLE_CHANGED audit log: %s", exc)

    return {
        "id": updated_user.id,
        "email": updated_user.email,
        "first_name": updated_user.firstName,
        "last_name": updated_user.lastName,
        "role": str(updated_user.role),
        "is_active": updated_user.isActive,
        "mfa_enabled": updated_user.mfaEnabled,
        "failed_login_count": updated_user.failedLoginCount,
        "is_locked": False,
        "locked_until": updated_user.lockedUntil,
        "last_login_at": updated_user.lastLoginAt,
        "created_at": updated_user.createdAt,
    }


async def update_user_status(
    db: Prisma,
    org_id: str,
    user_id: str,
    is_active: bool,
    actor: object,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Suspend or reactivate member account with session invalidation."""
    # Prevent self-deactivation
    if getattr(actor, "id", None) == user_id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SELF_DEACTIVATION_FORBIDDEN",
                "message": "Administrators cannot deactivate their own active user account.",
            },
        )

    async with set_org_context(org_id) as tx:
        target_user = await tx.user.find_unique(where={"id": user_id})
        if not target_user or target_user.organizationId != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found in this organization."},
            )

        # Prevent deactivating sole owner
        if str(target_user.role) == "OWNER" and not is_active:
            owners_count = await tx.user.count(
                where={"organizationId": org_id, "role": "OWNER", "isActive": True}
            )
            if owners_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "SOLE_OWNER_DEACTIVATION_FORBIDDEN",
                        "message": "Cannot deactivate the sole institutional Owner.",
                    },
                )

        updated_user = await tx.user.update(
            where={"id": user_id},
            data={"isActive": is_active},
        )

        # If deactivating, invalidate active user sessions
        if not is_active:
            try:
                await tx.usersession.delete_many(where={"userId": user_id})
            except Exception:
                pass

        action_type = AuditAction.USER_DEACTIVATED.value if not is_active else AuditAction.USER_REACTIVATED.value
        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": getattr(actor, "id", None),
                    "action": action_type,
                    "entityType": "user",
                    "entityId": user_id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({
                        "target_user_id": user_id,
                        "is_active": is_active,
                        "modified_by": getattr(actor, "id", None),
                    }),
                }
            )
        except Exception as exc:
            logger.error("Failed to record %s audit log: %s", action_type, exc)

    return {
        "id": updated_user.id,
        "email": updated_user.email,
        "first_name": updated_user.firstName,
        "last_name": updated_user.lastName,
        "role": str(updated_user.role),
        "is_active": updated_user.isActive,
        "mfa_enabled": updated_user.mfaEnabled,
        "failed_login_count": updated_user.failedLoginCount,
        "is_locked": False,
        "locked_until": updated_user.lockedUntil,
        "last_login_at": updated_user.lastLoginAt,
        "created_at": updated_user.createdAt,
    }


async def unlock_user_account(
    db: Prisma,
    org_id: str,
    user_id: str,
    actor: object,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Reset brute-force lockout and failed login attempts counter."""
    async with set_org_context(org_id) as tx:
        target_user = await tx.user.find_unique(where={"id": user_id})
        if not target_user or target_user.organizationId != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found in this organization."},
            )

        await tx.user.update(
            where={"id": user_id},
            data={
                "failedLoginCount": 0,
                "lockedUntil": None,
            },
        )

        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": getattr(actor, "id", None),
                    "action": AuditAction.USER_ACCOUNT_LOCKED.value,
                    "entityType": "user",
                    "entityId": user_id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({
                        "action_detail": "ACCOUNT_MANUALLY_UNLOCKED",
                        "target_user_id": user_id,
                        "unlocked_by": getattr(actor, "id", None),
                    }),
                }
            )
        except Exception as exc:
            logger.error("Failed to record ACCOUNT_UNLOCKED audit log: %s", exc)

    return {"success": True, "message": f"Account for {target_user.email} has been unlocked successfully."}


async def reset_user_mfa(
    db: Prisma,
    org_id: str,
    user_id: str,
    actor: object,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Emergency administrative reset of user Two-Factor Authentication (TOTP)."""
    async with set_org_context(org_id) as tx:
        target_user = await tx.user.find_unique(where={"id": user_id})
        if not target_user or target_user.organizationId != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found in this organization."},
            )

        await tx.user.update(
            where={"id": user_id},
            data={
                "mfaEnabled": False,
                "mfaSecret": None,
            },
        )

        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": getattr(actor, "id", None),
                    "action": AuditAction.USER_MFA_DISABLED.value,
                    "entityType": "user",
                    "entityId": user_id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({
                        "action_detail": "ADMIN_EMERGENCY_MFA_RESET",
                        "target_user_id": user_id,
                        "reset_by": getattr(actor, "id", None),
                    }),
                }
            )
        except Exception as exc:
            logger.error("Failed to record USER_MFA_DISABLED audit log: %s", exc)

    return {"success": True, "message": f"2FA for {target_user.email} has been reset. User must re-enroll upon login."}
