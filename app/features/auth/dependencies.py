"""
Auth dependencies — FastAPI Depends() factories.
Import `CurrentUser` or `require_role` in any feature router.
"""

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from prisma import Prisma

from app.db.client import get_db_dep
from app.db.enums import UserRole
from app.features.auth.exceptions import InsufficientPermissionsError, TokenExpiredError

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[Prisma, Depends(get_db_dep)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)] = None,
):
    """Extract and validate the current user from the Bearer token.

    Raises TokenExpiredError if token is invalid/expired.
    Returns the Prisma User model.
    """
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
        user = await tx.user.find_unique(where={"id": user_id})
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
