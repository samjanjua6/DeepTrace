import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.client import connect, disconnect, db


@pytest.mark.asyncio
async def test_webhooks_complete_rbac_and_lifecycle():
    """Comprehensive test for Webhook RBAC, CRUD lifecycle, test ping, and SBP audit logging."""
    if db.is_connected():
        await disconnect()
    await connect()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # ── 1. Unauthenticated requests must be rejected with 401 ──────────
            res = await client.get("/api/v1/webhooks")
            assert res.status_code == 401

            # ── 2. Analyst role must be rejected with 403 FORBIDDEN ────────────
            from app.core.security import create_access_token
            async with db.tx() as tx:
                await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
                analyst_user = await tx.user.find_first(where={"role": "ANALYST"})
            assert analyst_user is not None
            analyst_token = create_access_token(subject=analyst_user.id)
            analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

            # GET should be 403
            res_get = await client.get("/api/v1/webhooks", headers=analyst_headers)
            assert res_get.status_code == 403
            assert "FORBIDDEN" in res_get.text

            # POST should be 403
            res_post = await client.post(
                "/api/v1/webhooks",
                json={"url": "https://analyst.meezan.pk/webhook", "events": ["investigation.completed"]},
                headers=analyst_headers,
            )
            assert res_post.status_code == 403
            assert "FORBIDDEN" in res_post.text

            # DELETE should be 403
            res_del = await client.delete("/api/v1/webhooks/fake-ep-id", headers=analyst_headers)
            assert res_del.status_code == 403
            assert "FORBIDDEN" in res_del.text

            # ── 3. Admin role can create, list, inspect secret, test, and delete ─
            admin_login_resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "admin@deeptrace.test", "password": "Admin@12345"},
            )
            assert admin_login_resp.status_code == 200
            admin_token = admin_login_resp.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Create webhook endpoint
            create_payload = {
                "url": "https://core-banking.meezanbank.com/api/v1/events",
                "events": ["investigation.completed", "risk.critical"],
                "description": "Meezan Core Banking Middleware Notification",
            }
            res_create = await client.post("/api/v1/webhooks", json=create_payload, headers=admin_headers)
            assert res_create.status_code == 201
            created_data = res_create.json()

            endpoint_id = created_data["id"]
            secret = created_data["secret"]
            assert endpoint_id is not None
            assert len(secret) == 64  # 32 bytes hex
            assert created_data["is_active"] is True
            assert "investigation.completed" in created_data["events"]

            # List endpoints
            res_list = await client.get("/api/v1/webhooks", headers=admin_headers)
            assert res_list.status_code == 200
            endpoints = res_list.json()
            assert any(ep["id"] == endpoint_id for ep in endpoints)

            # Retrieve secret via dedicated endpoint
            res_sec = await client.get(f"/api/v1/webhooks/{endpoint_id}/secret", headers=admin_headers)
            assert res_sec.status_code == 200
            assert res_sec.json()["secret"] == secret

            # Query initial deliveries
            res_deliv = await client.get(f"/api/v1/webhooks/{endpoint_id}/deliveries", headers=admin_headers)
            assert res_deliv.status_code == 200
            assert isinstance(res_deliv.json(), list)

            # Trigger live test ping
            res_test = await client.post(
                f"/api/v1/webhooks/{endpoint_id}/test",
                json={"event_type": "test.ping"},
                headers=admin_headers,
            )
            assert res_test.status_code == 200
            test_data = res_test.json()
            assert "signature_header" in test_data
            assert test_data["signature_header"].startswith("t=")
            assert "v1=" in test_data["signature_header"]
            assert "payload_sent" in test_data

            # Check deliveries again - should have at least 1 delivery recorded from test ping
            res_deliv_after = await client.get(f"/api/v1/webhooks/{endpoint_id}/deliveries", headers=admin_headers)
            assert res_deliv_after.status_code == 200
            deliveries = res_deliv_after.json()
            assert len(deliveries) >= 1
            assert deliveries[0]["event_type"] == "test.ping"

            # Deactivate / delete endpoint
            res_del = await client.delete(f"/api/v1/webhooks/{endpoint_id}", headers=admin_headers)
            assert res_del.status_code == 204

            # List endpoints after deletion
            res_list_after = await client.get("/api/v1/webhooks", headers=admin_headers)
            assert res_list_after.status_code == 200
            active_endpoints = res_list_after.json()
            assert not any(ep["id"] == endpoint_id for ep in active_endpoints)

            # Verify SBP audit logs in PostgreSQL
            async with db.tx() as tx:
                await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
                admin_user = await tx.user.find_first(where={"email": "admin@deeptrace.test"})
                await tx.execute_raw("SELECT set_config('app.current_org_id', $1, true);", admin_user.organizationId)
                audit_logs = await tx.auditlog.find_many(
                    where={"entityId": endpoint_id},
                    order={"createdAt": "asc"},
                )
            assert len(audit_logs) >= 2
            actions = [log.action for log in audit_logs]
            assert "ORGANIZATION_SETTINGS_UPDATED" in actions
    finally:
        if db.is_connected():
            await disconnect()
