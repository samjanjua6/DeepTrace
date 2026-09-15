from datetime import datetime, timezone
from fastapi import HTTPException, status
from prisma import Json, Prisma
from app.db.client import set_org_context
from app.db.enums import AuditAction

TIER_LIMITS: dict[str, int] = {
    "FREE": 100,
    "FINTECH_GROWTH": 2000,
    "BUSINESS_SCALE": 15000,
    "ENTERPRISE": 100000,
}


def _calculate_renewal(billing_cycle_start: datetime | None, created_at: datetime | None) -> tuple[int, bool]:
    now = datetime.now(timezone.utc)
    start = billing_cycle_start or created_at or now
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    elapsed_days = (now - start).days
    needs_rollover = elapsed_days >= 30
    days_until_renewal = max(0, 30 - (elapsed_days % 30))
    return days_until_renewal, needs_rollover


async def get_org(db: Prisma, org_id: str) -> dict:
    """Fetch an organization by its ID with computed usage metrics."""
    org = await db.organization.find_unique(where={"id": org_id})
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORG_NOT_FOUND", "message": "Organization not found."},
        )
    remaining_docs = max(0, org.monthlyDocLimit - org.monthlyDocUsed)
    usage_percentage = round((org.monthlyDocUsed / max(1, org.monthlyDocLimit)) * 100, 1)
    days_until_renewal, _ = _calculate_renewal(org.billingCycleStart, org.createdAt)
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "subscription_tier": str(org.subscriptionTier),
        "monthly_doc_limit": org.monthlyDocLimit,
        "monthly_doc_used": org.monthlyDocUsed,
        "remaining_docs": remaining_docs,
        "usage_percentage": usage_percentage,
        "domain": org.domain,
        "settings": org.settings if isinstance(org.settings, dict) else {},
        "billing_cycle_start": org.billingCycleStart,
        "days_until_renewal": days_until_renewal,
    }


async def update_settings(
    db: Prisma,
    org_id: str,
    data: dict,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Update organization settings with SBP audit logging."""
    update_data = {}
    if data.get("name") is not None:
        update_data["name"] = data["name"]
    if data.get("domain") is not None:
        update_data["domain"] = data["domain"]
    if data.get("settings") is not None:
        update_data["settings"] = Json(data["settings"])

    async with set_org_context(org_id) as tx:
        await tx.organization.update(
            where={"id": org_id},
            data=update_data,
        )

        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": user_id,
                    "action": AuditAction.ORGANIZATION_SETTINGS_UPDATED.value,
                    "entityType": "organization",
                    "entityId": org_id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({"updated_fields": list(update_data.keys())}),
                }
            )
        except Exception as exc:
            import logging
            logging.error("Failed to record audit log: %s", exc)

    return await get_org(db, org_id)


async def upgrade_tier(
    db: Prisma,
    org_id: str,
    target_tier: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Change organization subscription tier and adjust document limit with SBP audit trail."""
    tier_upper = target_tier.upper()
    if tier_upper not in TIER_LIMITS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_TIER", "message": f"Invalid tier. Must be one of: {list(TIER_LIMITS.keys())}"},
        )

    new_limit = TIER_LIMITS[tier_upper]
    current_org = await db.organization.find_unique(where={"id": org_id})
    if not current_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORG_NOT_FOUND", "message": "Organization not found."},
        )

    old_tier = str(current_org.subscriptionTier)

    async with set_org_context(org_id) as tx:
        await tx.organization.update(
            where={"id": org_id},
            data={
                "subscriptionTier": tier_upper,
                "monthlyDocLimit": new_limit,
            },
        )

        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": user_id,
                    "action": AuditAction.ORGANIZATION_SETTINGS_UPDATED.value,
                    "entityType": "organization",
                    "entityId": org_id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({
                        "action": "TIER_UPGRADE",
                        "old_tier": old_tier,
                        "new_tier": tier_upper,
                        "new_monthly_doc_limit": new_limit,
                    }),
                }
            )
        except Exception as exc:
            import logging
            logging.error("Failed to record upgrade_tier audit log: %s", exc)

    return await get_org(db, org_id)


async def get_usage_stats(db: Prisma, org_id: str) -> dict:
    """Compute usage stats, remaining quota, renewal countdown, and document breakdown."""
    org = await db.organization.find_unique(where={"id": org_id})
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORG_NOT_FOUND", "message": "Organization not found."},
        )

    days_until_renewal, needs_rollover = _calculate_renewal(org.billingCycleStart, org.createdAt)

    if needs_rollover:
        now = datetime.now(timezone.utc)
        await db.organization.update(
            where={"id": org_id},
            data={
                "monthlyDocUsed": 0,
                "billingCycleStart": now,
            },
        )
        org = await db.organization.find_unique(where={"id": org_id})
        days_until_renewal = 30

    remaining = max(0, org.monthlyDocLimit - org.monthlyDocUsed)
    usage_pct = round((org.monthlyDocUsed / max(1, org.monthlyDocLimit)) * 100, 1)

    # Breakdown by document type
    breakdown: dict[str, int] = {}
    try:
        async with set_org_context(org_id) as tx:
            docs = await tx.document.find_many(
                where={
                    "investigation": {"organizationId": org_id},
                    "deletedAt": None,
                },
            )
            for d in docs:
                dtype = str(d.documentType)
                breakdown[dtype] = breakdown.get(dtype, 0) + 1
    except Exception:
        pass

    return {
        "subscription_tier": str(org.subscriptionTier),
        "monthly_doc_limit": org.monthlyDocLimit,
        "monthly_doc_used": org.monthlyDocUsed,
        "remaining": remaining,
        "usage_percentage": usage_pct,
        "days_until_renewal": days_until_renewal,
        "billing_cycle_start": org.billingCycleStart,
        "document_type_breakdown": breakdown,
    }
