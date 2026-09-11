"""Pipeline schemas with Pydantic v2 AliasChoices for Prisma models."""
from datetime import datetime
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class StageStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str | None = None
    stage_type: str = Field(validation_alias=AliasChoices("stage_type", "stageType"))
    stage_order: int = Field(validation_alias=AliasChoices("stage_order", "stageOrder"))
    status: str
    duration_ms: int | None = Field(default=None, validation_alias=AliasChoices("duration_ms", "durationMs"))
    error_message: str | None = Field(default=None, validation_alias=AliasChoices("error_message", "errorMessage"))
    started_at: datetime | None = Field(default=None, validation_alias=AliasChoices("started_at", "startedAt"))
    completed_at: datetime | None = Field(default=None, validation_alias=AliasChoices("completed_at", "completedAt"))
    output_payload: dict | None = Field(default=None, validation_alias=AliasChoices("output_payload", "outputPayload"))


class PipelineRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    investigation_id: str = Field(validation_alias=AliasChoices("investigation_id", "investigationId"))
    run_number: int = Field(validation_alias=AliasChoices("run_number", "runNumber"))
    status: str
    trigger_source: str = Field(validation_alias=AliasChoices("trigger_source", "triggerSource"))
    total_duration_ms: int | None = Field(default=None, validation_alias=AliasChoices("total_duration_ms", "totalDurationMs"))
    started_at: datetime | None = Field(default=None, validation_alias=AliasChoices("started_at", "startedAt"))
    completed_at: datetime | None = Field(default=None, validation_alias=AliasChoices("completed_at", "completedAt"))
    created_at: datetime = Field(validation_alias=AliasChoices("created_at", "createdAt"))
    stages: list[StageStatusResponse] = []


class PipelineTriggerRequest(BaseModel):
    document_id: str | None = None  # If None, analyze all docs in investigation
    parameters: dict = {}
