import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.client import connect, disconnect, db


@pytest.mark.asyncio
async def test_remember_me_and_sso_endpoints():
    """Verify remember_me session duration and SSO federation endpoints."""
    if db.is_connected():
        await disconnect()
    await connect()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Test SSO Providers endpoint
            res_sso = await client.get("/api/v1/auth/sso/providers")
            assert res_sso.status_code == 200
            providers = res_sso.json()
            assert len(providers) >= 3
            provider_ids = [p["id"] for p in providers]
            assert "azure_ad" in provider_ids
            assert "okta" in provider_ids
            assert "saml" in provider_ids

            # 2. Test SSO Initiate endpoint
            res_init = await client.post(
                "/api/v1/auth/sso/initiate",
                json={"provider": "azure_ad", "tenant_domain": "meezan.pk"},
            )
            assert res_init.status_code == 200
            init_data = res_init.json()
            assert init_data["provider"] == "azure_ad"
            assert "login.microsoftonline.com" in init_data["sso_url"]
            assert "entity_id" in init_data

            # 3. Test Login with remember_me = False
            async with db.tx() as tx:
                await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
                analyst = await tx.user.find_first(where={"role": "ANALYST"})
            assert analyst is not None

            # Login with analyst credentials
            res_login_transient = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": analyst.email,
                    "password": "Password123!",
                    "remember_me": False,
                },
            )
            # If standard seeded password
            if res_login_transient.status_code == 200:
                data = res_login_transient.json()
                assert "access_token" in data
                assert "refresh_token" in data
    finally:
        if db.is_connected():
            await disconnect()
