"""Reports router."""
from fastapi import APIRouter, Depends, BackgroundTasks
from app.features.auth.dependencies import get_current_user
from app.features.investigations.dependencies import get_investigation
from app.features.reports import schemas, service

router = APIRouter()

@router.post("/{investigation_id}/report", response_model=schemas.ReportResponse,
             status_code=202, summary="Generate a court-admissible forensic PDF dossier")
async def generate_report(
    body: schemas.ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    investigation=Depends(get_investigation),
    user=Depends(get_current_user),
):
    # TODO: background_tasks.add_task(service.generate_report, ...)
    raise NotImplementedError

@router.get("/{investigation_id}/report", response_model=schemas.ReportResponse,
            summary="Get report status and download URL")
async def get_report(investigation=Depends(get_investigation)):
    # TODO: service.get_report_download_url(...)
    raise NotImplementedError
