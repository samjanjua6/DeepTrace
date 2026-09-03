"""
Investigations dependencies — FastAPI Depends() factories.
"""
from fastapi import Depends, HTTPException, status
from prisma import Prisma

from app.db.client import get_db_dep, set_org_context
from app.features.auth.dependencies import get_current_user


async def get_investigation(
    investigation_id: str,
    db: Prisma = Depends(get_db_dep),
    user=Depends(get_current_user),
):
    """Fetch an investigation by ID within the tenant RLS context."""
    async with set_org_context(user.organizationId) as tx:
        investigation = await tx.investigation.find_unique(
            where={"id": investigation_id}
        )
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Investigation not found."},
        )
    if investigation.organizationId != user.organizationId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Access denied."},
        )
    return investigation
