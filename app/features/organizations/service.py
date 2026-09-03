from fastapi import HTTPException, status
from prisma import Prisma


async def get_org(db: Prisma, org_id: str) -> object:
    """Fetch an organization by its ID."""
    org = await db.organization.find_unique(where={"id": org_id})
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORG_NOT_FOUND", "message": "Organization not found."},
        )
    return org


async def update_settings(db: Prisma, org_id: str, data: dict) -> object:
    """Update organization settings."""
    update_data = {}
    if data.get("name") is not None:
        update_data["name"] = data["name"]
    if data.get("settings") is not None:
        update_data["settings"] = data["settings"]

    org = await db.organization.update(
        where={"id": org_id},
        data=update_data,
    )
    return org


async def get_usage_stats(db: Prisma, org_id: str) -> dict:
    """Compute usage stats and remaining quota for an organization."""
    org = await get_org(db, org_id)
    remaining = max(0, org.monthlyDocLimit - org.monthlyDocUsed)
    return {
        "monthly_doc_limit": org.monthlyDocLimit,
        "monthly_doc_used": org.monthlyDocUsed,
        "remaining": remaining,
        "billing_cycle_start": org.billingCycleStart,
    }
