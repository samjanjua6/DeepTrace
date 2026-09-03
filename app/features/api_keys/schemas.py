from datetime import datetime
from pydantic import AliasChoices, BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = ["read", "write"]
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str = Field(validation_alias=AliasChoices("key_prefix", "keyPrefix"))
    scopes: list[str]
    is_active: bool = Field(validation_alias=AliasChoices("is_active", "isActive"))
    created_at: datetime = Field(validation_alias=AliasChoices("created_at", "createdAt"))
    expires_at: datetime | None = Field(default=None, validation_alias=AliasChoices("expires_at", "expiresAt"))
    last_used_at: datetime | None = Field(default=None, validation_alias=AliasChoices("last_used_at", "lastUsedAt"))


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned ONCE at creation. Full plaintext key is included here only."""
    plaintext_key: str
