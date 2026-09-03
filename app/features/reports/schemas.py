"""Reports schemas."""
from datetime import datetime
from pydantic import BaseModel


class ReportGenerateRequest(BaseModel):
    include_ela_heatmaps: bool = True
    include_font_analysis: bool = True
    include_agent_narrative: bool = True
    language: str = "en"


class ReportResponse(BaseModel):
    id: str
    investigation_id: str
    status: str  # "generating" | "ready" | "failed"
    download_url: str | None  # Pre-signed S3 URL, populated when ready
    file_size_bytes: int | None
    sha256_hash: str | None
    generated_at: datetime | None
