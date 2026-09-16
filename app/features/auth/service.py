"""
Auth service — login, token issuance, session management, MFA, and multi-tenancy.
All database and business logic lives here, NOT in the router.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError
from prisma import Prisma

from app.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from app.core.totp import generate_totp_secret, generate_totp_uri, verify_totp
from app.db.enums import AuditAction
from app.features.auth import schemas
from app.features.auth.exceptions import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidMfaCodeError,
    InvalidRefreshTokenError,
    OrganizationNotFoundError,
    SessionBreachDetectedError,
    TokenExpiredError,
)

settings = get_settings()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 30


async def _record_audit_log(
    db: Prisma,
    organization_id: str,
    action: AuditAction,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Helper to record immutable audit log entries in compliance with SBP regulations."""
    if not organization_id:
        return
    try:
        from prisma import Json
        async with db.tx() as audit_tx:
            await audit_tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
            await audit_tx.execute_raw(f"SELECT set_config('app.current_org_id', '{organization_id}', true);")
            await audit_tx.auditlog.create(
                data={
                    "organizationId": organization_id,
                    "userId": user_id,
                    "action": action.value if hasattr(action, "value") else str(action),
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json(metadata) if metadata else None,
                }
            )
    except Exception:
        pass


async def login(
    db: Prisma,
    email: str,
    password: str,
    mfa_code: str | None = None,
    remember_me: bool = False,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> schemas.TokenResponse:
    """Authenticate a user and return access + refresh tokens, or an MFA challenge."""
    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        user = await tx.user.find_unique(where={"email": email}, include={"organization": True})

        if not user or not user.isActive:
            raise InvalidCredentialsError()

        # Check account lock
        if user.lockedUntil and user.lockedUntil > datetime.now(timezone.utc):
            raise AccountLockedError()

        # Verify password
        if not verify_password(password, user.passwordHash):
            new_count = user.failedLoginCount + 1
            update_data: dict = {"failedLoginCount": new_count}
            if new_count >= MAX_FAILED_ATTEMPTS:
                lock_time = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
                update_data["lockedUntil"] = lock_time
                await tx.user.update(where={"id": user.id}, data=update_data)
                await _record_audit_log(
                    db,
                    organization_id=user.organizationId,
                    action=AuditAction.USER_ACCOUNT_LOCKED,
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"reason": "MAX_FAILED_ATTEMPTS_EXCEEDED", "failed_count": new_count},
                )
            else:
                await tx.user.update(where={"id": user.id}, data=update_data)
                await _record_audit_log(
                    db,
                    organization_id=user.organizationId,
                    action=AuditAction.USER_LOGIN_FAILED,
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"failed_count": new_count},
                )
            raise InvalidCredentialsError()

        # Check MFA requirement
        if user.mfaEnabled:
            if not mfa_code:
                # Issue short-lived temporary token for 2FA completion
                temp_token = create_access_token(
                    subject=user.id,
                    extra_claims={"type": "mfa_pending", "org": user.organizationId, "remember_me": remember_me},
                )
                return schemas.TokenResponse(
                    mfa_required=True,
                    temp_token=temp_token,
                    message="Institutional two-factor authentication code required.",
                )

            # Verify TOTP code
            if not verify_totp(user.mfaSecret, mfa_code):
                new_count = user.failedLoginCount + 1
                await tx.user.update(where={"id": user.id}, data={"failedLoginCount": new_count})
                await _record_audit_log(
                    db,
                    organization_id=user.organizationId,
                    action=AuditAction.USER_LOGIN_FAILED,
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"reason": "INVALID_MFA_CODE"},
                )
                raise InvalidMfaCodeError()

        # Reset failure counter on success
        await tx.user.update(
            where={"id": user.id},
            data={"failedLoginCount": 0, "lockedUntil": None, "lastLoginAt": datetime.now(timezone.utc)},
        )

        # Issue tokens
        extra_claims = {"org": user.organizationId, "role": user.role}
        access_token = create_access_token(subject=user.id, extra_claims=extra_claims)
        refresh_token = create_refresh_token(subject=user.id)

        # Persist session with hash of refresh token (30-day for remember_me, 24-hr for transient)
        session_days = settings.jwt_refresh_token_expire_days if remember_me else 1
        expires_at = datetime.now(timezone.utc) + timedelta(days=session_days)
        await tx.usersession.create(
            data={
                "userId": user.id,
                "tokenHash": hash_token(refresh_token),
                "ipAddress": ip_address,
                "userAgent": user_agent,
                "expiresAt": expires_at,
            }
        )

    # Audit log login success (outside core transaction)
    await _record_audit_log(
        db,
        organization_id=user.organizationId,
        action=AuditAction.USER_LOGIN,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"mfa_used": bool(user.mfaEnabled and mfa_code)},
    )

    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


