"""
Auth service — login, token issuance, session management.
All database and business logic lives here, NOT in the router.
"""

from datetime import datetime, timezone

from prisma import Prisma

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from app.config import get_settings
from app.features.auth.exceptions import AccountLockedError, InvalidCredentialsError
from app.features.auth.schemas import TokenResponse

settings = get_settings()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 30


async def login(db: Prisma, email: str, password: str, ip_address: str | None = None) -> TokenResponse:
    """Authenticate a user and return access + refresh tokens."""
    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        user = await tx.user.find_unique(where={"email": email})

        if not user or not user.isActive:
            raise InvalidCredentialsError()

        # Check account lock
        if user.lockedUntil and user.lockedUntil > datetime.now(timezone.utc):
            raise AccountLockedError()

        if not verify_password(password, user.passwordHash):
            new_count = user.failedLoginCount + 1
            update_data: dict = {"failedLoginCount": new_count}
            if new_count >= MAX_FAILED_ATTEMPTS:
                from datetime import timedelta
                update_data["lockedUntil"] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
            await tx.user.update(where={"id": user.id}, data=update_data)
            raise InvalidCredentialsError()

        # Reset failure counter on success
        await tx.user.update(
            where={"id": user.id},
            data={"failedLoginCount": 0, "lockedUntil": None, "lastLoginAt": datetime.now(timezone.utc)},
        )

        # Issue tokens
        extra_claims = {"org": user.organizationId, "role": user.role}
        access_token = create_access_token(subject=user.id, extra_claims=extra_claims)
        refresh_token = create_refresh_token(subject=user.id)

        # Persist session
        import secrets
        raw_session_token = secrets.token_urlsafe(48)
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
        await tx.usersession.create(data={
            "userId": user.id,
            "tokenHash": hash_token(raw_session_token),
            "ipAddress": ip_address,
            "expiresAt": expires_at,
        })

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )


async def logout(db: Prisma, token_hash: str) -> None:
    """Revoke a session by its token hash."""
    from datetime import datetime, timezone
    await db.usersession.update_many(
        where={"tokenHash": token_hash},
        data={"revokedAt": datetime.now(timezone.utc)},
    )
