"""Evidence router — /api/v1/investigations/{id}/evidence endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.features.auth.dependencies import get_current_user
from app.features.investigations.dependencies import get_investigation
from app.features.evidence import schemas, service

router = APIRouter()


@router.get(
    "/{investigation_id}/evidence",
    response_model=list[schemas.EvidenceItemResponse],
    summary="Get all forensic evidence items for an investigation",
)
async def list_evidence(
    investigation=Depends(get_investigation),
    severity: str | None = Query(default=None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW, INFO"),
):
    """Retrieve all discrete forensic findings with bounding boxes for an investigation."""
    return await service.list_evidence(
        org_id=investigation.organizationId,
        investigation_id=investigation.id,
        severity=severity,
    )


@router.get(
    "/{investigation_id}/evidence/{evidence_id}",
    response_model=schemas.EvidenceItemResponse,
    summary="Get a single evidence item with bounding boxes and artifacts",
)
async def get_evidence_item(
    evidence_id: str,
    investigation=Depends(get_investigation),
):
    """Retrieve a single evidence finding with its bounding boxes and proof artifacts."""
    item = await service.get_evidence_item(
        org_id=investigation.organizationId,
        evidence_id=evidence_id,
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence item '{evidence_id}' not found.",
        )
    return item
