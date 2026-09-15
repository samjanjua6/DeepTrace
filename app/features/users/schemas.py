"""Pydantic schemas for User & Role Administration."""
from datetime import datetime
from pydantic import AliasChoices, BaseModel, EmailStr, Field
from app.db.enums import UserRole


class UserItemResponse(BaseModel):
    id: str
    email: str
    first_name: str = Field(validation_alias=AliasChoices("first_name", "firstName"))
    last_name: str = Field(validation_alias=AliasChoices("last_name", "lastName"))
    role: str
    is_active: bool = Field(validation_alias=AliasChoices("is_active", "isActive"))
    mfa_enabled: bool = Field(default=False, validation_alias=AliasChoices("mfa_enabled", "mfaEnabled"))
    failed_login_count: int = Field(default=0, validation_alias=AliasChoices("failed_login_count", "failedLoginCount"))
    is_locked: bool = False
    locked_until: datetime | None = Field(default=None, validation_alias=AliasChoices("locked_until", "lockedUntil"))
    last_login_at: datetime | None = Field(default=None, validation_alias=AliasChoices("last_login_at", "lastLoginAt"))
    created_at: datetime = Field(validation_alias=AliasChoices("created_at", "createdAt"))


class InviteUserRequest(BaseModel):
    email: str = Field(min_length=3)
    first_name: str
    last_name: str
    role: UserRole = UserRole.ANALYST
    temp_password: str | None = None


class InviteUserResponse(BaseModel):
    user: UserItemResponse
    temp_password: str
    login_url: str
    dispatch_memo: str


class UpdateUserRoleRequest(BaseModel):
    role: UserRole


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class ActionMessageResponse(BaseModel):
    success: bool
    message: str
