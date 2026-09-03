"""Webhooks schemas."""
from datetime import datetime
from pydantic import BaseModel, HttpUrl


class WebhookEndpointCreate(BaseModel):
    url: HttpUrl
    events: list[str]  # e.g. ["investigation.completed", "risk.critical"]
    description: str | None = None


class WebhookEndpointResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    is_active: bool
    description: str | None
    failure_count: int
    created_at: datetime


class DeliveryLogResponse(BaseModel):
    id: str
    event_type: str
    http_status_code: int | None
    attempt: int
    delivered_at: datetime | None
    failed_at: datetime | None
    error_message: str | None
    created_at: datetime
