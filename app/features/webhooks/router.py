from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from prisma import Prisma

from app.db.client import get_db_dep, set_org_context
from app.db.enums import UserRole
from app.features.auth.dependencies import require_role
from app.features.webhooks import schemas, service

router = APIRouter()

# Restrict all Webhook governance operations to institutional administrators (ADMIN and OWNER)
AdminUser = Depends(require_role(UserRole.ADMIN, UserRole.OWNER))


@router.get("", response_model=list[schemas.WebhookEndpointResponse], summary="List webhook endpoints (Admin only)")
async def list_endpoints(
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    endpoints = await service.list_endpoints(db, user.organizationId)
    return [
        schemas.WebhookEndpointResponse(
            id=ep.id,
            url=ep.url,
            events=ep.events,
            is_active=ep.isActive,
            description=ep.description,
            failure_count=ep.failureCount,
            created_at=ep.createdAt,
        )
        for ep in endpoints
    ]


@router.post("", response_model=schemas.WebhookEndpointCreatedResponse, status_code=201, summary="Create a webhook endpoint (Admin only)")
async def create_endpoint(
    body: schemas.WebhookEndpointCreate,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    ep = await service.create_endpoint(
        db,
        org_id=user.organizationId,
        url=str(body.url),
        events=body.events,
        description=body.description,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return schemas.WebhookEndpointCreatedResponse(
        id=ep.id,
        url=ep.url,
        events=ep.events,
        is_active=ep.isActive,
        description=ep.description,
        failure_count=ep.failureCount,
        created_at=ep.createdAt,
        secret=ep.secret,
    )


@router.get("/{endpoint_id}/secret", response_model=schemas.WebhookSecretResponse, summary="Retrieve HMAC signing secret for an endpoint (Admin only)")
async def get_endpoint_secret(
    endpoint_id: str,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    async with set_org_context(user.organizationId) as tx:
        ep = await tx.webhookendpoint.find_first(
            where={"id": endpoint_id, "organizationId": user.organizationId}
        )
        if not ep:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        return schemas.WebhookSecretResponse(secret=ep.secret)


@router.delete("/{endpoint_id}", status_code=204, summary="Deactivate a webhook endpoint (Admin only)")
async def delete_endpoint(
    endpoint_id: str,
    request: Request,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    async with set_org_context(user.organizationId) as tx:
        ep = await tx.webhookendpoint.find_first(
            where={"id": endpoint_id, "organizationId": user.organizationId}
        )
        if not ep:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    await service.delete_endpoint(
        db,
        user.organizationId,
        endpoint_id,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return None


@router.get("/{endpoint_id}/deliveries", response_model=list[schemas.DeliveryLogResponse], summary="Get delivery history for an endpoint (Admin only)")
async def list_deliveries(
    endpoint_id: str,
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    async with set_org_context(user.organizationId) as tx:
        ep = await tx.webhookendpoint.find_first(
            where={"id": endpoint_id, "organizationId": user.organizationId}
        )
        if not ep:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")

        deliveries = await tx.webhookdelivery.find_many(
            where={"webhookEndpointId": endpoint_id},
            order={"createdAt": "desc"},
            take=50,
        )
        return [
            schemas.DeliveryLogResponse(
                id=d.id,
                event_type=d.eventType,
                http_status_code=d.httpStatusCode,
                attempt=d.attempt,
                response_duration_ms=d.responseDurationMs,
                response_body=d.responseBody,
                delivered_at=d.deliveredAt,
                failed_at=d.failedAt,
                error_message=d.errorMessage,
                created_at=d.createdAt,
            )
            for d in deliveries
        ]


@router.post("/{endpoint_id}/test", response_model=schemas.WebhookTestResponse, summary="Send simulated HMAC-signed test ping to endpoint (Admin only)")
async def test_endpoint(
    endpoint_id: str,
    body: schemas.WebhookTestRequest = schemas.WebhookTestRequest(),
    user=AdminUser,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    return await service.test_endpoint_ping(
        db,
        user.organizationId,
        endpoint_id,
        event_type=body.event_type,
    )

