"""Webhooks service. TODO: Implement."""
import hashlib, hmac, json
from prisma import Prisma

def sign_payload(secret: str, payload: dict) -> str:
    """Generate HMAC-SHA256 signature for a webhook payload."""
    body = json.dumps(payload, separators=(",", ":")).encode()
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

async def create_endpoint(db: Prisma, org_id: str, url: str, events: list, description: str | None) -> object:
    # TODO: db.webhookendpoint.create(...)
    raise NotImplementedError

async def list_endpoints(db: Prisma, org_id: str) -> list:
    # TODO: db.webhookendpoint.find_many(where={"organizationId": org_id})
    raise NotImplementedError

async def delete_endpoint(db: Prisma, endpoint_id: str) -> None:
    # TODO: db.webhookendpoint.update(where={"id": endpoint_id}, data={"isActive": False})
    raise NotImplementedError

async def dispatch_event(db: Prisma, org_id: str, event_type: str, payload: dict) -> None:
    """Find active endpoints subscribed to event_type and enqueue delivery tasks."""
    # TODO: find matching endpoints, for each: webhooks.tasks.deliver_webhook_event.delay(...)
    raise NotImplementedError
