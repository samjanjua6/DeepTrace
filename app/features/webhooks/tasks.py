"""Webhooks Celery delivery task."""
from app.core.celery_app import celery_app

@celery_app.task(
    name="app.features.webhooks.tasks.deliver_webhook_event",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def deliver_webhook_event(self, delivery_id: str) -> None:
    """
    Deliver a single webhook event to the configured endpoint URL.
    Signs payload with HMAC-SHA256, POSTs to endpoint, records result.
    Retries up to 3 times with exponential backoff on failure.
    Auto-disables endpoint after too many consecutive failures.
    TODO: Implement with httpx.
    """
    import asyncio
    async def _deliver():
        # TODO: fetch WebhookDelivery, POST to endpoint.url, update delivery record
        raise NotImplementedError
    asyncio.run(_deliver())
