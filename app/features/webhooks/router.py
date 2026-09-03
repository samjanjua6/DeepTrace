"""Webhooks router."""
from fastapi import APIRouter, Depends
from app.features.auth.dependencies import get_current_user
from app.features.webhooks import schemas, service

router = APIRouter()

@router.get("", response_model=list[schemas.WebhookEndpointResponse], summary="List webhook endpoints")
async def list_endpoints(user=Depends(get_current_user)):
    raise NotImplementedError

@router.post("", response_model=schemas.WebhookEndpointResponse, status_code=201, summary="Create a webhook endpoint")
async def create_endpoint(body: schemas.WebhookEndpointCreate, user=Depends(get_current_user)):
    raise NotImplementedError

@router.delete("/{endpoint_id}", status_code=204, summary="Deactivate a webhook endpoint")
async def delete_endpoint(endpoint_id: str, user=Depends(get_current_user)):
    raise NotImplementedError

@router.get("/{endpoint_id}/deliveries", response_model=list[schemas.DeliveryLogResponse], summary="Get delivery history for an endpoint")
async def list_deliveries(endpoint_id: str, user=Depends(get_current_user)):
    raise NotImplementedError
