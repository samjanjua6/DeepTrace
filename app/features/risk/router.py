"""Risk router."""
from fastapi import APIRouter, Depends
from app.features.auth.dependencies import get_current_user
from app.features.investigations.dependencies import get_investigation
from app.features.risk import schemas, service

router = APIRouter()

@router.get("/{investigation_id}/risk", response_model=schemas.RiskAssessmentResponse,
            summary="Get the computed risk assessment for an investigation")
async def get_risk_assessment(investigation=Depends(get_investigation)):
    # TODO: service.get_risk_assessment(...)
    raise NotImplementedError

@router.post("/{investigation_id}/risk/override", response_model=schemas.RiskAssessmentResponse,
             summary="Analyst override of the computed risk score")
async def override_risk_score(
    body: schemas.RiskOverrideRequest,
    investigation=Depends(get_investigation),
    user=Depends(get_current_user),
):
    # TODO: service.override_risk_score(...)
    raise NotImplementedError
