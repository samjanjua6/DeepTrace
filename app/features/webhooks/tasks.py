import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
import time
import httpx

from app.core.celery_app import celery_app
from app.db.client import db, set_org_context
from prisma import Prisma
from app.features.webhooks.service import sign_payload

logger = logging.getLogger(__name__)


async def execute_delivery(delivery_id: str, org_id: str | None = None, client: Prisma | None = None) -> bool:
    """
    Deliver a webhook event to its destination URL via HTTP POST.
    Includes Stripe-standard timestamped HMAC signature and exponential backoff retry tracking.
    """
    if client is None and org_id:
        async with set_org_context(org_id) as tx:
            return await execute_delivery(delivery_id, org_id=org_id, client=tx)

    c = client or db
    delivery = await c.webhookdelivery.find_unique(
        where={"id": delivery_id},
        include={"webhookEndpoint": True},
    )
    if not delivery or not delivery.webhookEndpoint:
        logger.warning(f"Webhook delivery {delivery_id} or endpoint not found.")
        return False

    endpoint = delivery.webhookEndpoint
    if not endpoint.isActive:
        logger.info(f"Endpoint {endpoint.id} is inactive; skipping delivery.")
        return False

    raw_payload = delivery.payload
    if isinstance(raw_payload, str):
        try:
            payload_dict = json.loads(raw_payload)
        except Exception:
            payload_dict = {"raw": raw_payload}
    else:
        payload_dict = raw_payload or {}

    now_ts = int(time.time())
    sig_header = sign_payload(endpoint.secret, payload_dict, timestamp=now_ts)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "DeepTrace-Webhooks/1.0",
        "X-DeepTrace-Signature": sig_header,
        "X-DeepTrace-Event": delivery.eventType,
        "X-DeepTrace-Delivery-Id": delivery.id,
        "X-DeepTrace-Timestamp": str(now_ts),
    }

    start_time = time.perf_counter()
    status_code = None
    response_body = None
    error_message = None
    success = False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(endpoint.url, json=payload_dict, headers=headers)
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

    if success:
        await c.webhookdelivery.update(
            where={"id": delivery.id},
            data={
                "httpStatusCode": status_code,
                "responseBody": response_body,
                "responseDurationMs": duration_ms,
                "deliveredAt": datetime.now(timezone.utc),
                "errorMessage": None,
            },
        )
        if endpoint.failureCount > 0:
            await c.webhookendpoint.update(
                where={"id": endpoint.id},
                data={"failureCount": 0},
            )
        return True
    else:
        new_failure_count = endpoint.failureCount + 1
        endpoint_disabled = False
        if new_failure_count >= 10:
            endpoint_disabled = True

        next_retry = None
        if delivery.attempt < delivery.maxAttempts:
            backoff_secs = 60 * (2 ** (delivery.attempt - 1))
            next_retry = datetime.now(timezone.utc) + timedelta(seconds=backoff_secs)

        await c.webhookdelivery.update(
            where={"id": delivery.id},
            data={
                "httpStatusCode": status_code,
                "responseBody": response_body,
                "responseDurationMs": duration_ms,
                "failedAt": datetime.now(timezone.utc),
                "errorMessage": error_message,
                "nextRetryAt": next_retry,
            },
        )

        ep_update_data: dict = {"failureCount": new_failure_count}
        if endpoint_disabled:
            ep_update_data["isActive"] = False
            ep_update_data["disabledAt"] = datetime.now(timezone.utc)

        await c.webhookendpoint.update(
            where={"id": endpoint.id},
            data=ep_update_data,
        )
        return False


@celery_app.task(
    name="app.features.webhooks.tasks.deliver_webhook_event",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def deliver_webhook_event(self, delivery_id: str, org_id: str = "") -> None:
    """
    Deliver a single webhook event to the configured endpoint URL.
    Signs payload with HMAC-SHA256, POSTs to endpoint, records result.
    Retries up to 3 times with exponential backoff on failure.
    """
    asyncio.run(execute_delivery(delivery_id, org_id=org_id))
