import logging
from datetime import datetime, timezone, timedelta
from prisma import Prisma, Json
from app.core.security import generate_api_key
from app.db.client import set_org_context
from app.db.enums import AuditAction

logger = logging.getLogger(__name__)


async def list_keys(db: Prisma, org_id: str, include_revoked: bool = False) -> list:
    async with set_org_context(org_id) as tx:
        where_clause = {"organizationId": org_id}
        if not include_revoked:
            where_clause["isActive"] = True

        records = await tx.apikey.find_many(
            where=where_clause,
            order={"createdAt": "desc"},
        )
        now = datetime.now(timezone.utc)
        result = []
        for r in records:
            is_expired = bool(r.expiresAt and r.expiresAt < now)
            result.append({
                "id": r.id,
                "name": r.name,
                "key_prefix": r.keyPrefix,
                "scopes": r.scopes,
                "is_active": r.isActive,
                "created_at": r.createdAt,
                "expires_at": r.expiresAt,
                "last_used_at": r.lastUsedAt,
                "is_expired": is_expired,
            })
        return result


async def create_key(
    db: Prisma,
    org_id: str,
    user_id: str,
    data: dict,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    plaintext, prefix, key_hash = generate_api_key()
    expires_at = data.get("expires_at")
    if not expires_at and data.get("expires_in_days"):
        expires_at = datetime.now(timezone.utc) + timedelta(days=data["expires_in_days"])

    scopes = data.get("scopes") or ["investigations:read", "investigations:write"]

    async with set_org_context(org_id) as tx:
        record = await tx.apikey.create(
            data={
                "organizationId": org_id,
                "name": data["name"],
                "keyPrefix": prefix,
                "keyHash": key_hash,
                "scopes": scopes,
                "expiresAt": expires_at,
            }
        )

        # Register immutable SBP audit log
        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": user_id,
                    "action": AuditAction.API_KEY_CREATED.value,
                    "entityType": "api_key",
                    "entityId": record.id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({
                        "key_id": record.id,
                        "key_prefix": prefix,
                        "key_name": record.name,
                        "scopes": scopes,
                        "expires_at": expires_at.isoformat() if expires_at else None,
                    }),
                }
            )
        except Exception as exc:
            logger.error("Failed to record SBP audit log for API key creation: %s", exc)
            raise exc

    return {
        "id": record.id,
        "name": record.name,
        "key_prefix": record.keyPrefix,
        "scopes": record.scopes,
        "is_active": record.isActive,
        "created_at": record.createdAt,
        "expires_at": record.expiresAt,
        "last_used_at": record.lastUsedAt,
        "is_expired": False,
        "plaintext_key": plaintext,
    }


async def revoke_key(
    db: Prisma,
    org_id: str,
    key_id: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    async with set_org_context(org_id) as tx:
        record = await tx.apikey.find_first(
            where={"id": key_id, "organizationId": org_id}
        )
        if not record:
            return

        await tx.apikey.update(
            where={"id": key_id},
            data={"isActive": False},
        )

        # Register immutable SBP audit log
        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": user_id,
                    "action": AuditAction.API_KEY_REVOKED.value,
                    "entityType": "api_key",
                    "entityId": key_id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({
                        "key_id": key_id,
                        "key_prefix": record.keyPrefix,
                        "key_name": record.name,
                    }),
                }
            )
        except Exception as exc:
            logger.error("Failed to record SBP audit log for API key revocation: %s", exc)
            raise exc

