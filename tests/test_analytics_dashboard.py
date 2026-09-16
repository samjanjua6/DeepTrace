"""Tests for Executive Fraud Analytics & Risk Command Center API."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.client import connect, disconnect, db
from app.features.analytics.service import format_rupees_pakistan, format_latency


def test_formatting_helpers():
    """Verify Pakistani rupee Lakh/Crore and latency formatting."""
    # Crores (>= 10,000,000)
    full, short = format_rupees_pakistan(48_250_000)
    assert full == "PKR 48,250,000"
    assert short == "PKR 4.83 Crore"

    # Lakhs (>= 100,000)
    full, short = format_rupees_pakistan(2_175_000)
    assert full == "PKR 2,175,000"
    assert short == "PKR 21.75 Lakh"

    # Small amounts
    full, short = format_rupees_pakistan(50_000)
    assert full == "PKR 50,000"
    assert short == "PKR 50,000"

    # Latencies
    assert format_latency(580) == "580 ms"
    assert format_latency(2100) == "2.1 s"
    assert format_latency(35) == "35 ms"


from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_dashboard_analytics_endpoints():
    """Verify unauthenticated rejection, authenticated metrics response, and data integrity."""
    if db.is_connected():
        await disconnect()
    await connect()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Unauthenticated request should fail with 401
            res_unauth = await client.get("/api/v1/analytics/dashboard")
            assert res_unauth.status_code == 401

            # 2. Authenticate as Analyst or Admin
            async with db.tx() as tx:
                await tx.execute_raw("SELECT set_config('app.is_auth', 'true', true);")
                user = await tx.user.find_first(where={"role": "ANALYST"})
                if not user:
                    user = await tx.user.find_first()
            assert user is not None

            token = create_access_token(subject=user.id)
            headers = {"Authorization": f"Bearer {token}"}

            # 3. Request /api/v1/analytics/dashboard
            res_dashboard = await client.get("/api/v1/analytics/dashboard", headers=headers)
            assert res_dashboard.status_code == 200
            data = res_dashboard.json()

            # Verify Top 4 Stat Cards
            # Card 1: Total Scanned Documents & Quota
            scanned = data["total_scanned"]
            assert "month_to_date" in scanned
            assert "monthly_limit" in scanned
            assert "quota_usage_percentage" in scanned
            assert "remaining_capacity" in scanned
            assert scanned["monthly_limit"] > 0
            assert 0 <= scanned["quota_usage_percentage"] <= 100

            # Card 2: Tampering Detection Rate
            tampering = data["tampering_detection"]
            assert "rate_percentage" in tampering
            assert "critical_count" in tampering
            assert "high_count" in tampering
            assert "total_evaluated" in tampering
            assert "risk_status" in tampering
            assert 0 <= tampering["rate_percentage"] <= 100

            # Card 3: Financial Exposure Prevented
            exposure = data["financial_exposure"]
            assert "total_prevented_pkr" in exposure
            assert "total_prevented_formatted" in exposure
            assert "total_prevented_short" in exposure
            assert exposure["total_prevented_pkr"] > 0
            assert "PKR" in exposure["total_prevented_formatted"]

            # Card 4: Verification Latency
            latency = data["verification_latency"]
            assert "p50_ms" in latency
            assert "p95_ms" in latency
            assert "p50_formatted" in latency
            assert "p95_formatted" in latency
            assert "deterministic_p50_ms" in latency
            assert "multi_page_ocr_p95_ms" in latency
            assert latency["p50_ms"] > 0
            assert latency["p95_ms"] >= latency["p50_ms"]

            # Additional Executive Telemetry
            assert "recent_critical_alerts" in data
            assert isinstance(data["recent_critical_alerts"], list)
            assert "document_type_distribution" in data
            assert isinstance(data["document_type_distribution"], dict)

            # 4. Test alias route /api/v1/dashboard
            res_alias = await client.get("/api/v1/dashboard", headers=headers)
            assert res_alias.status_code == 200
            alias_data = res_alias.json()
            assert alias_data["organization_id"] == data["organization_id"]

    finally:
        await disconnect()