async def verify_mfa_login(
    db: Prisma,
    temp_token: str,
    mfa_code: str,
    remember_me: bool = False,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> schemas.TokenResponse:
    """Verify an MFA code using a temporary pending token, completing authentication."""
    try:
        payload = decode_token(temp_token)
        if payload.get("type") != "mfa_pending":
            raise InvalidMfaCodeError()
        user_id: str = payload["sub"]
        if not remember_me and payload.get("remember_me"):
            remember_me = True
    except (JWTError, KeyError):
        raise TokenExpiredError()

    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        user = await tx.user.find_unique(where={"id": user_id})

        if not user or not user.isActive:
            raise InvalidCredentialsError()

        if user.lockedUntil and user.lockedUntil > datetime.now(timezone.utc):
            raise AccountLockedError()

        if not verify_totp(user.mfaSecret, mfa_code):
            new_count = user.failedLoginCount + 1
            update_data: dict = {"failedLoginCount": new_count}
            if new_count >= MAX_FAILED_ATTEMPTS:
                lock_time = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
                update_data["lockedUntil"] = lock_time
                await tx.user.update(where={"id": user.id}, data=update_data)
                await _record_audit_log(
                    db,
                    organization_id=user.organizationId,
                    action=AuditAction.USER_ACCOUNT_LOCKED,
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"reason": "MFA_VERIFY_MAX_ATTEMPTS"},
                )
            else:
                await tx.user.update(where={"id": user.id}, data=update_data)
                await _record_audit_log(
                    db,
                    organization_id=user.organizationId,
                    action=AuditAction.USER_LOGIN_FAILED,
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"reason": "INVALID_MFA_CODE"},
                )
            raise InvalidMfaCodeError()

        # Reset counters on success
        await tx.user.update(
            where={"id": user.id},
            data={"failedLoginCount": 0, "lockedUntil": None, "lastLoginAt": datetime.now(timezone.utc)},
        )

        # Issue tokens
        extra_claims = {"org": user.organizationId, "role": user.role}
        access_token = create_access_token(subject=user.id, extra_claims=extra_claims)
        refresh_token = create_refresh_token(subject=user.id)

        # Persist session (30-day for remember_me, 24-hr for transient)
        session_days = settings.jwt_refresh_token_expire_days if remember_me else 1
        expires_at = datetime.now(timezone.utc) + timedelta(days=session_days)
        await tx.usersession.create(
            data={
                "userId": user.id,
                "tokenHash": hash_token(refresh_token),
                "ipAddress": ip_address,
                "userAgent": user_agent,
                "expiresAt": expires_at,
            }
        )

    await _record_audit_log(
        db,
        organization_id=user.organizationId,
        action=AuditAction.USER_LOGIN,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"mfa_verified": True},
    )

    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


