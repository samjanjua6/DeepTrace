"""Evidence schemas with Pydantic v2 AliasChoices for Prisma models."""
from datetime import datetime
from typing import Any
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class BoundingBoxResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    page_number: int = Field(validation_alias=AliasChoices("page_number", "pageNumber"))
    x: float
    y: float
    width: float
    height: float
    x_pts: float | None = Field(default=None, validation_alias=AliasChoices("x_pts", "xPts"))
    y_pts: float | None = Field(default=None, validation_alias=AliasChoices("y_pts", "yPts"))
    width_pts: float | None = Field(default=None, validation_alias=AliasChoices("width_pts", "widthPts"))
    height_pts: float | None = Field(default=None, validation_alias=AliasChoices("height_pts", "heightPts"))
    label: str | None = None
    color: str | None = None


class EvidenceArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    artifact_type: str = Field(validation_alias=AliasChoices("artifact_type", "artifactType"))
    storage_path: str = Field(validation_alias=AliasChoices("storage_path", "storagePath", "storage_url", "storageUrl"))
    storage_url: str | None = None
    mime_type: str = Field(validation_alias=AliasChoices("mime_type", "mimeType"))
    caption: str | None = None
    file_size_bytes: int | None = Field(default=None, validation_alias=AliasChoices("file_size_bytes", "fileSizeBytes"))


class EvidenceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    category: str
    severity: str
    rule_id: str = Field(validation_alias=AliasChoices("rule_id", "ruleId"))
    risk_points: int = Field(validation_alias=AliasChoices("risk_points", "riskPoints"))
    title: str
    description: str
    is_deterministic: bool = Field(validation_alias=AliasChoices("is_deterministic", "isDeterministic"))
    confidence: float | None = None
    page_number: int | None = Field(default=None, validation_alias=AliasChoices("page_number", "pageNumber"))
    expected_value: str | None = Field(default=None, validation_alias=AliasChoices("expected_value", "expectedValue"))
    actual_value: str | None = Field(default=None, validation_alias=AliasChoices("actual_value", "actualValue"))
    discrepancy: str | None = None
    technical_details: dict[str, Any] | None = Field(default=None, validation_alias=AliasChoices("technical_details", "technicalDetails"))
    bounding_boxes: list[BoundingBoxResponse] = Field(default=[], validation_alias=AliasChoices("bounding_boxes", "boundingBoxes"))
    artifacts: list[EvidenceArtifactResponse] = []
    created_at: datetime = Field(validation_alias=AliasChoices("created_at", "createdAt"))
