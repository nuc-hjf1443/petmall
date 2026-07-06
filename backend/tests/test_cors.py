import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_local_frontend_origin_can_complete_preflight(test_context):
    client: AsyncClient = test_context["client"]

    response = await client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]


@pytest.mark.asyncio
async def test_unconfigured_remote_origin_is_rejected(test_context):
    client: AsyncClient = test_context["client"]

    response = await client.options(
        "/auth/login",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
