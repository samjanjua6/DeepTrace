from datetime import datetime, timezone
from prisma import Prisma
from app.core.security import generate_api_key
from app.db.client import set_org_context


async def list_keys(db: Prisma, org_id: str) -> list:
    async with set_org_context(org_id) as tx:
        return await tx.apikey.find_many(
            where={"organizationId": org_id, "isActive": True},
            order={"createdAt": "desc"},
        )


async def create_key(db: Prisma, org_id: str, user_id: str, data: dict) -> dict:
    plaintext, prefix, key_hash = generate_api_key()
    async with set_org_context(org_id) as tx:
        record = await tx.apikey.create(
            data={
                "organizationId": org_id,
                "name": data["name"],
                "keyPrefix": prefix,
                "keyHash": key_hash,
                "scopes": data.get("scopes", ["read", "write"]),
                "expiresAt": data.get("expires_at"),
            }
        )
    return {
        "id": record.id,
        "name": record.name,
        "key_prefix": record.keyPrefix,
        "scopes": record.scopes,
        "is_active": record.isActive,
        "created_at": record.createdAt,
        "expires_at": record.expiresAt,
        "last_used_at": record.lastUsedAt,
        "plaintext_key": plaintext,
    }


async def revoke_key(db: Prisma, org_id: str, key_id: str) -> None:
    async with set_org_context(org_id) as tx:
        await tx.apikey.update(
            where={"id": key_id},
            data={"isActive": False},
        )
