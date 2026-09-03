"""Reports service. TODO: Implement PDF dossier generation."""
from prisma import Prisma


async def generate_report(db: Prisma, investigation_id: str, options: dict) -> object:
    """
    Build a court-admissible forensic PDF dossier containing:
    - SHA-256 chain-of-custody header
    - Risk score summary and tier classification
    - Per-evidence finding with bounding box screenshots
    - ELA heatmap attachments
    - Lead Investigator Agent narrative
    - Regulatory disclosure (ETO 2002, PECA 2016, SBP frameworks)
    TODO: Implement with WeasyPrint or ReportLab.
    """
    raise NotImplementedError


async def get_report_download_url(db: Prisma, investigation_id: str) -> str:
    """Return a fresh pre-signed S3 URL for the generated dossier."""
    # TODO: fetch report record, call storage.generate_presigned_url(...)
    raise NotImplementedError
