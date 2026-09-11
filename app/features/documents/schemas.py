"""Documents schemas with Pydantic v2 AliasChoices for Prisma models."""
from datetime import datetime
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    investigation_id: str = Field(validation_alias=AliasChoices("investigation_id", "investigationId"))
    original_filename: str = Field(validation_alias=AliasChoices("original_filename", "originalFilename"))
    mime_type: str = Field(default="application/pdf", validation_alias=AliasChoices("mime_type", "mimeType"))
    file_size_bytes: int = Field(validation_alias=AliasChoices("file_size_bytes", "fileSizeBytes"))
    document_type: str = Field(validation_alias=AliasChoices("document_type", "documentType"))
    sha256_hash: str = Field(validation_alias=AliasChoices("sha256_hash", "sha256Hash"))
    md5_hash: str | None = Field(default=None, validation_alias=AliasChoices("md5_hash", "md5Hash"))
    page_count: int | None = Field(default=None, validation_alias=AliasChoices("page_count", "pageCount"))
    is_password_protected: bool = Field(default=False, validation_alias=AliasChoices("is_password_protected", "isPasswordProtected"))
    processing_status: str = Field(validation_alias=AliasChoices("processing_status", "processingStatus"))
    created_at: datetime = Field(validation_alias=AliasChoices("created_at", "createdAt"))


class DocumentMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    document_id: str = Field(validation_alias=AliasChoices("document_id", "documentId"))
    pdf_version: str | None = Field(default=None, validation_alias=AliasChoices("pdf_version", "pdfVersion"))
    producer: str | None = None
    creator: str | None = None
    creation_date: datetime | None = Field(default=None, validation_alias=AliasChoices("creation_date", "creationDate"))
    modification_date: datetime | None = Field(default=None, validation_alias=AliasChoices("modification_date", "modificationDate"))
    incremental_save_count: int = Field(default=0, validation_alias=AliasChoices("incremental_save_count", "incrementalSaveCount"))
    has_javascript: bool = Field(default=False, validation_alias=AliasChoices("has_javascript", "hasJavaScript"))


class DocumentPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    page_number: int = Field(validation_alias=AliasChoices("page_number", "pageNumber"))
    width_px: int | None = Field(default=None, validation_alias=AliasChoices("width_px", "widthPx"))
    height_px: int | None = Field(default=None, validation_alias=AliasChoices("height_px", "heightPx"))
    width_pts: float | None = Field(default=None, validation_alias=AliasChoices("width_pts", "widthPts"))
    height_pts: float | None = Field(default=None, validation_alias=AliasChoices("height_pts", "heightPts"))
    dpi: int | None = None
    ocr_confidence: float | None = Field(default=None, validation_alias=AliasChoices("ocr_confidence", "ocrConfidence"))
    rendered_image_url: str | None = None
    thumbnail_url: str | None = None


class CustodyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    investigation_id: str = Field(validation_alias=AliasChoices("investigation_id", "investigationId"))
    event_type: str = Field(validation_alias=AliasChoices("event_type", "eventType"))
    description: str
    sha256_hash: str | None = Field(default=None, validation_alias=AliasChoices("sha256_hash", "sha256Hash"))
    actor_type: str = Field(default="system", validation_alias=AliasChoices("actor_type", "actorType"))
    actor_id: str | None = Field(default=None, validation_alias=AliasChoices("actor_id", "actorId"))
    timestamp: datetime = Field(validation_alias=AliasChoices("timestamp", "created_at", "createdAt"))


class DocumentDetailResponse(DocumentResponse):
    pages: list[DocumentPageResponse] = []
    custody_events: list[CustodyEventResponse] = []

