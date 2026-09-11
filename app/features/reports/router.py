from typing import Annotated
from fastapi import APIRouter, Depends
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth.dependencies import get_current_user
from app.features.investigations.dependencies import get_investigation
from app.features.reports import schemas, service

router = APIRouter()

@router.post("/{investigation_id}/report", response_model=schemas.ReportResponse,
             status_code=202, summary="Generate a court-admissible forensic PDF dossier")
async def generate_report(
    body: schemas.ReportGenerateRequest,
    investigation=Depends(get_investigation),
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    return await service.generate_report(db, investigation.id, body.model_dump())

@router.get("/{investigation_id}/report", response_model=schemas.ReportResponse,
            summary="Get report status and download URL")
async def get_report(
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    return await service.get_report_download_url(db, investigation.id)
