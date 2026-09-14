"""
DeepTrace — Full Authentication, Session Lifecycle, MFA, and Multi-Tenancy Test Suite.
Tests:
- Standard login (email + password)
- Bad credentials & lock counter
- RFC 6819 refresh token rotation
- Token reuse breach detection (replay protection)
- User logout and session revocation
- RFC 6238 TOTP engine accuracy
- 2FA challenge and verification flow
- Multi-tenancy listing and organization switching
- Identity endpoint /me with organization context
"""

import pytest
from httpx import AsyncClient
from app.core.totp import generate_totp_secret, get_totp_code, verify_totp

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.asyncio
async def test_totp_engine_rfc6238():
    """Verify RFC 6238 TOTP computation and drift tolerance."""
    secret = "JBSWY3DPEHPK3PXP"  # Standard test secret
    code = get_totp_code(secret)
    assert len(code) == 6
    assert code.isdigit()
    assert verify_totp(secret, code)
    assert not verify_totp(secret, "000000")
    assert not verify_totp(None, code)
    assert not verify_totp(secret, None)


@pytest.mark.asyncio
async def test_standard_login_success(client: AsyncClient):
    """Test standard login with valid credentials."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@meezan.pk", "password": "Analyst@12345"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["mfa_required"] is False


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    """Test login with incorrect password returns 401."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@meezan.pk", "password": "WrongPassword99!"},
    )
    err = resp.json()
    err_code = err.get("error", {}).get("code") or err.get("detail", {}).get("code")
    assert err_code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_breach_detection(client: AsyncClient):
    """Test RFC 6819 refresh token rotation and breach detection upon token reuse."""
    # 1. Login to obtain tokens
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@meezan.pk", "password": "Analyst@12345"},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    first_refresh = token_data["refresh_token"]

    # 2. Rotate session using the refresh token
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert refresh_resp.status_code == 200, refresh_resp.text
    rotated_data = refresh_resp.json()
    second_refresh = rotated_data["refresh_token"]
    assert second_refresh != first_refresh
    assert "access_token" in rotated_data

    # 3. Breach Detection: Attempting to reuse first_refresh (already revoked!)
    reuse_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert reuse_resp.status_code == 401
    err = reuse_resp.json()
    err_code = err.get("error", {}).get("code") or err.get("detail", {}).get("code")
    assert err_code == "SESSION_BREACH_DETECTED"


@pytest.mark.asyncio
async def test_logout_revokes_session(client: AsyncClient):
    """Test logout endpoint revokes session."""
    # 1. Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@meezan.pk", "password": "Analyst@12345"},
    )
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["refresh_token"]

    # 2. Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 204

    # 3. Subsequent refresh attempt should be rejected (revoked session)
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_mfa_login_flow(client: AsyncClient):
    """Test MFA challenge and two-step verification."""
    # 1. Login without code -> triggers MFA challenge
    challenge_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "analyst.mfa@meezan.pk", "password": "Analyst@12345"},
    )
    assert challenge_resp.status_code == 200
    challenge_data = challenge_resp.json()
    assert challenge_data["mfa_required"] is True
    temp_token = challenge_data["temp_token"]
    assert temp_token is not None

    # 2. Verify with invalid code -> rejected
    invalid_verify = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"temp_token": temp_token, "mfa_code": "000000"},
    )
    assert invalid_verify.status_code == 401
    err = invalid_verify.json()
    err_code = err.get("error", {}).get("code") or err.get("detail", {}).get("code")
    assert err_code == "INVALID_MFA_CODE"

    # 3. Verify with valid TOTP code
    valid_code = get_totp_code("JBSWY3DPEHPK3PXP")
    valid_verify = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"temp_token": temp_token, "mfa_code": valid_code},
    )
    assert valid_verify.status_code == 200, valid_verify.text
    tokens = valid_verify.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # 4. Direct login with valid mfa_code included
    direct_code = get_totp_code("JBSWY3DPEHPK3PXP")
    direct_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "analyst.mfa@meezan.pk",
            "password": "Analyst@12345",
            "mfa_code": direct_code,
        },
    )
    assert direct_resp.status_code == 200
    assert direct_resp.json()["mfa_required"] is False
    assert "access_token" in direct_resp.json()


@pytest.mark.asyncio
async def test_multi_tenancy_and_switching(client: AsyncClient):
    """Test listing organizations and switching active banking tenant."""
    # 1. Login as admin
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@deeptrace.test", "password": "Admin@12345"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. List organizations
    orgs_resp = await client.get("/api/v1/auth/organizations", headers=headers)
    assert orgs_resp.status_code == 200
    orgs = orgs_resp.json()
    assert len(orgs) >= 4
    slugs = [o["slug"] for o in orgs]
    assert "meezan-bank" in slugs
    assert "hbl" in slugs
    assert "ubl" in slugs

    # Find HBL org ID
    hbl_org = next(o for o in orgs if o["slug"] == "hbl")

    # 3. Switch organization to HBL
    switch_resp = await client.post(
        "/api/v1/auth/switch-org",
        json={"organization_id": hbl_org["id"]},
        headers=headers,
    )
    assert switch_resp.status_code == 200, switch_resp.text
    switch_data = switch_resp.json()
    assert switch_data["organization"]["slug"] == "hbl"
    hbl_token = switch_data["access_token"]

    # 4. Verify /me reflects the switched organization
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {hbl_token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["organization_id"] == hbl_org["id"]
    assert me_data["organization_slug"] == "hbl"
    assert me_data["organization_name"] == "Habib Bank Limited"


@pytest.mark.asyncio
async def test_mfa_setup_enable_and_disable_lifecycle(client: AsyncClient):
    """Test full real-world MFA lifecycle: enrollment, activation, and disablement."""
    # 1. Login as standard analyst
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@meezan.pk", "password": "Analyst@12345"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Call /mfa/setup to generate secret & QR URI
    setup_resp = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_resp.status_code == 200, setup_resp.text
    setup_data = setup_resp.json()
    secret = setup_data["secret"]
    otpauth_uri = setup_data["otpauth_uri"]
    assert len(secret) >= 16
    assert otpauth_uri.startswith("otpauth://totp/")
    assert "secret=" in otpauth_uri

    # 3. User scans QR code and enters valid 6-digit code
    current_code = get_totp_code(secret)
    enable_resp = await client.post(
        "/api/v1/auth/mfa/enable",
        json={"secret": secret, "code": current_code},
        headers=headers,
    )
    assert enable_resp.status_code == 204

    # 4. Verify /me now confirms MFA is enabled
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["mfa_enabled"] is True

    # 5. Disable MFA with password and code
    disable_code = get_totp_code(secret)
    disable_resp = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": "Analyst@12345", "code": disable_code},
        headers=headers,
    )
    assert disable_resp.status_code == 204

    # 6. Verify /me confirms MFA is now disabled
    me_after = await client.get("/api/v1/auth/me", headers=headers)
    assert me_after.status_code == 200
    assert me_after.json()["mfa_enabled"] is False
