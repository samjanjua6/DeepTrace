"""Auth Pydantic schemas — request/response models."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    mfa_code: Optional[str] = None
    remember_me: Optional[bool] = False


class TokenResponse(BaseModel):
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "bearer"
    expires_in: int = 0  # seconds
    mfa_required: bool = False
    temp_token: Optional[str] = None
    message: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class MfaVerifyRequest(BaseModel):
    temp_token: str
    mfa_code: str = Field(min_length=6, max_length=6)
    remember_me: Optional[bool] = False


class SsoProviderOption(BaseModel):
    id: str
    name: str
    protocol: str  # SAML2, OIDC, WS_FED
    description: str


class SsoInitiateRequest(BaseModel):
    provider: str = "azure_ad"
    tenant_domain: Optional[str] = None
    redirect_uri: Optional[str] = "/investigations"


class SsoInitiateResponse(BaseModel):
    provider: str
    sso_url: str
    entity_id: str
    protocol: str
    message: str


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    issuer: str = "DeepTrace"


class MfaEnableRequest(BaseModel):
    secret: str
    code: str = Field(min_length=6, max_length=6)


class MfaDisableRequest(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=6)


class OrganizationOption(BaseModel):
    id: str
    name: str
    slug: str
    domain: Optional[str] = None
    subscription_tier: Optional[str] = None


class SwitchOrgRequest(BaseModel):
    organization_id: str


class SwitchOrgResponse(BaseModel):
    access_token: str
    refresh_token: str
    organization: OrganizationOption


class MeResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    organization_id: str
    mfa_enabled: bool
    organization_name: Optional[str] = None
    organization_slug: Optional[str] = None
