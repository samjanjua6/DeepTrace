"""Router for Executive Fraud Analytics & Risk Command Center."""
from typing import Annotated
from fastapi import APIRouter, Depends
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth.dependencies import get_current_user
from app.features.analytics import schemas, service

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=schemas.DashboardStatsResponse,
    summary="Get executive fraud analytics and risk command center metrics",
)
async def get_dashboard_analytics(
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """
    Retrieve executive telemetry metrics:
    - Month-to-date scanned document volume and quota utilization
    - Tampering detection rate across CRITICAL and HIGH severity cases
    - Total financial exposure prevented (Pakistani Rupee inflation intercepted)
    - Average verification latency (p50 and p95 processing percentiles)
    - Recent critical risk alerts and document distribution
    """
    return await service.get_dashboard_metrics(db, user.organizationId)


@router.get(
    "",
    response_model=schemas.DashboardStatsResponse,
    summary="Get executive fraud analytics and risk command center metrics (direct root)",
    include_in_schema=False,
)
async def get_dashboard_root(
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    return await service.get_dashboard_metrics(db, user.organizationId)
