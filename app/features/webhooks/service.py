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


from fastapi import HTTPException
from app.db.client import set_org_context
from app.db.enums import AuditAction


async def create_endpoint(
    db: Prisma,
    org_id: str,
    url: str,
    events: list[str],
    description: str | None = None,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> object:
    """Create a new WebhookEndpoint with an auto-generated cryptographically secure secret and SBP audit logging."""
    secret = secrets.token_hex(32)
    async with set_org_context(org_id) as tx:
        endpoint = await tx.webhookendpoint.create(
            data={
                "organizationId": org_id,
                "url": str(url),
                "secret": secret,
                "events": events,
                "description": description,
                "isActive": True,
            }
        )

        # Register immutable SBP audit log
        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": user_id,
                    "action": AuditAction.ORGANIZATION_SETTINGS_UPDATED.value,
                    "entityType": "webhook_endpoint",
                    "entityId": endpoint.id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({
                        "endpoint_id": endpoint.id,
                        "url": endpoint.url,
                        "events": endpoint.events,
                        "action_detail": "WEBHOOK_ENDPOINT_CREATED",
                    }),
                }
            )
        except Exception as exc:
            logger.error("Failed to record SBP audit log for webhook creation: %s", exc)

    return endpoint


async def list_endpoints(db: Prisma, org_id: str) -> list:
    """List all active webhook endpoints for an organization under tenant RLS."""
    async with set_org_context(org_id) as tx:
        return await tx.webhookendpoint.find_many(
            where={"organizationId": org_id, "isActive": True},
            order={"createdAt": "desc"},
        )


async def delete_endpoint(
    db: Prisma,
    org_id: str,
    endpoint_id: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Soft-delete an endpoint by setting isActive=False with SBP audit logging."""
    async with set_org_context(org_id) as tx:
        endpoint = await tx.webhookendpoint.find_first(
            where={"id": endpoint_id, "organizationId": org_id}
        )
        if not endpoint:
            return

        await tx.webhookendpoint.update(
            where={"id": endpoint_id},
            data={"isActive": False, "disabledAt": datetime.now(timezone.utc)},
        )

        # Register immutable SBP audit log
        try:
            await tx.auditlog.create(
                data={
                    "organizationId": org_id,
                    "userId": user_id,
                    "action": AuditAction.ORGANIZATION_SETTINGS_UPDATED.value,
                    "entityType": "webhook_endpoint",
                    "entityId": endpoint_id,
                    "ipAddress": ip_address,
                    "userAgent": user_agent,
                    "metadata": Json({
                        "endpoint_id": endpoint_id,
                        "url": endpoint.url,
                        "action_detail": "WEBHOOK_ENDPOINT_DEACTIVATED",
                    }),
                }
            )
        except Exception as exc:
            logger.error("Failed to record SBP audit log for webhook deactivation: %s", exc)


async def test_endpoint_ping(
    db: Prisma,
    org_id: str,
    endpoint_id: str,
    event_type: str = "test.ping",
) -> dict:
    """
    Dispatch a simulated event payload with HMAC-SHA256 signature to the destination URL.
    Measures duration and records a test entry in webhook_deliveries.
    """
    import httpx
    async with set_org_context(org_id) as tx:
        endpoint = await tx.webhookendpoint.find_first(
            where={"id": endpoint_id, "organizationId": org_id}
        )
        if not endpoint:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")

        sample_payload = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "organization_id": org_id,
            "data": {
                "message": "DeepTrace institutional webhook verification ping.",
                "compliance_standard": "SBP BPRD / NIST SP 800-86",
                "test_id": f"test_{secrets.token_hex(8)}",
            },
        }

        now_ts = int(time.time())
        sig_header = sign_payload(endpoint.secret, sample_payload, timestamp=now_ts)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "DeepTrace-Webhooks/1.0",
            "X-DeepTrace-Signature": sig_header,
            "X-DeepTrace-Event": event_type,
            "X-DeepTrace-Timestamp": str(now_ts),
        }

        start_time = time.perf_counter()
        status_code = None
        response_body = None
        error_message = None
        success = False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(endpoint.url, json=sample_payload, headers=headers)
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                status_code = resp.status_code
                response_body = resp.text[:1000]
                if 200 <= resp.status_code < 300:
                    success = True
                else:
                    error_message = f"Remote endpoint returned HTTP {resp.status_code}"
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            error_message = f"Delivery failed: {exc}"

        # Record test delivery in webhook_deliveries
        await tx.webhookdelivery.create(
            data={
                "webhookEndpointId": endpoint.id,
                "eventType": event_type,
                "payload": Json(sample_payload),
                "httpStatusCode": status_code,
                "responseBody": response_body,
                "responseDurationMs": duration_ms,
                "attempt": 1,
                "maxAttempts": 1,
                "deliveredAt": datetime.now(timezone.utc) if success else None,
                "failedAt": datetime.now(timezone.utc) if not success else None,
                "errorMessage": error_message,
            }
        )

        return {
            "success": success,
            "http_status_code": status_code,
            "response_duration_ms": duration_ms,
            "signature_header": sig_header,
            "payload_sent": sample_payload,
            "response_body": response_body,
            "error_message": error_message,
        }


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
