"""organizations Pydantic schemas — request/response models."""
from datetime import datetime
from enum import Enum
from pydantic import AliasChoices, BaseModel, Field


class SubscriptionTierEnum(str, Enum):
    FREE = "FREE"
    FINTECH_GROWTH = "FINTECH_GROWTH"
    BUSINESS_SCALE = "BUSINESS_SCALE"
    ENTERPRISE = "ENTERPRISE"


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    subscription_tier: str = Field(validation_alias=AliasChoices("subscription_tier", "subscriptionTier"))
    monthly_doc_limit: int = Field(validation_alias=AliasChoices("monthly_doc_limit", "monthlyDocLimit"))
    monthly_doc_used: int = Field(validation_alias=AliasChoices("monthly_doc_used", "monthlyDocUsed"))
    remaining_docs: int = 0
    usage_percentage: float = 0.0
    domain: str | None = None
    settings: dict | None = None
    billing_cycle_start: datetime | None = Field(default=None, validation_alias=AliasChoices("billing_cycle_start", "billingCycleStart"))
    days_until_renewal: int = 30


class OrgSettingsUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    settings: dict | None = None


class TierUpgradeRequest(BaseModel):
    target_tier: SubscriptionTierEnum


class UsageStatsResponse(BaseModel):
    subscription_tier: str = Field(default="FREE", validation_alias=AliasChoices("subscription_tier", "subscriptionTier"))
    monthly_doc_limit: int = Field(validation_alias=AliasChoices("monthly_doc_limit", "monthlyDocLimit"))
    monthly_doc_used: int = Field(validation_alias=AliasChoices("monthly_doc_used", "monthlyDocUsed"))
    remaining: int
    usage_percentage: float = 0.0
    days_until_renewal: int = 30
    billing_cycle_start: datetime | None = Field(default=None, validation_alias=AliasChoices("billing_cycle_start", "billingCycleStart"))
    document_type_breakdown: dict[str, int] = Field(default_factory=dict)