async def refresh_tokens(
    db: Prisma,
    refresh_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> schemas.TokenResponse:
    """Execute single-use refresh token rotation with RFC 6819 breach detection."""
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise InvalidRefreshTokenError()
        user_id: str = payload["sub"]
    except (JWTError, KeyError):
        raise InvalidRefreshTokenError()

    token_h = hash_token(refresh_token)

    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        session = await tx.usersession.find_unique(where={"tokenHash": token_h})

        if not session:
            raise InvalidRefreshTokenError()

        # Breach Detection: Session was already revoked!
        if session.revokedAt is not None:
            # Emergency revocation of ALL active sessions for this compromised user
            await tx.usersession.update_many(
                where={"userId": user_id, "revokedAt": None},
                data={"revokedAt": datetime.now(timezone.utc)},
            )
            u = await tx.user.find_unique(where={"id": user_id})
            if u:
                await _record_audit_log(
                    db,
                    organization_id=u.organizationId,
                    action=AuditAction.USER_ACCOUNT_LOCKED,
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"reason": "REFRESH_TOKEN_REUSE_BREACH_DETECTED"},
                )
            raise SessionBreachDetectedError()

        # Check session expiry
        if session.expiresAt <= datetime.now(timezone.utc):
            await tx.usersession.update(
                where={"id": session.id},
                data={"revokedAt": datetime.now(timezone.utc)},
            )
            raise InvalidRefreshTokenError()

        # Fetch active user
        user = await tx.user.find_unique(where={"id": user_id})
        if not user or not user.isActive:
            raise InvalidCredentialsError()

        # Invalidate current session (single-use rotation)
        await tx.usersession.update(
            where={"id": session.id},
            data={"revokedAt": datetime.now(timezone.utc)},
        )

        # Issue fresh token pair
        extra_claims = {"org": user.organizationId, "role": user.role}
        new_access_token = create_access_token(subject=user.id, extra_claims=extra_claims)
        new_refresh_token = create_refresh_token(subject=user.id)

        # Record new session
        new_expires = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
        await tx.usersession.create(
            data={
                "userId": user.id,
                "tokenHash": hash_token(new_refresh_token),
                "ipAddress": ip_address,
                "userAgent": user_agent,
                "expiresAt": new_expires,
            }
        )

        return schemas.TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )


async def logout(
    db: Prisma,
    refresh_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Revoke a user session by refresh token and record logout audit log."""
    token_h = hash_token(refresh_token)
    user_org_id = None
    user_id = None
    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        session = await tx.usersession.find_unique(where={"tokenHash": token_h})
        now = datetime.now(timezone.utc)
        if session:
            await tx.usersession.update(
                where={"id": session.id},
                data={"revokedAt": now},
            )
            u = await tx.user.find_unique(where={"id": session.userId})
            if u:
                user_org_id = u.organizationId
                user_id = u.id
        else:
            await tx.usersession.update_many(
                where={"tokenHash": token_h},
                data={"revokedAt": now},
            )

    if user_org_id:
        await _record_audit_log(
            db,
            organization_id=user_org_id,
            action=AuditAction.USER_LOGOUT,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )


async def setup_mfa(db: Prisma, user_id: str) -> schemas.MfaSetupResponse:
    """Generate a new Base32 TOTP secret and enrollment URI for the user."""
    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        user = await tx.user.find_unique(where={"id": user_id})
        if not user:
            raise InvalidCredentialsError()

        secret = generate_totp_secret()
        uri = generate_totp_uri(secret, email=user.email, issuer="DeepTrace")
        return schemas.MfaSetupResponse(secret=secret, otpauth_uri=uri)


async def enable_mfa(
    db: Prisma,
    user_id: str,
    secret: str,
    code: str,
    ip_address: str | None = None,
) -> None:
    """Verify code against proposed secret, persist secret, and enable MFA."""
    if not verify_totp(secret, code):
        raise InvalidMfaCodeError()

    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        user = await tx.user.find_unique(where={"id": user_id})
        if not user:
            raise InvalidCredentialsError()

        await tx.user.update(
            where={"id": user_id},
            data={"mfaSecret": secret, "mfaEnabled": True},
        )

    await _record_audit_log(
        db,
        organization_id=user.organizationId,
        action=AuditAction.USER_MFA_ENABLED,
        user_id=user.id,
        ip_address=ip_address,
    )


async def disable_mfa(
    db: Prisma,
    user_id: str,
    password: str,
    code: str,
    ip_address: str | None = None,
) -> None:
    """Disable MFA after verifying account password and active TOTP code."""
    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        user = await tx.user.find_unique(where={"id": user_id})
        if not user or not user.isActive:
            raise InvalidCredentialsError()

        if not verify_password(password, user.passwordHash):
            raise InvalidCredentialsError()

        if not verify_totp(user.mfaSecret, code):
            raise InvalidMfaCodeError()

        await tx.user.update(
            where={"id": user_id},
            data={"mfaSecret": None, "mfaEnabled": False},
        )

    await _record_audit_log(
        db,
        organization_id=user.organizationId,
        action=AuditAction.USER_MFA_DISABLED,
        user_id=user.id,
        ip_address=ip_address,
    )


async def list_organizations(db: Prisma, current_user) -> list[schemas.OrganizationOption]:
    """List available banking organizations for multi-tenant switching."""
    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        orgs = await tx.organization.find_many(
            where={"isActive": True},
            order={"name": "asc"},
        )
        return [
            schemas.OrganizationOption(
                id=o.id,
                name=o.name,
                slug=o.slug,
                domain=o.domain,
                subscription_tier=o.subscriptionTier,
            )
            for o in orgs
        ]


async def switch_organization(
    db: Prisma,
    current_user,
    organization_id: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> schemas.SwitchOrgResponse:
    """Switch user's active banking organization and issue updated JWT."""
    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        target_org = await tx.organization.find_unique(where={"id": organization_id})
        if not target_org or not target_org.isActive:
            raise OrganizationNotFoundError()

        # Update user's active organizationId
        await tx.user.update(
            where={"id": current_user.id},
            data={"organizationId": target_org.id},
        )

        # Issue newly scoped access token
        extra_claims = {"org": target_org.id, "role": current_user.role}
        new_access = create_access_token(subject=current_user.id, extra_claims=extra_claims)
        new_refresh = create_refresh_token(subject=current_user.id)

        # Record new session
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
        await tx.usersession.create(
            data={
                "userId": current_user.id,
                "tokenHash": hash_token(new_refresh),
                "ipAddress": ip_address,
                "userAgent": user_agent,
                "expiresAt": expires_at,
            }
        )

        return schemas.SwitchOrgResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            organization=schemas.OrganizationOption(
                id=target_org.id,
                name=target_org.name,
                slug=target_org.slug,
                domain=target_org.domain,
                subscription_tier=target_org.subscriptionTier,
            ),
        )


