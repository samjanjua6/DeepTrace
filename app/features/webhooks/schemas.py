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


class WebhookEndpointCreatedResponse(WebhookEndpointResponse):
    secret: str


class WebhookSecretResponse(BaseModel):
    secret: str


class WebhookTestRequest(BaseModel):
    event_type: str = "test.ping"


class WebhookTestResponse(BaseModel):
    success: bool
    http_status_code: int | None = None
    response_duration_ms: int = 0
    signature_header: str
    payload_sent: dict
    response_body: str | None = None
    error_message: str | None = None


class DeliveryLogResponse(BaseModel):
    id: str
    event_type: str
    http_status_code: int | None
    attempt: int
    response_duration_ms: int | None = None
    response_body: str | None = None
    delivered_at: datetime | None
    failed_at: datetime | None
    error_message: str | None
    created_at: datetime

