"""Documents schemas."""
from datetime import datetime
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    investigation_id: str
    original_filename: str
    file_size_bytes: int
    document_type: str
    sha256_hash: str
    page_count: int | None
    processing_status: str
    created_at: datetime


class DocumentMetadataResponse(BaseModel):
    id: str
    document_id: str
    pdf_version: str | None
    producer: str | None
    creator: str | None
    creation_date: datetime | None
    modification_date: datetime | None
    incremental_save_count: int
    suspicious_producers: list[str]
    producer_creator_match: bool | None
    font_count: int
    image_count: int


class DocumentPageResponse(BaseModel):
    id: str
    page_number: int
    width_px: int | None
    height_px: int | None
    ocr_confidence: float | None
    rendered_image_url: str | None  # Pre-signed S3 URL
