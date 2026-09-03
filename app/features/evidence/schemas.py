"""Evidence schemas."""
from pydantic import BaseModel
from datetime import datetime


class BoundingBoxResponse(BaseModel):
    id: str
    page_number: int
    x: float; y: float; width: float; height: float
    label: str | None
    color: str | None


class EvidenceArtifactResponse(BaseModel):
    id: str
    artifact_type: str
    storage_url: str  # Pre-signed S3 URL
    mime_type: str
    caption: str | None


class EvidenceItemResponse(BaseModel):
    id: str
    category: str
    severity: str
    rule_id: str
    risk_points: int
    title: str
    description: str
    is_deterministic: bool
    confidence: float | None
    page_number: int | None
    expected_value: str | None
    actual_value: str | None
    discrepancy: str | None
    bounding_boxes: list[BoundingBoxResponse] = []
    artifacts: list[EvidenceArtifactResponse] = []
    created_at: datetime
