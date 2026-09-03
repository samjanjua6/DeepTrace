"""Evidence router."""
from fastapi import APIRouter, Depends, Query
from app.features.auth.dependencies import get_current_user
from app.features.investigations.dependencies import get_investigation
from app.features.evidence import schemas, service

router = APIRouter()

@router.get("/{investigation_id}/evidence", response_model=list[schemas.EvidenceItemResponse],
            summary="Get all forensic evidence items for an investigation")
async def list_evidence(
    investigation=Depends(get_investigation),
    severity: str | None = Query(default=None),
):
    # TODO: service.list_evidence(...)
    raise NotImplementedError

@router.get("/{investigation_id}/evidence/{evidence_id}", response_model=schemas.EvidenceItemResponse,
            summary="Get a single evidence item with bounding boxes and artifacts")
async def get_evidence_item(evidence_id: str, investigation=Depends(get_investigation)):
    # TODO: fetch single evidence item with relations
    raise NotImplementedError
