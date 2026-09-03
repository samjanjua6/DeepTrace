"""organizations Pydantic schemas — request/response models."""
from datetime import datetime
from pydantic import AliasChoices, BaseModel, Field


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    subscription_tier: str = Field(validation_alias=AliasChoices("subscription_tier", "subscriptionTier"))
    monthly_doc_limit: int = Field(validation_alias=AliasChoices("monthly_doc_limit", "monthlyDocLimit"))
    monthly_doc_used: int = Field(validation_alias=AliasChoices("monthly_doc_used", "monthlyDocUsed"))
    domain: str | None = None
    settings: dict | None = None


class OrgSettingsUpdate(BaseModel):
    name: str | None = None
    settings: dict | None = None


class UsageStatsResponse(BaseModel):
    monthly_doc_limit: int = Field(validation_alias=AliasChoices("monthly_doc_limit", "monthlyDocLimit"))
    monthly_doc_used: int = Field(validation_alias=AliasChoices("monthly_doc_used", "monthlyDocUsed"))
    remaining: int
    billing_cycle_start: datetime | None = Field(default=None, validation_alias=AliasChoices("billing_cycle_start", "billingCycleStart"))
