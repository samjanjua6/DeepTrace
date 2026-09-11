from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth.dependencies import get_current_user
from app.features.webhooks import schemas, service

router = APIRouter()


@router.get("", response_model=list[schemas.WebhookEndpointResponse], summary="List webhook endpoints")
async def list_endpoints(
    user=Depends(get_current_user),
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


@router.post("", response_model=schemas.WebhookEndpointResponse, status_code=201, summary="Create a webhook endpoint")
async def create_endpoint(
    body: schemas.WebhookEndpointCreate,
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    ep = await service.create_endpoint(
        db,
        org_id=user.organizationId,
        url=str(body.url),
        events=body.events,
        description=body.description,
    )
    return schemas.WebhookEndpointResponse(
        id=ep.id,
        url=ep.url,
        events=ep.events,
        is_active=ep.isActive,
        description=ep.description,
        failure_count=ep.failureCount,
        created_at=ep.createdAt,
    )


@router.delete("/{endpoint_id}", status_code=204, summary="Deactivate a webhook endpoint")
async def delete_endpoint(
    endpoint_id: str,
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    ep = await db.webhookendpoint.find_unique(where={"id": endpoint_id})
    if not ep or ep.organizationId != user.organizationId:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    await service.delete_endpoint(db, endpoint_id)
    return None


@router.get("/{endpoint_id}/deliveries", response_model=list[schemas.DeliveryLogResponse], summary="Get delivery history for an endpoint")
async def list_deliveries(
    endpoint_id: str,
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    ep = await db.webhookendpoint.find_unique(where={"id": endpoint_id})
    if not ep or ep.organizationId != user.organizationId:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    deliveries = await db.webhookdelivery.find_many(
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
            delivered_at=d.deliveredAt,
            failed_at=d.failedAt,
            error_message=d.errorMessage,
            created_at=d.createdAt,
        )
        for d in deliveries
    ]
