import asyncio
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import secrets
import socket
import time
from urllib.parse import urlparse
from prisma import Json, Prisma

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_last_broker_check_time: float = 0.0
_broker_available: bool | None = None


def _is_celery_broker_available() -> bool:
    global _last_broker_check_time, _broker_available
    now = time.time()
    if _broker_available is not None and (now - _last_broker_check_time < 15.0):
        return _broker_available
    try:
        parsed = urlparse(settings.celery_broker_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        s = socket.create_connection((host, port), timeout=0.05)
        s.close()
        _broker_available = True
    except Exception:
        _broker_available = False
    _last_broker_check_time = now
    return _broker_available


def sign_payload(secret: str, payload: dict, timestamp: int | None = None) -> str:
    """
    Generate Stripe-standard timestamped HMAC-SHA256 signature for a webhook payload.
    Header format: t={timestamp},v1={hex_signature}
    """
    ts = timestamp if timestamp is not None else int(time.time())
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    to_sign = f"{ts}.{body}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def verify_signature(secret: str, payload: dict, header: str, tolerance_seconds: int = 300) -> bool:
    """Verify an incoming or outgoing webhook signature."""
    try:
        parts = dict(item.split("=", 1) for item in header.split(","))
        ts = int(parts["t"])
        v1 = parts["v1"]

        # Check timestamp tolerance
        if abs(int(time.time()) - ts) > tolerance_seconds:
            return False

        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        to_sign = f"{ts}.{body}".encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        return hmac.compare_digest(v1, expected)
    except Exception:
        return False


async def create_endpoint(
    db: Prisma, org_id: str, url: str, events: list[str], description: str | None = None
) -> object:
    """Create a new WebhookEndpoint with an auto-generated cryptographically secure secret."""
    secret = secrets.token_hex(32)
    endpoint = await db.webhookendpoint.create(
        data={
            "organizationId": org_id,
            "url": str(url),
            "secret": secret,
            "events": events,
            "description": description,
            "isActive": True,
        }
    )
    return endpoint


async def list_endpoints(db: Prisma, org_id: str) -> list:
    """List all active webhook endpoints for an organization."""
    return await db.webhookendpoint.find_many(
        where={"organizationId": org_id, "isActive": True},
        order={"createdAt": "desc"},
    )


async def delete_endpoint(db: Prisma, endpoint_id: str) -> None:
    """Soft-delete an endpoint by setting isActive=False."""
    await db.webhookendpoint.update(
        where={"id": endpoint_id},
        data={"isActive": False, "disabledAt": datetime.now(timezone.utc)},
    )


async def dispatch_event(
    db: Prisma,
    org_id: str,
    event_type: str,
    payload: dict,
    enqueue_tasks: bool = True,
) -> list[str]:
    """
    Find active endpoints subscribed to event_type and enqueue delivery tasks.
    Supports wildcard subscription ('*') and specific event types.
    """
    endpoints = await db.webhookendpoint.find_many(
        where={"organizationId": org_id, "isActive": True}
    )
    matching_endpoints = [
        ep for ep in endpoints
        if "*" in ep.events or event_type in ep.events
    ]

    delivery_ids = []
    for ep in matching_endpoints:
        delivery = await db.webhookdelivery.create(
            data={
                "webhookEndpointId": ep.id,
                "eventType": event_type,
                "payload": Json(payload),
                "attempt": 1,
                "maxAttempts": 3,
            }
        )
        delivery_ids.append(delivery.id)

        # Enqueue Celery task if broker is reachable
        if enqueue_tasks and _is_celery_broker_available():
            try:
                from app.features.webhooks.tasks import deliver_webhook_event
                deliver_webhook_event.apply_async(args=[delivery.id, org_id], retry=False, ignore_result=True)
            except Exception as exc:
                logger.debug(f"Celery worker unavailable; webhook delivery {delivery.id} logged: {exc}")

    return delivery_ids
