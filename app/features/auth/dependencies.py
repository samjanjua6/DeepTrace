"""
Auth dependencies — FastAPI Depends() factories.
Import `CurrentUser` or `require_role` in any feature router.
"""

from typing import Annotated

import hashlib
from datetime import datetime, timezone
from fastapi import Depends, Security, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from prisma import Prisma

from app.config import get_settings
from app.db.client import get_db_dep
from app.db.enums import UserRole
from app.features.auth.exceptions import InsufficientPermissionsError, TokenExpiredError

bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()


async def get_current_user(
    request: Request,
    db: Annotated[Prisma, Depends(get_db_dep)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)] = None,
):
    """Extract and validate the current user from Bearer JWT token OR X-API-Key credential.

    Raises TokenExpiredError if token/key is invalid or expired.
    Returns the authenticated Prisma User model.
    """
    # 1. Check for programmatic machine-to-machine API Key
    api_key_val = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if not api_key_val and credentials and credentials.credentials.startswith(settings.api_key_prefix):
        api_key_val = credentials.credentials

    if api_key_val:
        raw_key = api_key_val.strip()
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        async with db.tx() as tx:
            await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
            orgs = await tx.organization.find_many()
            api_key = None
            for org in orgs:
                await tx.execute_raw("SELECT set_config('app.current_org_id', $1, true);", org.id)
                found = await tx.apikey.find_first(
                    where={"keyHash": key_hash, "isActive": True},
                    include={"organization": True},
                )
                if found:
                    api_key = found
                    break

            if not api_key:
                raise TokenExpiredError()

            if api_key.expiresAt and api_key.expiresAt < datetime.now(timezone.utc):
                raise TokenExpiredError()

            # Record programmatic lastUsedAt timestamp
            await tx.apikey.update(
                where={"id": api_key.id},
                data={"lastUsedAt": datetime.now(timezone.utc)},
            )

            # Associate with active organization identity
            user = await tx.user.find_first(
                where={"organizationId": api_key.organizationId, "isActive": True},
                include={"organization": True},
            )
            if not user:
                raise TokenExpiredError()

            return user

    # 2. Standard JWT Bearer token authentication
    if not credentials:
        raise TokenExpiredError()

    from app.core.security import decode_token
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload["sub"]
    except (JWTError, KeyError):
        raise TokenExpiredError()

    async with db.tx() as tx:
        await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
        user = await tx.user.find_unique(where={"id": user_id}, include={"organization": True})
        if not user or not user.isActive:
            raise TokenExpiredError()
        return user


def require_role(*roles: UserRole):
    """Dependency factory: restrict endpoint to users with specific roles.

    Usage:
        @router.get("/admin-only")
        async def admin_route(user = Depends(require_role(UserRole.ADMIN, UserRole.OWNER))):
            ...
    """
    async def _check(user=Depends(get_current_user)):
        if user.role not in [r.value for r in roles]:
            raise InsufficientPermissionsError(required_role=", ".join(r.value for r in roles))
        return user
    return _check


# Convenient type alias for common use
CurrentUser = Annotated[object, Depends(get_current_user)]
