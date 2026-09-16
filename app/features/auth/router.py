"""Auth router — /api/v1/auth endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth import schemas, service
from app.features.auth.dependencies import CurrentUser, get_current_user

router = APIRouter()


@router.post("/login", response_model=schemas.TokenResponse, summary="Login with email + password (optional MFA code)")
async def login(
    body: schemas.LoginRequest,
    request: Request,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.login(
        db,
        body.email,
        body.password,
        mfa_code=body.mfa_code,
        remember_me=bool(body.remember_me),
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post("/token", response_model=schemas.TokenResponse, summary="OAuth2 compatible token endpoint")
async def token(
    request: Request,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    """Accept both application/x-www-form-urlencoded (OAuth2) and application/json."""
    content_type = request.headers.get("content-type", "")
    mfa_code = None
    remember_me = False
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        email = str(form.get("username") or form.get("email") or "")
        password = str(form.get("password") or "")
        mfa_code = form.get("mfa_code") or form.get("otp")
        remember_me = str(form.get("remember_me") or "").lower() in ("true", "1", "yes")
    else:
        try:
            data = await request.json()
            email = str(data.get("email") or data.get("username") or "")
            password = str(data.get("password") or "")
            mfa_code = data.get("mfa_code")
            remember_me = bool(data.get("remember_me", False))
        except Exception:
            email, password = "", ""

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.login(
        db,
        email,
        password,
        mfa_code=str(mfa_code) if mfa_code else None,
        remember_me=remember_me,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post("/refresh", response_model=schemas.TokenResponse, summary="Rotate refresh token and issue fresh access token")
async def refresh(
    body: schemas.RefreshRequest,
    request: Request,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.refresh_tokens(db, body.refresh_token, ip_address=ip, user_agent=user_agent)


@router.post("/logout", status_code=204, summary="Revoke current user session")
async def logout(
    body: schemas.RefreshRequest,
    request: Request,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await service.logout(db, body.refresh_token, ip_address=ip, user_agent=user_agent)


@router.post("/mfa/verify", response_model=schemas.TokenResponse, summary="Finalize login with 2FA TOTP code")
async def verify_mfa(
    body: schemas.MfaVerifyRequest,
    request: Request,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.verify_mfa_login(
        db,
        temp_token=body.temp_token,
        mfa_code=body.mfa_code,
        remember_me=bool(body.remember_me),
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post("/mfa/setup", response_model=schemas.MfaSetupResponse, summary="Generate new 2FA secret and setup URI")
async def mfa_setup(
    current_user: CurrentUser,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    return await service.setup_mfa(db, current_user.id)


@router.post("/mfa/enable", status_code=204, summary="Verify TOTP code and enable 2FA on user account")
async def mfa_enable(
    body: schemas.MfaEnableRequest,
    current_user: CurrentUser,
    request: Request,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    ip = request.client.host if request.client else None
    await service.enable_mfa(db, current_user.id, body.secret, body.code, ip_address=ip)


@router.post("/mfa/disable", status_code=204, summary="Disable 2FA after password and TOTP code verification")
async def mfa_disable(
    body: schemas.MfaDisableRequest,
    current_user: CurrentUser,
    request: Request,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    ip = request.client.host if request.client else None
    await service.disable_mfa(db, current_user.id, body.password, body.code, ip_address=ip)


@router.get("/organizations", response_model=list[schemas.OrganizationOption], summary="List available banking tenants")
async def get_organizations(
    current_user: CurrentUser,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    return await service.list_organizations(db, current_user)


@router.post("/switch-org", response_model=schemas.SwitchOrgResponse, summary="Switch active banking organization context")
async def switch_org(
    body: schemas.SwitchOrgRequest,
    current_user: CurrentUser,
    request: Request,
    db: Annotated[Prisma, Depends(get_db_dep)],
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.switch_organization(
        db,
        current_user,
        body.organization_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get("/me", response_model=schemas.MeResponse, summary="Get current authenticated user identity")
async def me(current_user: CurrentUser):
    org_name = current_user.organization.name if hasattr(current_user, "organization") and current_user.organization else None
    org_slug = current_user.organization.slug if hasattr(current_user, "organization") and current_user.organization else None
    return schemas.MeResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.firstName,
        last_name=current_user.lastName,
        role=current_user.role,
        organization_id=current_user.organizationId,
        mfa_enabled=current_user.mfaEnabled,
        organization_name=org_name,
        organization_slug=org_slug,
    )


@router.get("/sso/providers", response_model=list[schemas.SsoProviderOption], summary="Get available enterprise SSO identity providers")
async def sso_providers():
    return service.get_sso_providers()


@router.post("/sso/initiate", response_model=schemas.SsoInitiateResponse, summary="Initiate enterprise SSO federation")
async def sso_initiate(body: schemas.SsoInitiateRequest):
    return service.initiate_sso(
        provider=body.provider,
        tenant_domain=body.tenant_domain,
        redirect_uri=body.redirect_uri,
    )
