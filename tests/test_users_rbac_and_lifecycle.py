import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.client import connect, disconnect, db
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_users_complete_rbac_and_lifecycle():
    """Test complete User & Role Administration lifecycle, RBAC, audit logging, and safety guardrails."""
    if db.is_connected():
        await disconnect()
    await connect()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # ── 1. Unauthenticated Requests ────────────────────────────────────
            res_unauth = await client.get("/api/v1/users")
            assert res_unauth.status_code == 401

            # ── 2. Authenticated Analyst (403 Forbidden on all user routes) ────
            async with db.tx() as tx:
                await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
                analyst_user = await tx.user.find_first(where={"role": "ANALYST"})
                admin_user = await tx.user.find_first(where={"role": "ADMIN"})
            assert analyst_user is not None
            assert admin_user is not None

            analyst_token = create_access_token(subject=analyst_user.id)
            analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

            admin_token = create_access_token(subject=admin_user.id)
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # GET users -> 403
            res_get = await client.get("/api/v1/users", headers=analyst_headers)
            assert res_get.status_code == 403
            assert "FORBIDDEN" in res_get.text

            # POST invite -> 403
            res_post = await client.post(
                "/api/v1/users/invite",
                json={
                    "email": "unauth.analyst@bank.test",
                    "first_name": "Test",
                    "last_name": "Analyst",
                    "role": "ANALYST",
                },
                headers=analyst_headers,
            )
            assert res_post.status_code == 403

            # PATCH role -> 403
            res_patch_role = await client.patch(
                f"/api/v1/users/{analyst_user.id}/role",
                json={"role": "ADMIN"},
                headers=analyst_headers,
            )
            assert res_patch_role.status_code == 403

            # ── 3. Admin User Lifecycle ─────────────────────────────────────────
            # List users
            res_list = await client.get("/api/v1/users", headers=admin_headers)
            assert res_list.status_code == 200
            users_list = res_list.json()
            assert isinstance(users_list, list)
            assert any(u["id"] == admin_user.id for u in users_list)

            # Invite new analyst
            import uuid
            invite_email = f"invited.analyst.{uuid.uuid4().hex[:8]}@deeptrace.test"
            res_invite = await client.post(
                "/api/v1/users/invite",
                json={
                    "email": invite_email,
                    "first_name": "Tariq",
                    "last_name": "Mehmood",
                    "role": "ANALYST",
                },
                headers=admin_headers,
            )
            assert res_invite.status_code == 201
            invite_data = res_invite.json()
            new_user = invite_data["user"]
            assert new_user["email"] == invite_email
            assert new_user["role"] == "ANALYST"
            assert "temp_password" in invite_data
            assert "dispatch_memo" in invite_data
            new_user_id = new_user["id"]

            # Change role from ANALYST to VIEWER
            res_role = await client.patch(
                f"/api/v1/users/{new_user_id}/role",
                json={"role": "VIEWER"},
                headers=admin_headers,
            )
            assert res_role.status_code == 200
            assert res_role.json()["role"] == "VIEWER"

            # Suspend member account (deactivate)
            res_deact = await client.patch(
                f"/api/v1/users/{new_user_id}/status",
                json={"is_active": False},
                headers=admin_headers,
            )
            assert res_deact.status_code == 200
            assert res_deact.json()["is_active"] is False

            # Reactivate member account
            res_react = await client.patch(
                f"/api/v1/users/{new_user_id}/status",
                json={"is_active": True},
                headers=admin_headers,
            )
            assert res_react.status_code == 200
            assert res_react.json()["is_active"] is True

            # Unlock member account
            res_unlock = await client.post(
                f"/api/v1/users/{new_user_id}/unlock",
                headers=admin_headers,
            )
            assert res_unlock.status_code == 200
            assert res_unlock.json()["success"] is True

            # Reset 2FA
            res_mfa = await client.post(
                f"/api/v1/users/{new_user_id}/reset-mfa",
                headers=admin_headers,
            )
            assert res_mfa.status_code == 200
            assert res_mfa.json()["success"] is True

            # Self-deactivation prevention check
            res_self = await client.patch(
                f"/api/v1/users/{admin_user.id}/status",
                json={"is_active": False},
                headers=admin_headers,
            )
            assert res_self.status_code == 400
            self_err = res_self.json()
            assert (self_err.get("error") or self_err.get("detail", {})).get("code") == "SELF_DEACTIVATION_FORBIDDEN"

            # ── 4. Verify Immutable SBP Audit Logs in PostgreSQL ───────────────
            async with db.tx() as tx:
                await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
                await tx.execute_raw("SELECT set_config('app.current_org_id', $1, true);", admin_user.organizationId)
                audit_logs = await tx.auditlog.find_many(
                    where={"organizationId": admin_user.organizationId},
                    order={"createdAt": "desc"},
                )
            actions = [log.action for log in audit_logs]
            assert "USER_CREATED" in actions
            assert "USER_ROLE_CHANGED" in actions
            assert "USER_DEACTIVATED" in actions
            assert "USER_REACTIVATED" in actions

    finally:
        if db.is_connected():
            await disconnect()
