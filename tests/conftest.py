"""
DeepTrace — Test Fixtures (conftest.py)
Shared pytest fixtures for database, async HTTP client, and mock users.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.client import connect, disconnect, db


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Async HTTP test client against the FastAPI app."""
    if not db.is_connected():
        await connect()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def mock_org_id() -> str:
    return "org_test_deeptrace_001"


@pytest.fixture
def mock_user_payload(mock_org_id: str) -> dict:
    return {
        "id": "user_test_001",
        "email": "analyst@deeptrace.test",
        "organization_id": mock_org_id,
        "role": "ANALYST",
    }
