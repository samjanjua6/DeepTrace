"""
Risk service — evidence fusion and tier classification.
TODO: Implement Bayesian fusion engine.
"""
from prisma import Prisma
from app.db.enums import RiskTier


async def get_risk_assessment(db: Prisma, investigation_id: str) -> object:
    """Fetch the computed RiskAssessment with all RiskSignal breakdowns."""
    # TODO: db.riskassessment.find_unique(where={"investigationId": investigation_id}, include={"riskSignals": True})
    raise NotImplementedError


async def override_risk_score(db: Prisma, risk_assessment_id: str, score: int,
                               overriding_user_id: str, reason: str) -> object:
    """Allow an analyst to manually override the computed risk score."""
    tier = RiskTier.from_score(score)
    # TODO: db.riskassessment.update(...)
    # TODO: write RISK_SCORE_OVERRIDDEN audit log
    raise NotImplementedError


def compute_risk_score(evidence_items: list) -> tuple[int, str]:
    """
    Bayesian weighted evidence fusion.
    Returns (score: int 0-100, tier: str).
    Called internally by stage_7_fusion Celery task.
    TODO: Implement full Bayesian weighting per §5.2 of the proposal.
    """
    raise NotImplementedError