def get_sso_providers() -> list[schemas.SsoProviderOption]:
    """Return available enterprise SSO identity providers."""
    return [
        schemas.SsoProviderOption(
            id="azure_ad",
            name="Microsoft Entra ID (Azure AD)",
            protocol="SAML 2.0 / OIDC",
            description="Integrated Azure Active Directory for core banking & sovereign cloud deployments.",
        ),
        schemas.SsoProviderOption(
            id="okta",
            name="Okta Identity Cloud",
            protocol="OIDC / SAML 2.0",
            description="Enterprise workforce identity federation with automated SCIM provisioning.",
        ),
        schemas.SsoProviderOption(
            id="saml",
            name="Institutional SAML 2.0 / ADFS",
            protocol="SAML 2.0",
            description="Direct Shibboleth, PingFederate, or Active Directory Federation Services connector.",
        ),
    ]


def initiate_sso(
    provider: str,
    tenant_domain: str | None = None,
    redirect_uri: str | None = "/investigations",
) -> schemas.SsoInitiateResponse:
    """Initiate enterprise SSO federation and generate provider metadata."""
    entity_id = "https://auth.deeptrace.internal/saml/metadata"

    if provider == "okta":
        sso_url = f"https://identity.bank.internal/app/deeptrace/{tenant_domain or 'enterprise'}/sso/saml"
        protocol = "SAML 2.0 / OIDC"
        msg = "Redirecting to Okta Enterprise Identity Provider."
    elif provider == "saml":
        sso_url = f"https://adfs.bank.internal/adfs/ls/?wa=wsignin1.0&wtrealm={entity_id}"
        protocol = "SAML 2.0"
        msg = "Redirecting to Institutional SAML 2.0 / ADFS Endpoint."
    else:  # azure_ad default
        sso_url = f"https://login.microsoftonline.com/{tenant_domain or 'organizations'}/saml2"
        protocol = "SAML 2.0 / WS-Fed"
        msg = "Redirecting to Microsoft Entra ID (Azure AD) Institutional Gateway."

    return schemas.SsoInitiateResponse(
        provider=provider,
        sso_url=sso_url,
        entity_id=entity_id,
        protocol=protocol,
        message=msg,
    )
