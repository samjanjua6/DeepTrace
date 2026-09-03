"""Tests for pipeline feature. TODO: Implement test cases."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_placeholder(client: AsyncClient):
    """Replace with real tests for the pipeline feature."""
    response = await client.get("/health")
    assert response.status_code == 200
