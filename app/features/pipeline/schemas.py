"""Pipeline schemas."""
from datetime import datetime
from pydantic import BaseModel


class PipelineRunResponse(BaseModel):
    id: str
    investigation_id: str
    run_number: int
    status: str
    trigger_source: str
    total_duration_ms: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class StageStatusResponse(BaseModel):
    stage_type: str
    stage_order: int
    status: str
    duration_ms: int | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class PipelineTriggerRequest(BaseModel):
    document_id: str | None = None  # If None, analyze all docs in investigation
    parameters: dict = {}
