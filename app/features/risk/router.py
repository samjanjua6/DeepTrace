"""Risk router — /api/v1/investigations/{id}/risk endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.features.auth.dependencies import get_current_user
from app.features.investigations.dependencies import get_investigation
from app.features.risk import schemas, service

router = APIRouter()


@router.get(
    "/{investigation_id}/risk",
    response_model=schemas.RiskAssessmentResponse,
    summary="Get the computed risk assessment for an investigation",
)
async def get_risk_assessment(
    investigation=Depends(get_investigation),
):
    """Retrieve calibrated risk assessment, tier classification, and Bayesian signal breakdown."""
    assessment = await service.get_risk_assessment(
        org_id=investigation.organizationId,
        investigation_id=investigation.id,
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk assessment not computed yet. Please trigger pipeline analysis first.",
        )
    return assessment


@router.post(
    "/{investigation_id}/risk/override",
    response_model=schemas.RiskAssessmentResponse,
    summary="Analyst override of the computed risk score",
)
async def override_risk_score(
    body: schemas.RiskOverrideRequest,
    investigation=Depends(get_investigation),
    user=Depends(get_current_user),
):
    """Permit an authorized credit or compliance officer to manually override the fraud score with rationale."""
    try:
        return await service.override_risk_score(
            org_id=investigation.organizationId,
            investigation_id=investigation.id,
            score=body.score,
            overriding_user_id=user.id,
            reason=body.reason,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
