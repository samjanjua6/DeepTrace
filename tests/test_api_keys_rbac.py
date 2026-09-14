import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.client import connect, disconnect, db


@pytest.mark.asyncio
async def test_api_keys_complete_rbac_and_audit_lifecycle():
    """Comprehensive test for API key RBAC, full lifecycle, and audit logging."""
    if db.is_connected():
        await disconnect()
    await connect()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # ── 1. Unauthenticated requests must be rejected with 401 ──────────
            res = await client.get("/api/v1/api-keys")
            assert res.status_code == 401

            # ── 2. Analyst role must be rejected with 403 INSUFFICIENT_PERMISSIONS ──
            from app.core.security import create_access_token
            async with db.tx() as tx:
                await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
                analyst_user = await tx.user.find_first(where={"role": "ANALYST"})
            assert analyst_user is not None
            analyst_token = create_access_token(subject=analyst_user.id)
            analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

            # GET should be 403
            res_get = await client.get("/api/v1/api-keys", headers=analyst_headers)
            assert res_get.status_code == 403
            assert "FORBIDDEN" in res_get.text

            # POST should be 403
            res_post = await client.post(
                "/api/v1/api-keys",
                json={"name": "Illicit Key Attempt", "scopes": ["investigations:read"]},
                headers=analyst_headers,
            )
            assert res_post.status_code == 403
            assert "FORBIDDEN" in res_post.text

            # DELETE should be 403
            res_del = await client.delete("/api/v1/api-keys/fake-key-id", headers=analyst_headers)
            assert res_del.status_code == 403
            assert "FORBIDDEN" in res_del.text

            # ── 3. Admin role can create, list, and revoke keys ─────────────────
            admin_login_resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "admin@deeptrace.test", "password": "Admin@12345"},
            )
            assert admin_login_resp.status_code == 200
            admin_token = admin_login_resp.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Create API key with 30-day expiration
            create_payload = {
                "name": "Meezan Core Banking Middleware",
                "scopes": ["investigations:read", "investigations:write"],
                "expires_in_days": 30,
            }
            res_create = await client.post("/api/v1/api-keys", json=create_payload, headers=admin_headers)
            assert res_create.status_code == 201
            created_data = res_create.json()

            key_id = created_data["id"]
            prefix = created_data["key_prefix"]
            plaintext = created_data["plaintext_key"]

            assert key_id is not None
            assert prefix.startswith("dt_pk_")
            assert plaintext.startswith("dt_pk_")
            assert created_data["scopes"] == ["investigations:read", "investigations:write"]
            assert created_data["expires_at"] is not None
            assert created_data["is_active"] is True

            # List active keys - verify key appears with prefix but plaintext is never leaked
            res_list = await client.get("/api/v1/api-keys", headers=admin_headers)
            assert res_list.status_code == 200
            keys = res_list.json()
            assert any(k["id"] == key_id for k in keys)
            found = next(k for k in keys if k["id"] == key_id)
            assert "plaintext_key" not in found
            assert found["key_prefix"] == prefix

            # Revoke the key
            res_revoke = await client.delete(f"/api/v1/api-keys/{key_id}", headers=admin_headers)
            assert res_revoke.status_code == 204

            # Verify key is no longer in active keys list
            res_list_after = await client.get("/api/v1/api-keys", headers=admin_headers)
            assert res_list_after.status_code == 200
            active_keys = res_list_after.json()
            assert not any(k["id"] == key_id for k in active_keys)

            # Verify key appears in revoked keys query (include_revoked=True)
            res_all = await client.get("/api/v1/api-keys?include_revoked=true", headers=admin_headers)
            assert res_all.status_code == 200
            all_keys = res_all.json()
            revoked_item = next((k for k in all_keys if k["id"] == key_id), None)
            assert revoked_item is not None
            assert revoked_item["is_active"] is False

            # Verify SBP audit logs were created in DB
            async with db.tx() as tx:
                await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
                admin_user = await tx.user.find_first(where={"email": "admin@deeptrace.test"})
                await tx.execute_raw("SELECT set_config('app.current_org_id', $1, true);", admin_user.organizationId)
                audit_logs = await tx.auditlog.find_many(
                    where={"entityId": key_id},
                    order={"createdAt": "asc"},
                )
            assert len(audit_logs) >= 2
            actions = [log.action for log in audit_logs]
            assert "API_KEY_CREATED" in actions
            assert "API_KEY_REVOKED" in actions
    finally:
        if db.is_connected():
            await disconnect()


