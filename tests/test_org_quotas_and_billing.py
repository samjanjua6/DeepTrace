import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.client import connect, disconnect, db
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_org_quotas_and_billing_lifecycle():
    """Test organizational quotas, usage stats, tier upgrade, RBAC, audit logging, and upload enforcement."""
    if db.is_connected():
        await disconnect()
    await connect()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Unauthenticated requests
            res = await client.get("/api/v1/org")
            assert res.status_code == 401

            # 2. Authenticated Analyst
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

            # Analyst CAN read org & usage
            res_org = await client.get("/api/v1/org", headers=analyst_headers)
            assert res_org.status_code == 200
            org_data = res_org.json()
            assert "monthly_doc_limit" in org_data
            assert "monthly_doc_used" in org_data
            assert "remaining_docs" in org_data
            assert "usage_percentage" in org_data

            res_usage = await client.get("/api/v1/org/usage", headers=analyst_headers)
            assert res_usage.status_code == 200
            usage_data = res_usage.json()
            assert "monthly_doc_limit" in usage_data
            assert "remaining" in usage_data
            assert "document_type_breakdown" in usage_data

            # Analyst CANNOT update settings (403 Forbidden)
            res_patch = await client.patch(
                "/api/v1/org/settings",
                json={"name": "Unauthorized Org Rename"},
                headers=analyst_headers,
            )
            assert res_patch.status_code == 403
            assert "FORBIDDEN" in res_patch.text

            # Analyst CANNOT upgrade tier (403 Forbidden)
            res_tier = await client.post(
                "/api/v1/org/tier",
                json={"target_tier": "ENTERPRISE"},
                headers=analyst_headers,
            )
            assert res_tier.status_code == 403
            assert "FORBIDDEN" in res_tier.text

            # 3. Admin can update settings and upgrade tier
            res_admin_patch = await client.patch(
                "/api/v1/org/settings",
                json={"settings": {"alert_threshold_pct": 85}},
                headers=admin_headers,
            )
            assert res_admin_patch.status_code == 200

            # Admin upgrades tier to BUSINESS_SCALE
            res_admin_tier = await client.post(
                "/api/v1/org/tier",
                json={"target_tier": "BUSINESS_SCALE"},
                headers=admin_headers,
            )
            assert res_admin_tier.status_code == 200
            tier_data = res_admin_tier.json()
            assert tier_data["subscription_tier"] == "BUSINESS_SCALE"
            assert tier_data["monthly_doc_limit"] == 15000

            # Verify audit log in PostgreSQL under RLS
            async with db.tx() as tx:
                await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
                await tx.execute_raw("SELECT set_config('app.current_org_id', $1, true);", admin_user.organizationId)
                audit_entry = await tx.auditlog.find_first(
                    where={
                        "organizationId": admin_user.organizationId,
                        "action": "ORGANIZATION_SETTINGS_UPDATED",
                    },
                    order={"createdAt": "desc"},
                )
                assert audit_entry is not None

            # 4. Quota Enforcement during Document Intake
            # Create a test investigation
            inv_res = await client.post(
                "/api/v1/investigations",
                json={"title": "Quota Verification Case", "description": "Testing intake quota limits"},
                headers=admin_headers,
            )
            assert inv_res.status_code in (200, 201)
            inv_id = inv_res.json()["id"]

            # Simulate quota exhausted on the organization
            async with db.tx() as tx:
                await tx.organization.update(
                    where={"id": admin_user.organizationId},
                    data={"subscriptionTier": "FREE", "monthlyDocLimit": 5, "monthlyDocUsed": 5},
                )

            # Attempt upload when limit reached -> 402 Payment Required
            import fitz
            pdf_doc = fitz.open()
            pdf_doc.new_page()
            valid_pdf = pdf_doc.tobytes()
            pdf_doc.close()

            res_blocked = await client.post(
                f"/api/v1/investigations/{inv_id}/documents",
                files={"file": ("over_quota.pdf", valid_pdf, "application/pdf")},
                data={"document_type": "BANK_STATEMENT"},
                headers=admin_headers,
            )
            assert res_blocked.status_code == 402
            blocked_json = res_blocked.json()
            err_data = blocked_json.get("error") or blocked_json.get("detail", {})
            assert err_data.get("code") == "DOCUMENT_QUOTA_EXCEEDED"

            # Reset quota allowance and verify upload succeeds + increments count
            async with db.tx() as tx:
                await tx.organization.update(
                    where={"id": admin_user.organizationId},
                    data={"monthlyDocUsed": 2, "monthlyDocLimit": 100},
                )

            res_allowed = await client.post(
                f"/api/v1/investigations/{inv_id}/documents",
                files={"file": ("within_quota.pdf", valid_pdf, "application/pdf")},
                data={"document_type": "BANK_STATEMENT"},
                headers=admin_headers,
            )
            assert res_allowed.status_code == 201

            # Check that monthlyDocUsed incremented to 3
            res_after = await client.get("/api/v1/org/usage", headers=admin_headers)
            assert res_after.status_code == 200
            assert res_after.json()["monthly_doc_used"] == 3

    finally:
        if db.is_connected():
            await disconnect()
