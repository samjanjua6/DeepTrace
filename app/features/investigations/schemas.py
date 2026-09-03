from datetime import datetime
from pydantic import AliasChoices, BaseModel, Field


class InvestigationCreate(BaseModel):
    title: str | None = None
    description: str | None = None
    client_reference: str | None = None
    priority: int = Field(default=0, ge=0, le=2)


class InvestigationUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: int | None = Field(default=None, ge=0, le=2)
    assigned_analyst_id: str | None = None


class InvestigationResponse(BaseModel):
    id: str
    case_number: str = Field(validation_alias=AliasChoices("case_number", "caseNumber"))
    title: str | None = None
    status: str
    priority: int
    source: str
    client_reference: str | None = Field(default=None, validation_alias=AliasChoices("client_reference", "clientReference"))
    risk_score: int | None = None
    risk_tier: str | None = None
    created_at: datetime = Field(validation_alias=AliasChoices("created_at", "createdAt"))
    updated_at: datetime = Field(validation_alias=AliasChoices("updated_at", "updatedAt"))


class InvestigationFilter(BaseModel):
    status: str | None = None
    priority: int | None = None
    document_type: str | None = None
    search: str | None = None
